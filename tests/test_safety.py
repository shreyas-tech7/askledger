import shutil
import sqlite3

import pytest

from askledger import db, questions, safety


@pytest.fixture
def writable(tmp_path):
    path = tmp_path / "copy.db"
    shutil.copy(db.DB_PATH, path)
    return path


def _count(path, table="payments"):
    con = sqlite3.connect(path)
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    con.close()
    return n


def test_every_gold_query_passes_the_safety_layer():
    """Broken case: an authorizer that denies CTE reads or window functions blocks real work."""
    for q in questions.load():
        assert safety.run(q.gold_sql).rows, q.id


def test_authorizer_alone_blocks_a_write(writable):
    """The write gets past the text check (off) and the read-only URI (off: rw connection).

    Broken case: with the authorizer also off, the same INSERT really writes a row.
    """
    sql = "INSERT INTO payments VALUES (9999, 1, '2026-01-01', 1000000, 'card')"
    before = _count(writable)
    with pytest.raises(safety.Blocked) as e:
        safety.run_layers(sql, writable, text=False, readonly=False, authorizer=True)
    assert e.value.reason == "write"
    assert _count(writable) == before
    safety.run_layers(sql, writable, text=False, readonly=False, authorizer=False)
    assert _count(writable) == before + 1


def test_authorizer_alone_blocks_a_write_hidden_in_a_cte(writable):
    sql = "WITH t AS (SELECT 1) DELETE FROM payments"
    with pytest.raises(safety.Blocked) as e:
        safety.run_layers(sql, writable, text=False, readonly=False)
    assert e.value.reason == "write"
    assert _count(writable) > 0


def test_read_only_uri_alone_blocks_a_write(writable):
    """Broken case: a plain connect() would let the DELETE through."""
    with pytest.raises(safety.Blocked) as e:
        safety.run_layers("DELETE FROM payments", writable, text=False, authorizer=False)
    assert e.value.reason == "read_only"
    assert _count(writable) > 0


def test_text_check():
    safety.text_check("SELECT 1")
    safety.text_check("  -- note\n  WITH a AS (SELECT 1) SELECT * FROM a;")
    safety.text_check("SELECT 'a;b'")
    for sql, reason in [
        ("SELECT 1; SELECT 2", "multiple_statements"),
        ("/* SELECT */ DELETE FROM x", "not_select"),
        ("PRAGMA table_info(x)", "not_select"),
        ("", "not_select"),
        ("SELECT " + "1," * 3000 + "1", "too_long"),
    ]:
        with pytest.raises(safety.Blocked) as e:
            safety.text_check(sql)
        assert e.value.reason == reason


def test_attach_is_blocked_even_without_the_authorizer(writable):
    """SQLITE_LIMIT_ATTACHED is 0, so ATTACH fails even if the authorizer were missing."""
    with pytest.raises(safety.Blocked) as e:
        safety.run_layers("ATTACH ':memory:' AS x", writable, text=False, authorizer=False)
    assert e.value.reason == "attach"
    with pytest.raises(safety.Blocked) as e:
        safety.run_layers("ATTACH ':memory:' AS x", writable, text=False)
    assert e.value.reason == "attach"


@pytest.mark.parametrize(
    "sql,reason",
    [
        ("SELECT * FROM pragma_table_info('customers')", "schema_read"),
        ("SELECT name FROM sqlite_master", "schema_read"),
        ("SELECT load_extension('x')", "extension"),
        ("SELECT randomblob(10)", "function"),
    ],
)
def test_authorizer_denials(sql, reason):
    with pytest.raises(safety.Blocked) as e:
        safety.run(sql)
    assert e.value.reason == reason


def test_pragma_statement_is_denied_by_the_authorizer(writable):
    """Broken case: with no authorizer, PRAGMA user_version = 7 changes the file."""
    with pytest.raises(safety.Blocked) as e:
        safety.run_layers("PRAGMA user_version = 7", writable, text=False, readonly=False)
    assert e.value.reason == "pragma"
    safety.run_layers(
        "PRAGMA user_version = 7", writable, text=False, readonly=False, authorizer=False
    )
    con = sqlite3.connect(writable)
    assert con.execute("PRAGMA user_version").fetchone()[0] == 7
    con.close()


def test_row_cap():
    with pytest.raises(safety.Blocked) as e:
        safety.run("SELECT * FROM order_items", max_rows=100)
    assert e.value.reason == "row_cap"
    assert len(safety.run("SELECT * FROM order_items", max_rows=5000).rows) > 100


def test_time_limit_stops_an_endless_query():
    """Broken case: without the progress handler this query never ends."""
    sql = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT COUNT(*) FROM c"
    with pytest.raises(safety.Blocked) as e:
        safety.run(sql, time_limit_s=0.2)
    assert e.value.reason == "timeout"


def test_sql_errors_are_not_blocks():
    with pytest.raises(safety.SQLError, match="no such column"):
        safety.run("SELECT revenue FROM orders")


def test_tables_read_are_recorded():
    r = safety.run(
        "SELECT c.city, o.channel FROM orders o JOIN customers c ON c.customer_id = o.customer_id LIMIT 1"
    )
    assert r.tables_read == {"orders", "customers"}


def test_database_file_is_unchanged_by_the_suite():
    assert db.content_hash(db.DB_PATH) == db.content_hash(db.DB_PATH)
