# Decisions

One line per choice: the options, the pick and the reason.

- 2026-11-21 Name: `askledger` (backup `ledgerql`). PyPI and npm both answered 404 for askledger today, and no well-known GitHub project uses the name. It matches the repo, so no rename step.
- 2026-11-21 Branch: the brief asked for `claude/build-askledger`, but this session may push only to `claude/project-thread-kyehoy`. Picked the allowed branch, so pushes work.
- 2026-11-21 Database: one invented coffee roaster ("Juniper Lane Coffee"), 18 months (2025-01 to 2026-06), seed 2026. A coffee shop has every table the brief names and is easy to explain.
- 2026-11-21 Names: built from syllables, so no row matches a real person.
- 2026-11-21 Revenue: order line quantity x unit_price x (1 - discount). Questions that use it say "not counting cancelled orders" in the text, so the gold answer is not a guess about intent.
- 2026-11-21 Question set: 42 families of 5 questions (210). Options: hand-write 210 one by one, or write families with fixed shapes and parameters. Families make the gold SQL easy to check and still give 210 real questions.
- 2026-11-21 Split: by family, seed 7. 10 of 14 tier-1 families, 9 of 14 tier-2 and 9 of 14 tier-3 go to dev (140 questions). Options were a random split by question or by family. By family means a held-out question shape never appears in dev, so held-out shows generalization, not memory of a shape.
- 2026-11-21 Gold determinism: tested with `PRAGMA reverse_unordered_selects` on a rebuilt database, which exposes any answer that depends on scan order.
- 2026-11-21 Fixed counts: execution accuracy over a fixed question set gets a Wilson interval because it estimates accuracy on questions like these. Counts of blocked hostile queries are fixed counts and get no interval.
