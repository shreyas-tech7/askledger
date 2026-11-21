import json

from askledger import pipeline
from askledger.templates import TemplateGenerator


def test_answer_has_a_table_the_sql_and_an_explanation(tmp_path):
    log = tmp_path / "log.jsonl"
    a = pipeline.answer("How many customers live in Ashford?", TemplateGenerator(), log_path=log)
    assert a.ok
    assert a.columns and a.rows
    assert a.sql.upper().startswith("SELECT")
    assert a.explanation == "Counted from customers, where city is Ashford."
    rec = json.loads(log.read_text())
    assert rec["question"] == a.question and rec["generator"] == "template"


def test_no_template_gives_a_clear_error():
    a = pipeline.answer("Sing a song", TemplateGenerator())
    assert not a.ok and a.error.startswith("no SQL")


def test_explain_mentions_filters_grouping_and_sorting():
    sql = "SELECT city, COUNT(*) FROM customers WHERE segment = 'retail' GROUP BY city ORDER BY 2"
    line = pipeline.explain(sql, {"customers"})
    assert "segment is retail" in line and "grouped" in line and "sorted" in line


def test_no_log_written_without_a_path(tmp_path, monkeypatch):
    monkeypatch.delenv("ASKLEDGER_LOG", raising=False)
    monkeypatch.chdir(tmp_path)
    pipeline.answer("How many customers live in Ashford?", TemplateGenerator())
    assert list(tmp_path.iterdir()) == []


def test_explain_reads_a_date_range():
    sql = (
        "SELECT SUM(amount) FROM expenses WHERE expense_date BETWEEN '2025-01-01' AND '2025-12-31'"
    )
    assert pipeline.explain(sql, {"expenses"}) == (
        "Added up from expenses, where expense_date is from 2025-01-01 to 2025-12-31."
    )
