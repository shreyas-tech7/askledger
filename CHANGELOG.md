# Changelog

## v0.1.0-rc1 (2026-11-21)

Release commit: RELEASE_SHA_PLACEHOLDER

First release candidate.

- Synthetic SQLite ledger for an invented coffee roaster: customers, products, orders, order items, invoices, payments, expenses and employees, with refunds, partial payments, a renamed product and a discontinued category.
- 210 frozen questions with gold SQL in three tiers, split by question family into dev and held-out.
- Execution accuracy with multiset comparison, rounding to two decimals and Wilson intervals.
- Safety layer: text checks, a read-only URI, a `set_authorizer` allowlist, a time limit, a row cap and SQLite limits.
- Hostile suite of prompt injection questions with expected block reasons, and a table of what each layer stops alone.
- BM25 schema linking with join closure, a template baseline, an LLM generator with record mode and fixture replay, and a repair loop with at most two retries.
- Simulated-fault study that measures when repair helps and when it makes a valid but wrong query.
- CLI: `ask`, `sql`, `eval`, `hostile`, `readme` and `demo`. README tables and `docs/index.html` are written from `results/*.json`.
