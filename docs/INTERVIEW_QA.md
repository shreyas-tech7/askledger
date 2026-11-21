# Interview questions and answers

Each answer points to the code and to the result that backs it. Results live in `results/*.json` and the README tables written from them.

**1. Why score by execution accuracy and not by matching the SQL text?**
Many different queries give the same right answer. `SUM(amount)` with a join and a subquery with `IN` can both be correct, and string match would fail one of them. Execution accuracy runs both queries and compares rows (`evaluate.correct`, `compare.same_result`). The catch is that two wrong queries can agree by luck on one database, which is why every gold query is checked for determinism (`tests/test_questions.py`).

**2. How exactly are results compared?**
Rows become multisets unless the question asks for an order. Floats round to two decimals, booleans become integers, and column names are ignored while column order is kept (`compare.normalize`, `compare.same_result`). The rules are in the README section "How results are compared" and tested in `tests/test_compare.py`.

**3. Why must safety sit below the model and not in the prompt?**
A prompt is a request, and prompt injection is text that changes the request. Anything the model can be talked into, an attacker can talk it into. The safety layer in `safety.py` is code that SQLite enforces, so it holds even if the model writes `DELETE FROM invoices`. The hostile test sends hostile SQL straight to the layer with no model at all (`tests/test_hostile.py`).

**4. What does `set_authorizer` do?**
SQLite calls the authorizer for every action a statement will take while it compiles the statement: each table read, each function, each write, ATTACH and PRAGMA. The callback returns OK, DENY or IGNORE. `_Guard.authorize` returns OK only for SELECT, recursive CTEs, reads of the eight ledger tables and allowlisted functions, and denies the rest with a reason. Because it runs at compile time, a denied statement never touches the file.

**5. If the connection is already read-only, why also use an authorizer?**
The layer table in the README shows it. The read-only URI alone still allows `CREATE TEMP TABLE`, `SAVEPOINT`, schema reads from `sqlite_master` and pragma table functions. The authorizer alone stops every write in the suite. `tests/test_safety.py::test_authorizer_alone_blocks_a_write` turns every other layer off and proves it.

**6. What does the safety layer not stop?**
A legal read can return every customer row with names and emails. The data here is synthetic, so that is acceptable for a demo. A real system needs row level rules per user and a column allowlist. The README "The safety layer" section says this plainly.

**7. How do you stop a query that never ends?**
`set_progress_handler` calls `_Guard.progress` every thousand virtual machine steps, and it returns 1 once the deadline passes, which makes SQLite raise "interrupted". The row cap fetches one row past the limit and refuses the result. SQLite limits cap string length, so `randomblob` style bombs fail with "too big". See the "endless" rows in the hostile table.

**8. When does repair help and when does it hurt?**
It helps when the error names the problem, like "no such column: qty", and the closest real name is the right one. It hurts when the closest real name is wrong, because then the query runs and returns a confident wrong answer. The simulated-fault study counts both, in the "valid SQL, wrong answer" column of the repair table (`experiments.repair_study`, `errorfix.fix`).

**9. Why does the template baseline do so well on dev and badly on held-out?**
The templates were written by reading the dev questions, so they match those shapes. The split is by question family (`scripts/write_questions.py`, `build`), so held-out shapes never appear in dev. The gap is the honest measure of how little a rule system generalizes. See the accuracy table.

**10. Why Wilson intervals?**
The held-out set has a few dozen questions per tier. With small counts and rates near 0 or 1, the normal approximation gives ranges outside 0 to 1 or of zero width. Wilson stays inside and is still simple (`evaluate.wilson`). Counts of blocked attacks get no interval because they are a fixed list, not a sample.

**11. How does schema linking work and how good is it?**
`linking.link` ranks table descriptions with BM25 and keeps the top three, then adds the tables on the foreign key path between them so joins are possible. The linking table reports recall at k. Missing a table is worse than adding one, so the LLM prompt gets the joined set.

**12. How do you test an LLM generator without calling an LLM?**
Record and replay. In record mode `LLMGenerator._call` posts to the provider and saves each reply as a fixture. In replay mode it reads the fixture, so tests and `askledger eval` are offline. `tests/test_llm.py` also runs record mode against a fake server on 127.0.0.1 and checks the key is sent in the header and never saved.

**13. How do you keep the README honest?**
Every number in it comes from `results/*.json` through `report.write`. `tests/test_readme.py` fails if the README and the result files disagree, and also fails if a number appears in hand written prose.

**14. What makes the gold SQL trustworthy?**
Each family's SQL is written once and filled with parameters, so one review covers five questions. Tests check that every gold query runs, returns at least one non-null row, and returns the same rows on a freshly built database with `PRAGMA reverse_unordered_selects` on, which exposes any answer that depends on scan order.

**15. What would you build next?**
Record a real free model and fill the LLM row. Add row level rules to the safety layer. Add a "show your work" mode that prints the linked tables and each repair attempt. Grow the database with a messier second business to see how linking degrades.
