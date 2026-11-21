# Project context: askledger

## What it is
askledger answers questions about a small business's sales and expenses by writing SQL.
It runs the SQL in a locked, read-only SQLite sandbox, shows the query next to the answer,
and measures accuracy against gold queries by running both and comparing results.

## Status
v0.1.0-rc1 build. See PROGRESS.md for what is done and what is next.

## Stack
Python 3.11+, standard library `sqlite3`, pytest, ruff. No SQL parser. No runtime dependency.

## Commands
- `./init.sh`: venv, install, lint, link check, all tests offline
- `askledger ask "question"`: answer one question (template baseline by default)
- `askledger eval`: run every generator setting and write `results/*.json`
- `askledger hostile`: run the hostile suite through the safety layer
- `askledger readme`: rewrite the README tables and docs/index.html from results (`--check` to verify)
- `askledger demo`: the short demo in docs/DEMO.md

## Layout
- `src/askledger/db.py`: seeded database generator. `data/ledger.db` is its output
- `src/askledger/data/questions.jsonl`: frozen questions and gold SQL (written by scripts/write_questions.py)
- `src/askledger/data/hostile.jsonl`: hostile suite with expected block reasons
- `src/askledger/safety.py`: read-only connection, authorizer, row and time limits
- `src/askledger/compare.py`: result comparison rules
- `src/askledger/linking.py`: BM25 schema linking
- `src/askledger/templates.py`: template baseline
- `src/askledger/llm.py`: LLM generator, record and replay
- `src/askledger/pipeline.py`: link, generate, run, repair, answer
- `src/askledger/evaluate.py`: execution accuracy, Wilson intervals
- `src/askledger/report.py`: README and results page writer
- `tests/`: offline tests. `conftest.py` blocks the network

## Rules
- Never edit questions.jsonl, hostile.jsonl or gold SQL to make a score go up.
- Never type numbers into the README. Run `askledger readme`.
- The safety layer is code. The read-only URI and the authorizer are always both on.
- Templates are built from dev questions only. Do not look at held-out questions when tuning.
- Run gitleaks before each commit.

## Skills that fit
superpowers test-driven-development, systematic-debugging, verification-before-completion,
requesting-code-review. Ponytail style (small plain code) by hand.

## Do not read
`.venv/`, `src/askledger/data/ledger.db` (binary), `docs/build/BUILD_PROMPT.md` unless resuming.
