import pytest

from askledger import evaluate, questions


def test_wilson_matches_known_values():
    """Known value: 8 of 10 gives about 0.490 to 0.943 (Wilson 1927 formula)."""
    lo, hi = evaluate.wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-4)
    assert hi == pytest.approx(0.9433, abs=1e-4)
    assert evaluate.wilson(0, 10)[0] == 0.0
    assert evaluate.wilson(10, 10)[1] == pytest.approx(1.0)
    assert evaluate.wilson(0, 0) == (0.0, 0.0)


def test_gold_sql_scores_itself_correct():
    for q in questions.load()[:30]:
        assert evaluate.correct(q.gold_sql, q), q.id


def test_wrong_blocked_and_missing_sql_score_zero():
    q = questions.load()[0]
    assert not evaluate.correct("SELECT COUNT(*) FROM products", q)
    assert not evaluate.correct("DROP TABLE customers", q)
    assert not evaluate.correct("SELECT nope FROM customers", q)
    assert not evaluate.correct(None, q)


def test_summarize_groups_by_split_and_tier():
    recs = [
        {"split": "dev", "tier": 1, "correct": True},
        {"split": "dev", "tier": 1, "correct": False},
        {"split": "heldout", "tier": 2, "correct": True},
    ]
    s = evaluate.summarize(recs)
    assert s["dev/tier1"]["correct"] == 1 and s["dev/tier1"]["n"] == 2
    assert s["dev/all"]["n"] == 2 and s["heldout/all"]["accuracy"] == 1.0
