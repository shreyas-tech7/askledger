import collections
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

from askledger import db, questions

ROOT = Path(__file__).resolve().parents[1]


def _writer():
    spec = importlib.util.spec_from_file_location("wq", ROOT / "scripts" / "write_questions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_question_file_is_frozen():
    """Broken case: someone edits a question or gold query after the freeze."""
    text = questions.QUESTIONS_PATH.read_bytes()
    frozen = questions.QUESTIONS_PATH.with_suffix(".sha256").read_text().strip()
    assert hashlib.sha256(text).hexdigest() == frozen
    assert _writer().render(_writer().build()).encode() == text


def test_size_tiers_and_split():
    qs = questions.load()
    assert len(qs) >= 200
    assert {q.tier for q in qs} == {1, 2, 3}
    split = collections.Counter(q.split for q in qs)
    assert split["dev"] == 140 and split["heldout"] == len(qs) - 140
    dev_fams = {q.family for q in qs if q.split == "dev"}
    held_fams = {q.family for q in qs if q.split == "heldout"}
    assert not dev_fams & held_fams
    assert len({q.id for q in qs}) == len(qs)


def _run(con, sql, ordered):
    rows = con.execute(sql).fetchall()
    return rows if ordered else sorted(rows, key=repr)


def test_every_gold_query_runs_non_empty_and_deterministic(tmp_path):
    """Broken case: a gold query with no ORDER BY tie-break, or an empty result.

    `reverse_unordered_selects` makes SQLite scan tables in the other order, which exposes
    any answer that depends on scan order. A rebuilt database must give the same answers.
    """
    fresh = db.build(tmp_path / "fresh.db")
    a = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True)
    b = sqlite3.connect(f"file:{fresh}?mode=ro", uri=True)
    b.execute("PRAGMA reverse_unordered_selects = ON")
    for q in questions.load():
        first = _run(a, q.gold_sql, q.ordered)
        assert first, q.id
        assert not all(v is None for row in first for v in row), q.id
        assert first == _run(a, q.gold_sql, q.ordered), q.id
        assert first == _run(b, q.gold_sql, q.ordered), q.id
    a.close()
    b.close()


def test_questions_jsonl_rows_have_fields():
    for line in questions.QUESTIONS_PATH.read_text().splitlines():
        row = json.loads(line)
        assert set(row) == {"id", "family", "tier", "split", "ordered", "question", "gold_sql"}
