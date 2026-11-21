"""Runs that write the result files in results/. The README is written from these files only."""

from __future__ import annotations

import json
import platform
import random
import re
import sqlite3
import time
from pathlib import Path

from askledger import evaluate, hostile, linking, pipeline, questions
from askledger.errorfix import fix
from askledger.templates import TemplateGenerator

RESULTS = Path(__file__).resolve().parents[2] / "results"
REPAIR_BUDGETS = (0, 1, 2)

# Plausible wrong names, the kind a model writes when it guesses the schema.
MISTAKES = {
    "amount": "total_amount",
    "order_date": "date",
    "issue_date": "invoice_date",
    "expense_date": "spent_on",
    "payment_date": "paid_on",
    "unit_price": "price",
    "quantity": "qty",
    "category": "product_category",
    "segment": "customer_type",
    "channel": "sales_channel",
    "status": "order_status",
    "city": "location",
    "order_items": "order_lines",
    "expenses": "expense",
    "payments": "payment",
    "invoices": "invoice",
}


def meta(**extra) -> dict:
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "cpu": cpu, **extra}  # fmt: skip


def run_generator(make_generator, max_repairs: int, qs=None) -> list[dict]:
    records = []
    for q in qs or questions.load():
        gen = make_generator()
        start = time.perf_counter()
        a = pipeline.answer(q.question, gen, max_repairs=max_repairs, question_id=q.id)
        elapsed = time.perf_counter() - start
        ok = a.ok and evaluate.correct(a.sql, q)
        records.append({"id": q.id, "split": q.split, "tier": q.tier, "correct": ok,
                        "repairs": a.repairs, "error": a.error, "sql": a.sql,
                        "seconds": round(elapsed, 4)})  # fmt: skip
    return records


def template_results() -> dict:
    out = {"meta": meta(generator="template", model="none (rules)", seed="none (deterministic)"),
           "by_repairs": {}}  # fmt: skip
    for budget in REPAIR_BUDGETS:
        recs = run_generator(TemplateGenerator, budget)
        out["by_repairs"][str(budget)] = {
            "summary": evaluate.summarize(recs),
            "errors": sum(1 for r in recs if r["error"] and r["sql"]),
            "no_sql": sum(1 for r in recs if not r["sql"]),
            "repairs_used": sum(r["repairs"] for r in recs),
            "mean_seconds": sum(r["seconds"] for r in recs) / len(recs),
        }
        if budget == 2:
            out["records"] = recs
    return out


def corrupt(sql: str, rng: random.Random) -> tuple[str, list[str]]:
    present = [k for k in MISTAKES if re.search(rf"\b{k}\b", sql)]
    n = min(len(present), rng.choice([1, 2]))
    picked = rng.sample(present, n)
    for k in picked:
        sql = re.sub(rf"\b{k}\b", MISTAKES[k], sql)
    return sql, picked


class _Faulty:
    """Hands out a corrupted gold query, then repairs with the error-guided fixer."""

    name = "simulated-faults"

    def __init__(self, sql: str):
        self.sql = sql

    def generate(self, question, tables):
        return self.sql

    def repair(self, question, sql, error, tables):
        return fix(sql, error)


def repair_study(seed: int) -> dict:
    rng = random.Random(seed)
    cases = []
    for q in questions.load():
        bad, picked = corrupt(q.gold_sql, rng)
        if picked:
            cases.append((q, bad, picked))
    out = {"meta": meta(generator="simulated faults + error-guided fixer", model="none",
                        seed=seed), "cases": len(cases), "by_repairs": {}}  # fmt: skip
    for budget in REPAIR_BUDGETS:
        recs, valid_wrong = [], 0
        for q, bad, _ in cases:
            a = pipeline.answer(q.question, _Faulty(bad), max_repairs=budget, question_id=q.id)
            ok = a.ok and evaluate.correct(a.sql, q)
            valid_wrong += int(a.ok and not ok)
            recs.append({"split": q.split, "tier": q.tier, "correct": ok})
        k = sum(r["correct"] for r in recs)
        lo, hi = evaluate.wilson(k, len(recs))
        out["by_repairs"][str(budget)] = {"correct": k, "n": len(recs), "accuracy": k / len(recs),
                                          "ci95": [lo, hi], "valid_but_wrong": valid_wrong}  # fmt: skip
    return out


def llm_results(model: str) -> dict:
    from askledger.llm import LLMGenerator

    gen_dir = LLMGenerator(model).dir
    if not gen_dir.exists() or not any(gen_dir.glob("*.json")):
        return {"meta": meta(generator="llm", model=model, seed="temperature 0"),
                "status": "not run",
                "reason": f"no recorded fixtures in fixtures/llm/{gen_dir.name} "
                          "(see BLOCKERS.md for why)"}  # fmt: skip
    out = {"meta": meta(generator="llm", model=model, seed="temperature 0"), "status": "replayed",
           "by_repairs": {}}  # fmt: skip
    for budget in REPAIR_BUDGETS:
        recs = run_generator(lambda: LLMGenerator(model), budget)
        out["by_repairs"][str(budget)] = {"summary": evaluate.summarize(recs)}
    return out


def linking_results() -> dict:
    out = {"meta": meta(generator="bm25 linking", model="none", seed="none"), "recall": {}}
    for split in ("dev", "heldout"):
        qs = questions.load(split)
        out["recall"][split] = {str(k): linking.recall(qs, k) for k in (1, 2, 3, 4)}
        out.setdefault("n", {})[split] = len(qs)
    return out


def hostile_results() -> dict:
    rows = hostile.layer_matrix()
    return {"meta": meta(generator="hostile suite", model="none", seed="none"), "rows": rows}


def write_all(model: str = "llama-3.1-8b-instant") -> list[Path]:
    RESULTS.mkdir(exist_ok=True)
    files = {
        "template.json": template_results(),
        "llm.json": llm_results(model),
        "repair_study_seed1.json": repair_study(1),
        "repair_study_seed2.json": repair_study(2),
        "linking.json": linking_results(),
        "hostile.json": hostile_results(),
    }
    paths = []
    for name, data in files.items():
        p = RESULTS / name
        p.write_text(json.dumps(data, indent=2, default=str) + "\n")
        paths.append(p)
    return paths
