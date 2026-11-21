"""Execution accuracy: run the predicted SQL and the gold SQL, compare the results."""

from __future__ import annotations

import math
from collections import defaultdict

from askledger import safety
from askledger.compare import same_result


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def correct(predicted_sql: str | None, question) -> bool:
    if not predicted_sql:
        return False
    try:
        predicted = safety.run(predicted_sql).rows
    except (safety.Blocked, safety.SQLError):
        return False
    return same_result(predicted, safety.run(question.gold_sql).rows, question.ordered)


def summarize(records: list[dict]) -> dict:
    """Group records (with split, tier, correct) into accuracy cells with intervals."""
    cells = defaultdict(lambda: [0, 0])
    for r in records:
        for key in (f"{r['split']}/tier{r['tier']}", f"{r['split']}/all"):
            cells[key][0] += int(r["correct"])
            cells[key][1] += 1
    out = {}
    for key, (k, n) in sorted(cells.items()):
        lo, hi = wilson(k, n)
        out[key] = {"correct": k, "n": n, "accuracy": k / n, "ci95": [lo, hi]}
    return out
