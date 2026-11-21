# Release check

Run on 2026-11-21 on the build machine, branch `claude/project-thread-kyehoy`. GitHub Actions could not be read from the build session, so every CI step ran locally.

| Check | How | Result |
| --- | --- | --- |
| Tests and lint | `./init.sh` (ruff check with S rules, ruff format, link check, pytest offline) | all checks passed |
| Generated files | `askledger readme --check` | up to date |
| Hostile suite | `askledger hostile` | every attack stopped with its expected outcome, three of them by a SQLite error (see README Limits) |
| Demo | `askledger demo` | runs, four hostile queries blocked |
| Secret scan | `gitleaks git -v .` on full history, plus `gitleaks git --pre-commit --redact --staged --verbose` before each commit | no leaks found |
| Dependency audit | `uvx pip-audit --path .venv/lib/python3.13/site-packages` | no known vulnerabilities. The package itself is not on PyPI, so it was skipped |
| Bandit rules | `ruff check --select S src scripts tests` | only S311 (seeded random for synthetic data and test faults), which is ignored on purpose in `pyproject.toml` |
| Workflow lint | `actionlint` | passes |
| Links | `scripts/check_links.py` | no broken local links or anchors. External links are listed, not fetched |
| Code review | a fresh reviewer subagent, by hand in the ponytail style (small plain code) | findings below |
| Security audit | a fresh subagent, focused on the SQL safety layer and the hostile suite, trying new attacks on a copy of the database | findings below |
| Outside check | a fresh subagent cloned the repo to `/tmp/outside-check`, ran `./init.sh` and checked every Done-means item without editing | findings below |
| Writing pass | humanizer rules by hand, enforced by `tests/test_repo.py::test_writing_rules` | passes |
| Clean tree | `git status --short` | empty after the final commit |

## Findings and fixes

| Finding | Source | Fix |
| --- | --- | --- |
| `docs/build/BUILD_PROMPT.md` was never committed, because `build/` in `.gitignore` also matched `docs/build/`. A fresh clone failed `./init.sh` | outside check | `.gitignore` now says `/build/`. The file is committed |
| Three file attacks counted as "blocked" though they fail as SQLite errors, which overstated the layer | outside check | the CLI and the attacks table now say how many were stopped by an error. A test proves the authorizer would deny those functions if they existed |
| The time limit could not interrupt one long GLOB call. A 4.8 KB query ran for 7 s against a 2 s limit | security audit | LIKE and GLOB patterns are capped at 200 characters and strings at 64 KB. A test proves a long pattern is refused fast |
| The row cap did not limit bytes. A short query could build hundreds of MB of result | security audit | rows are fetched one at a time and the result is refused past 2 MB. Tested |
| Two tests could never fail (a hash compared with itself, an `or` that was always true) | security audit | the hash test now compares the committed database with a fresh build. The other checks real fields |
| The text check read comments before strings, so `SELECT '--'; DELETE ...` hid the semicolon from it. Python's one statement rule still caught it | security audit | strings and comments are now read in one pass, left to right. Tested |
| The key could travel over plain HTTP, and urllib forwards it on a redirect | security audit | record mode needs https (plain http only to localhost for tests) and refuses redirects. Tested |
| `wilson(0, 0)` returned (0, 0) | security audit | returns (0, 1) |
| The LLM "not run" reason was fixed text | security audit | it now names the missing fixture folder and points to BLOCKERS.md |
| README Limits wording on the text check and the layer findings was muddled. DEMO could read as an LLM run | outside check | reworded |

Not changed: floats are compared after rounding to two decimals, as the brief asks. Two sums that differ by a tiny amount can still land on either side of a rounding boundary. No gold query hits this today, and the rule is written in the README.

## Done means

| Item | Status |
| --- | --- |
| Tests run offline and pass | true |
| Hostile suite of at least 40 questions, hostile SQL fed straight to the safety layer, all stopped | true |
| A test proves the authorizer blocks a write that passes every other check | true |
| README accuracy by tier with Wilson intervals, template and a recorded free model, dev and held-out | blocked with fallback: template rows only, LLM rows say "not run" with the reason |
| README accuracy with 0, 1 and 2 repairs | true |
| Every gold query non-empty and deterministic, tested | true |
| Quality bar, study kit, release check and hand-off | true |
