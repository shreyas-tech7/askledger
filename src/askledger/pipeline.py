"""The pipeline: link tables, generate SQL, run it safely, repair on error, answer and log."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from askledger import linking, safety

AGG = {"COUNT": "Counted", "SUM": "Added up", "AVG": "Averaged", "MAX": "Found the largest",
       "MIN": "Found the smallest"}  # fmt: skip
FILTER = re.compile(r"(\w+)\s*(?:(=|<>)\s*'([^']+)'|BETWEEN\s*'([^']+)'\s*AND\s*'([^']+)')", re.I)


@dataclass
class Answer:
    question: str
    sql: str | None
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    explanation: str = ""
    attempts: int = 0
    repairs: int = 0
    error: str | None = None
    blocked: str | None = None
    tables: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.sql is not None and self.error is None and self.blocked is None


def explain(sql: str, tables_read) -> str:
    """One plain line about what the query does. Built from the SQL text, not from a model."""
    up = sql.upper()
    verb = next((v for k, v in AGG.items() if re.search(rf"\b{k}\s*\(", up)), "Listed rows")
    if "OVER (" in up or "OVER(" in up:
        verb += " with a running or ranked window"
    shown = []
    for col, op, val, lo, hi in FILTER.findall(sql)[:3]:
        if lo:
            shown.append(f"{col} is from {lo} to {hi}")
        else:
            shown.append(f"{col} {'is not' if op == '<>' else 'is'} {val}")
    text = f"{verb} from {', '.join(sorted(tables_read)) or 'the ledger'}"
    if shown:
        text += ", where " + " and ".join(shown)
    shape = [w for w, k in (("grouped", "GROUP BY"), ("sorted", "ORDER BY")) if k in up]
    if shape:
        text += ", " + " and ".join(shape)
    return text + "."


def answer(question: str, generator, max_repairs: int = 2, question_id: str = "adhoc",
           log_path: Path | None = None, db_path=None) -> Answer:  # fmt: skip
    """Answer one question. Repairs only SQL errors, never a blocked query."""
    if hasattr(generator, "for_question"):
        generator.for_question(question_id)
    tables = linking.link(question)
    sql = generator.generate(question, tables)
    out = Answer(question, sql, tables=tables, attempts=1)
    while sql:
        try:
            kw = {"db_path": db_path} if db_path else {}
            result = safety.run(sql, **kw)
        except safety.Blocked as e:
            out.blocked, out.error = e.reason, str(e)
            break
        except safety.SQLError as e:
            out.error = str(e)
            if out.repairs >= max_repairs:
                break
            fixed = generator.repair(question, sql, str(e), tables)
            out.repairs += 1
            out.attempts += 1
            if not fixed:
                break
            sql = out.sql = fixed
            continue
        out.error = None
        out.columns, out.rows = result.columns, result.rows
        out.explanation = explain(sql, result.tables_read)
        break
    if sql is None:
        out.error = "no SQL: no template fits this question"
    _log(out, getattr(generator, "name", "unknown"), log_path)
    return out


def _log(a: Answer, generator: str, log_path: Path | None) -> None:
    path = log_path or os.environ.get("ASKLEDGER_LOG")
    if not path:
        return
    rec = asdict(a) | {"generator": generator, "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
    rec["rows"] = rec["rows"][:20]
    with open(path, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
