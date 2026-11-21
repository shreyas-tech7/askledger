"""Load the frozen question set."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.jsonl"


@dataclass(frozen=True)
class Question:
    id: str
    family: str
    tier: int
    split: str
    ordered: bool
    question: str
    gold_sql: str


def load(split: str | None = None) -> list[Question]:
    rows = [Question(**json.loads(line)) for line in QUESTIONS_PATH.read_text().splitlines()]
    return [q for q in rows if split in (None, q.split)]
