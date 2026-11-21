"""The LLM generator, tested with fake fixtures and a fake local server. No real provider."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from askledger import llm, pipeline

ANSWER = "Here you go:\n```sql\nSELECT COUNT(*) FROM customers WHERE city = 'Ashford';\n```"


def write(dirpath, qid, attempt, response):
    dirpath.mkdir(parents=True, exist_ok=True)
    rec = {"model": "fake", "prompt_sha": "x", "response": response, "recorded": "2026-01-01"}
    (dirpath / f"{qid}__a{attempt}.json").write_text(json.dumps(rec))


def test_extract_sql_takes_the_code_block_and_drops_the_semicolon():
    assert llm.extract_sql(ANSWER) == "SELECT COUNT(*) FROM customers WHERE city = 'Ashford'"
    assert llm.extract_sql("SELECT 1;") == "SELECT 1"
    assert llm.extract_sql("```sql\n```") is None


def test_replay_reads_fixtures_and_returns_none_when_missing(tmp_path):
    gen = llm.LLMGenerator("fake", fixtures=tmp_path)
    write(gen.dir, "q1", 0, ANSWER)
    gen.for_question("q1")
    assert gen.generate("How many customers live in Ashford?", ["customers"]).startswith("SELECT")
    gen.for_question("q2")
    assert gen.generate("anything", []) is None


def test_replay_runs_the_repair_attempt_from_its_own_fixture(tmp_path):
    gen = llm.LLMGenerator("fake", fixtures=tmp_path)
    write(gen.dir, "q1", 0, "```sql\nSELECT COUNT(*) FROM customer\n```")
    write(gen.dir, "q1", 1, ANSWER)
    a = pipeline.answer("How many customers live in Ashford?", gen, question_id="q1")
    assert a.ok and a.repairs == 1 and a.rows[0][0] > 0


def test_repair_prompt_carries_the_error_text():
    msgs = llm.prompt("q", ["customers"], sql="SELECT x", error="no such column: x")
    assert msgs[-1]["content"].startswith("SQLite returned this error:\nno such column: x")
    assert "customers" in msgs[1]["content"]


class _Fake(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Fake.seen.append((dict(self.headers), body))
        out = json.dumps({"choices": [{"message": {"content": ANSWER}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_server():
    server = HTTPServer(("127.0.0.1", 0), _Fake)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_record_mode_saves_a_fixture_without_the_key(tmp_path, fake_server, monkeypatch):
    monkeypatch.setenv("ASKLEDGER_LLM_API_KEY", "sk-test-not-a-real-key")
    gen = llm.LLMGenerator("fake", mode="record", fixtures=tmp_path, base_url=fake_server,
                           timeout_s=5)  # fmt: skip
    gen.for_question("q1")
    assert gen.generate("How many customers live in Ashford?", ["customers"]).startswith("SELECT")
    headers, body = _Fake.seen[-1]
    assert headers["Authorization"] == "Bearer sk-test-not-a-real-key"
    assert body["temperature"] == 0
    saved = (gen.dir / "q1__a0.json").read_text()
    assert "sk-test" not in saved and json.loads(saved)["response"] == ANSWER


def test_record_mode_needs_a_base_url(tmp_path, monkeypatch):
    monkeypatch.delenv("ASKLEDGER_LLM_BASE_URL", raising=False)
    gen = llm.LLMGenerator("fake", mode="record", fixtures=tmp_path)
    with pytest.raises(RuntimeError, match="BASE_URL"):
        gen.generate("q", [])


def test_no_fixture_for_the_real_model_is_committed_with_a_key():
    for path in llm.FIXTURES.rglob("*.json"):
        assert "Bearer" not in path.read_text() and "sk-" not in path.read_text()
