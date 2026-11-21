# Plan

The brief in docs/build/BUILD_PROMPT.md is the spec. This plan follows its build order.
No question rounds were run. Assumptions are listed at the end and in DECISIONS.md.

## Steps

1. Initializer and database generator. `db.build(path, seed)` writes 8 tables with quirks.
   Test: rebuild gives the same dump hash, quirks exist.
2. Questions. `scripts/write_questions.py` writes 210 questions in 42 families with gold SQL.
   Freeze with a sha256. Test: hash, size, tiers, split by family, gold non-empty and
   deterministic under `reverse_unordered_selects`.
3. Eval harness. `compare.py` (multiset unless ordered, round floats to 2, ignore names) and
   `evaluate.py` (accuracy by tier and split, Wilson 95% intervals). Tests per rule.
4. Safety layer. `safety.py`: `file:...?mode=ro` URI, `set_authorizer` allowlist, progress
   handler for time, fetch cap for rows, one statement only. Hostile suite of 40+ items with
   expected reasons. Tests: every hostile SQL blocked with its reason, the authorizer alone
   blocks a write on a writable connection.
5. Schema linking. BM25 over table and column descriptions plus foreign-key closure.
   Test: recall against gold tables found by the authorizer's read log.
6. Template baseline. Regex shapes from dev families only, slots filled from the database
   vocabulary.
7. LLM generator. OpenAI-compatible chat client, record mode writes fixtures, replay mode
   reads them. Tests use a fake fixture set and never the network.
8. Repair loop. On an SQL error the generator gets the error text, up to 2 retries.
   Report accuracy with 0, 1 and 2 repairs.
9. Record run. Probe hosts first. If blocked, mark LLM rows "not run".
10. Report, README, study kit, release check, hand-off.

## Assumptions
- "Revenue" is order line totals after discount on orders that are not cancelled.
- The hard tier fallback is used only if a question is too hard for both generators. With
  no LLM run there is no second generator, so no hard tier is made (logged in DECISIONS.md).
- The template baseline may score near zero on held-out families. That is the honest result
  of a split by family.
