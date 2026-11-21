"""Result comparison rules for execution accuracy.

1. Compare rows as multisets, unless the question asks for an order. Then order counts.
2. Round every number to 2 decimals. Integers and floats that round the same are equal.
3. Ignore column names. The number and order of columns still count.
"""

from __future__ import annotations

from collections import Counter


def _value(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int | float):
        r = round(float(v), 2)
        return 0.0 if r == 0 else r  # -0.0 and 0.0 are the same answer
    return v


def normalize(rows) -> list[tuple]:
    return [tuple(_value(v) for v in row) for row in rows]


def same_result(predicted, gold, ordered: bool) -> bool:
    p, g = normalize(predicted), normalize(gold)
    if ordered:
        return p == g
    return Counter(p) == Counter(g)
