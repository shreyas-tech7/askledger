"""The hostile suite: questions with prompt-injection text and the SQL a fooled model could write."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from askledger import safety
from askledger.db import DB_PATH

HOSTILE_PATH = Path(__file__).parent / "data" / "hostile.jsonl"

WRITE_TYPES = ("drop", "update", "delete", "insert", "create")

# Single layers for the defense-in-depth table. The time and row limits stay on in every
# setting, so a test run cannot hang.
LAYERS = {
    "full": dict(text=True, readonly=True, authorizer=True),
    "authorizer_only": dict(text=False, readonly=False, authorizer=True),
    "read_only_only": dict(text=False, readonly=True, authorizer=False),
    "text_only": dict(text=True, readonly=False, authorizer=False),
}


@dataclass(frozen=True)
class Attack:
    id: str
    attack_type: str
    question: str
    sql: str
    expected_reason: str


def load() -> list[Attack]:
    return [Attack(**json.loads(line)) for line in HOSTILE_PATH.read_text().splitlines()]


def outcome(sql: str, db_path: Path = DB_PATH, layers: str = "full", **limits) -> str:
    """Return the block reason, or "allowed" if the query ran."""
    try:
        safety.run_layers(sql, db_path, **LAYERS[layers], **limits)
    except safety.Blocked as e:
        return e.reason
    except safety.SQLError:
        return "sql_error"
    return "allowed"


def layer_matrix(time_limit_s: float = 0.5) -> list[dict]:
    """Run every attack against each layer alone, on a throwaway copy of the database."""
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for a in load():
            row = {"id": a.id, "attack_type": a.attack_type, "expected": a.expected_reason}
            for name in LAYERS:
                copy = Path(tmp) / f"{a.id}_{name}.db"
                shutil.copy(DB_PATH, copy)
                row[name] = outcome(a.sql, copy, name, time_limit_s=time_limit_s)
                copy.unlink()
            rows.append(row)
    return rows
