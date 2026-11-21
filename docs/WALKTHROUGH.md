# Walkthrough

A guided read of the code in the order a question travels. Each step names the file and function to open.

## 1. The data

`src/askledger/db.py` builds the ledger from seed 2026. `build()` writes eight tables for an invented coffee roaster over 18 months. The quirks are on purpose: refunds are negative payments, some wholesale invoices are paid in parts or not at all, "House Blend" used to be called "Morning Blend", and Candles stopped selling halfway through. `content_hash()` hashes a dump of the file, so a test can prove an attack changed nothing.

## 2. The questions

`scripts/write_questions.py` holds 42 question families. Each family has a tier, a SQL template and five parameter sets, which gives five real questions with gold SQL. `build()` splits whole families into dev and held-out with seed 7, so a held-out question shape never appears in dev. The output is frozen in `src/askledger/data/questions.jsonl`, and `tests/test_questions.py` checks its hash, that the writer still reproduces it, and that every gold query is non-empty and gives the same rows when SQLite scans tables in reverse order.

## 3. Linking

`src/askledger/linking.py`: `link()` scores each table's description against the question with the `BM25` class, keeps the top three, then walks the foreign key graph in `_path()` to add any table that sits between them. `recall()` measures how often the gold tables are all in the top k.

## 4. Generating SQL

`src/askledger/templates.py`: `TemplateGenerator.generate()` calls `_generate()`, a list of regular expressions that each match one question shape and return fixed SQL. Slot values (cities, categories, names) come from `vocab()`, which reads them from the database and keeps only values that match `SAFE_VALUE`, so no quote can reach the SQL text.

`src/askledger/llm.py`: `LLMGenerator` builds a prompt with `prompt()`, the linked tables from `schema.prompt_schema()` and, on a repair, the failed SQL and SQLite's error text. In replay mode `_ask()` reads `fixtures/llm/<model>/<question id>__a<attempt>.json`. In record mode `_call()` posts to the chat completions endpoint and saves the reply. The key never reaches the fixture.

## 5. The safety layer

`src/askledger/safety.py` is the part to read slowly.

- `text_check()` refuses more than one statement, anything over the length limit and anything that does not start with SELECT or WITH.
- `_connect()` opens a `file:<path>?mode=ro` URI, turns extension loading off, sets SQLite limits and installs `_Guard.authorize` and `_Guard.progress`.
- `_Guard.authorize()` is called by SQLite for every action a statement will take. It returns OK only for SELECT, recursive CTEs, reads of the eight ledger tables and functions on `ALLOWED_FUNCTIONS`. Everything else is denied with a reason.
- `_Guard.progress()` interrupts a query that runs past the time limit. It runs between SQLite steps, so it cannot stop one long GLOB call. That is why `_connect()` also caps LIKE and GLOB patterns at `MAX_PATTERN` characters.
- `_execute()` fetches one row at a time, stops at one row past the cap or past `MAX_RESULT_BYTES`, and maps each SQLite error to a `Blocked` reason or an `SQLError`.
- `run()` turns every layer on. `run_layers()` exists only so tests and the layer table can turn layers off.

## 6. The pipeline and repair

`src/askledger/pipeline.py`: `answer()` links, generates, runs and, on an `SQLError`, asks the generator to repair until `max_repairs` is used up. A `Blocked` query is never repaired, because a refusal is not a typo. `explain()` builds the one line explanation from the SQL text.

`src/askledger/errorfix.py`: `fix()` reads the bad name out of SQLite's error and swaps in the closest real name from `columns_in_scope()`. It is the template baseline's repair step and the fixer in the simulated-fault study.

## 7. Scoring

`src/askledger/compare.py`: `same_result()` compares rows as multisets unless the question is ordered, after `normalize()` rounds floats to two decimals. `src/askledger/evaluate.py`: `correct()` runs the prediction and the gold query through the safety layer and compares them. `summarize()` groups by split and tier and adds `wilson()` intervals.

## 8. Experiments and the README

`src/askledger/experiments.py`: `write_all()` runs the template baseline at repair budgets 0, 1 and 2, the LLM replay (or marks it "not run"), the simulated-fault study for two seeds, linking recall and the hostile layer matrix, and writes `results/*.json`. `src/askledger/report.py`: `write()` turns those files into the README tables and `docs/index.html`. `tests/test_readme.py` fails if they drift.

## 9. The hostile suite

`scripts/write_hostile.py` writes `src/askledger/data/hostile.jsonl`. `src/askledger/hostile.py`: `outcome()` runs one attack, and `layer_matrix()` runs every attack with each layer alone on a throwaway copy. `tests/test_hostile.py` checks every attack gets its expected reason and the database hash does not change.
