"""Schema linking: BM25 over table and column descriptions picks the tables a question needs.

Then the foreign-key graph adds any table that sits between two picked tables, so the
picked set can always be joined.
"""

from __future__ import annotations

import math
import re
from collections import Counter, deque

from askledger import schema

STOP = set(
    "a an and are as at by did do does each for from had has have how in is it of on or our the their to was we were what when which who with".split()
)


def tokens(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def _documents() -> dict[str, list[str]]:
    docs = {}
    for table, (text, cols) in schema.TABLES.items():
        words = [table.replace("_", " "), text]
        words += [c.replace("_", " ") + " " + d for c, d in cols.items()]
        docs[table] = tokens(" ".join(words))
    return docs


class BM25:
    def __init__(self, docs: dict[str, list[str]], k1: float = 1.2, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.avg = sum(len(d) for d in docs.values()) / len(docs)
        df = Counter(w for d in docs.values() for w in set(d))
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.tf = {name: Counter(d) for name, d in docs.items()}

    def scores(self, query: list[str]) -> dict[str, float]:
        out = {}
        for name, tf in self.tf.items():
            length = len(self.docs[name])
            s = 0.0
            for w in query:
                if w in tf:
                    f = tf[w]
                    s += (
                        self.idf[w]
                        * f
                        * (self.k1 + 1)
                        / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
                    )
            out[name] = s
        return out


_INDEX = BM25(_documents())


def _graph() -> dict[str, set[str]]:
    g = {t: set() for t in schema.TABLES}
    for a, b in schema.JOINS:
        g[a].add(b)
        g[b].add(a)
    return g


def _path(a: str, b: str) -> list[str]:
    g, seen, q = _graph(), {a: None}, deque([a])
    while q:
        cur = q.popleft()
        if cur == b:
            break
        for nxt in sorted(g[cur]):
            if nxt not in seen:
                seen[nxt] = cur
                q.append(nxt)
    path, cur = [], b
    while cur is not None:
        path.append(cur)
        cur = seen.get(cur)
    return path


def link(question: str, k: int = 3) -> list[str]:
    """Top-k tables by BM25, plus the tables on join paths between them."""
    scores = _INDEX.scores(tokens(question))
    ranked = sorted(scores, key=lambda t: (-scores[t], t))
    picked = [t for t in ranked[:k] if scores[t] > 0] or ranked[:1]
    out = set(picked)
    for t in picked[1:]:
        out.update(_path(picked[0], t))
    return sorted(out)


def gold_tables(sql: str) -> set[str]:
    return {t for t in schema.TABLES if re.search(rf"\b{t}\b", sql)}


def recall(qs, k: int = 3) -> float:
    """Share of questions whose linked tables cover every table the gold query uses."""
    hits = sum(gold_tables(q.gold_sql) <= set(link(q.question, k)) for q in qs)
    return hits / len(qs)
