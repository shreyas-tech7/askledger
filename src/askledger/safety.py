"""The safety layer. It never trusts the SQL it gets.

Four layers, each enforced by SQLite or by plain code, never by the model:

1. Text checks: one statement, at most MAX_SQL_CHARS, and it must start with SELECT or WITH.
2. A read-only connection opened with a ``file:<path>?mode=ro`` URI.
3. ``set_authorizer``: every action is denied except SELECT, reads of the ledger tables,
   recursive CTEs and functions on an allowlist. ATTACH, DETACH, PRAGMA, every write and
   every function off the list (load_extension, randomblob, printf...) is denied.
4. Limits: a time limit through ``set_progress_handler``, a row cap on the fetch, and
   SQLite limits on attached databases and on string length.

What it does not stop: a legal read can still return every customer row. The data is
synthetic, so that is fine here. A real deployment would also need row-level rules.
"""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from askledger.db import DB_PATH, TABLES

MAX_SQL_CHARS = 5000
MAX_ROWS = 1000
TIME_LIMIT_S = 2.0
MAX_STRING = 1_000_000

ALLOWED_FUNCTIONS = frozenset(
    """
    count sum total avg min max round abs coalesce ifnull nullif iif lower upper length
    substr substring trim ltrim rtrim replace instr like glob strftime date time datetime
    julianday group_concat row_number rank dense_rank percent_rank cume_dist ntile lag lead
    first_value last_value nth_value
    """.split()
)

WRITE_ACTIONS = {
    getattr(sqlite3, name)
    for name in dir(sqlite3)
    if name.startswith(("SQLITE_CREATE_", "SQLITE_DROP_"))
    or name
    in (
        "SQLITE_INSERT",
        "SQLITE_UPDATE",
        "SQLITE_DELETE",
        "SQLITE_ALTER_TABLE",
        "SQLITE_TRANSACTION",
        "SQLITE_SAVEPOINT",
        "SQLITE_ANALYZE",
        "SQLITE_REINDEX",
    )
}

COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)
LITERAL = re.compile(r"'(?:[^']|'')*'")


class Blocked(Exception):
    """The safety layer refused the query. ``reason`` is a short code."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


class SQLError(Exception):
    """The query was allowed but SQLite raised an error, for example a bad column name."""


@dataclass
class Result:
    columns: list[str]
    rows: list[tuple]
    tables_read: set[str] = field(default_factory=set)
    elapsed_s: float = 0.0


def text_check(sql: str) -> None:
    """Layer 1. Cheap checks on the text. The other layers do not depend on these."""
    if len(sql) > MAX_SQL_CHARS:
        raise Blocked("too_long", f"{len(sql)} characters")
    body = COMMENT.sub(" ", sql).strip().lstrip("(").lstrip()
    if LITERAL.sub("''", body).rstrip().rstrip(";").count(";"):
        raise Blocked("multiple_statements")
    first = body.split(None, 1)[0].upper() if body else ""
    if first not in ("SELECT", "WITH"):
        raise Blocked("not_select", first or "empty")


class _Guard:
    """The authorizer and the progress handler for one connection."""

    def __init__(self, tables: set[str]):
        self.tables = tables
        self.denied: list[tuple[str, str]] = []
        self.read: set[str] = set()
        self.deadline = 0.0

    def deny(self, reason: str, detail: str) -> int:
        self.denied.append((reason, detail))
        return sqlite3.SQLITE_DENY

    def authorize(self, action, arg1, arg2, dbname, trigger):
        if action == sqlite3.SQLITE_SELECT or action == sqlite3.SQLITE_RECURSIVE:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            name = (arg1 or "").lower()
            if name.startswith(("sqlite_", "pragma_")):
                return self.deny("schema_read", arg1)
            if arg1 in self.tables and dbname in ("main", None):
                self.read.add(arg1)
                return sqlite3.SQLITE_OK
            if dbname is None:  # a CTE or subquery name. Its own reads are checked too
                return sqlite3.SQLITE_OK
            return self.deny("table", f"{dbname}.{arg1}")
        if action == sqlite3.SQLITE_FUNCTION:
            name = (arg2 or "").lower()
            if name in ALLOWED_FUNCTIONS:
                return sqlite3.SQLITE_OK
            return self.deny("extension" if name == "load_extension" else "function", name)
        if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
            return self.deny("attach", arg1 or "")
        if action == sqlite3.SQLITE_PRAGMA:
            return self.deny("pragma", arg1 or "")
        if action in WRITE_ACTIONS:
            return self.deny("write", f"action {action} on {arg1}")
        return self.deny("other", f"action {action}")

    def progress(self) -> int:
        return 1 if time.monotonic() > self.deadline else 0


def _connect(path: Path, *, readonly: bool = True, authorizer: bool = True):
    """Open a guarded connection. Only tests turn a layer off, to prove the others alone."""
    uri = f"file:{Path(path).resolve()}?mode={'ro' if readonly else 'rw'}"
    con = sqlite3.connect(uri, uri=True, isolation_level=None, check_same_thread=False)
    if hasattr(con, "enable_load_extension"):
        con.enable_load_extension(False)
    con.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    con.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_STRING)
    con.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, MAX_SQL_CHARS + 100)
    if hasattr(con, "setconfig"):  # Python 3.12+: refuse writes to the schema
        con.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
        con.setconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False)
    guard = _Guard(set(TABLES))
    if authorizer:
        con.set_authorizer(guard.authorize)
    con.set_progress_handler(guard.progress, 1000)
    return con, guard


def _execute(con, guard, sql, max_rows, time_limit_s) -> Result:
    start = time.monotonic()
    guard.deadline = start + time_limit_s
    guard.denied.clear()
    guard.read.clear()
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(max_rows + 1)
    except sqlite3.ProgrammingError as e:
        if "one statement" in str(e):
            raise Blocked("multiple_statements") from e
        raise SQLError(str(e)) from e
    except sqlite3.Error as e:
        if guard.denied:
            reason, detail = guard.denied[0]
            raise Blocked(reason, detail) from e
        msg = str(e)
        if msg == "interrupted":
            raise Blocked("timeout", f"over {time_limit_s}s") from e
        if "readonly" in msg or "read-only" in msg:
            raise Blocked("read_only", msg) from e
        if "too many attached" in msg:
            raise Blocked("attach", msg) from e
        if "too big" in msg:
            raise Blocked("too_big", msg) from e
        raise SQLError(msg) from e
    if len(rows) > max_rows:
        cur.close()
        raise Blocked("row_cap", f"more than {max_rows} rows")
    columns = [d[0] for d in cur.description or []]
    return Result(columns, rows, set(guard.read), time.monotonic() - start)


def run(
    sql: str,
    db_path: Path = DB_PATH,
    *,
    max_rows: int = MAX_ROWS,
    time_limit_s: float = TIME_LIMIT_S,
) -> Result:
    """Run one query with every layer on. Raises Blocked or SQLError."""
    text_check(sql)
    con, guard = _connect(db_path)
    try:
        return _execute(con, guard, sql, max_rows, time_limit_s)
    finally:
        con.close()


def run_layers(
    sql: str,
    db_path: Path,
    *,
    text: bool = True,
    readonly: bool = True,
    authorizer: bool = True,
    max_rows: int = MAX_ROWS,
    time_limit_s: float = TIME_LIMIT_S,
) -> Result:
    """Test and report helper: run with some layers off. Never used to answer a user."""
    if text:
        text_check(sql)
    con, guard = _connect(db_path, readonly=readonly, authorizer=authorizer)
    try:
        return _execute(con, guard, sql, max_rows, time_limit_s)
    finally:
        con.close()
