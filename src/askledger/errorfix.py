"""Error-guided repair without a model.

SQLite names the first bad identifier in its error text. This module swaps it for the
closest real name in the schema. It is the template baseline's repair step, and the repair
step of the simulated-fault study. It can also make things worse: the closest name can be
a real column with the wrong meaning, which gives a valid query and a wrong answer.
"""

from __future__ import annotations

import difflib
import re

from askledger import schema
from askledger.safety import ALLOWED_FUNCTIONS

TABLE_NAMES = sorted(schema.TABLES)
COLUMN_NAMES = sorted({c for _, cols in schema.TABLES.values() for c in cols})

PATTERNS = [
    (re.compile(r"no such column: (?:\w+\.)?(\w+)"), COLUMN_NAMES),
    (re.compile(r"no such table: (?:\w+\.)?(\w+)"), TABLE_NAMES),
    (re.compile(r"no such function: (\w+)"), sorted(ALLOWED_FUNCTIONS)),
]


def closest(word: str, names: list[str]) -> str | None:
    hits = difflib.get_close_matches(word.lower(), names, n=1, cutoff=0.4)
    if hits:
        return hits[0]
    parts = [n for n in names if word.lower() in n or n in word.lower()]
    return parts[0] if parts else None


def columns_in_scope(sql: str) -> list[str]:
    """Columns of the tables the query names. Falls back to every column."""
    named = [t for t in TABLE_NAMES if re.search(rf"\b{t}\b", sql)]
    cols = sorted({c for t in named for c in schema.TABLES[t][1]})
    return cols or COLUMN_NAMES


def fix(sql: str, error: str) -> str | None:
    """Return a changed query, or None when the error gives nothing to fix."""
    for pattern, names in PATTERNS:
        m = pattern.search(error)
        if not m:
            continue
        bad = m.group(1)
        if names is COLUMN_NAMES:
            names = columns_in_scope(sql)
        good = closest(bad, names)
        if not good or good == bad:
            return None
        new = re.sub(rf"\b{re.escape(bad)}\b", good, sql)
        return new if new != sql else None
    return None
