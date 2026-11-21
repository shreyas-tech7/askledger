import sqlite3

from askledger import db


def test_rebuild_gives_the_same_content(tmp_path):
    """Broken case: an unseeded generator would give a different database each run."""
    fresh = db.build(tmp_path / "ledger.db")
    assert db.content_hash(fresh) == db.content_hash(db.DB_PATH)


def test_other_seed_gives_other_content(tmp_path):
    other = db.build(tmp_path / "other.db", seed=1)
    assert db.content_hash(other) != db.content_hash(db.DB_PATH)


def test_real_world_quirks_are_present():
    con = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True)
    one = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    assert set(db.TABLES) == {
        r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert one("SELECT COUNT(*) FROM payments WHERE amount < 0") > 0  # refunds
    assert one("SELECT former_name FROM products WHERE name = 'House Blend'") == "Morning Blend"
    assert one("SELECT COUNT(*) FROM customers WHERE email IS NULL") > 0
    assert one("SELECT COUNT(*) FROM expenses WHERE vendor IS NULL") > 0
    assert one("SELECT MIN(discontinued) FROM products WHERE category = 'Candles'") == 1
    late = "SELECT COUNT(*) FROM order_items oi JOIN orders o USING (order_id) JOIN products p USING (product_id) WHERE p.category = 'Candles' AND o.order_date >= '2025-07-01'"
    assert one(late) == 0
    con.close()
