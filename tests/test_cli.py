from askledger import cli


def test_ask_prints_sql_table_and_why(capsys):
    assert cli.main(["ask", "How many customers live in Ashford?"]) == 0
    out = capsys.readouterr().out
    assert "SQL: SELECT" in out and "Why: Counted" in out


def test_ask_fails_cleanly_when_nothing_fits(capsys):
    assert cli.main(["ask", "Write a haiku"]) == 1
    assert "Not answered" in capsys.readouterr().out


def test_sql_blocks_a_write(capsys):
    assert cli.main(["sql", "DELETE FROM invoices"]) == 1
    assert "BLOCKED not_select" in capsys.readouterr().out


def test_hostile_command_blocks_everything(capsys):
    assert cli.main(["hostile"]) == 0
    assert "55/55 blocked" in capsys.readouterr().out


def test_demo_runs(capsys):
    assert cli.main(["demo"]) == 0
    assert capsys.readouterr().out.count("BLOCKED") == len(cli.DEMO_SQL)


def test_record_refuses_without_a_provider(capsys, monkeypatch):
    monkeypatch.delenv("ASKLEDGER_LLM_BASE_URL", raising=False)
    assert cli.main(["record"]) == 2
    assert "ASKLEDGER_LLM_BASE_URL" in capsys.readouterr().out
