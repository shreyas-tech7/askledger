"""Command line: askledger ask | sql | eval | record | hostile | readme | demo."""

from __future__ import annotations

import argparse
import os
import sys

from askledger import hostile, pipeline, report, safety
from askledger.templates import TemplateGenerator

DEFAULT_MODEL = os.environ.get("ASKLEDGER_LLM_MODEL", "llama-3.1-8b-instant")

DEMO_QUESTIONS = [
    "How many customers live in Ashford?",
    "Who were our top 3 customers by invoiced amount in 2025?",
    "What was our cash profit in March 2025, meaning payments received minus expenses?",
]
DEMO_SQL = [
    "DELETE FROM invoices",
    "SELECT name FROM customers; DROP TABLE customers",
    "WITH x AS (SELECT 1) UPDATE customers SET email = NULL",
    "SELECT load_extension('/tmp/evil.so')",
]


def _generator(args):
    if args.generator == "llm":
        from askledger.llm import LLMGenerator

        return LLMGenerator(args.model, mode=args.mode)
    return TemplateGenerator()


def show(a: pipeline.Answer, out=None) -> None:
    out = out or sys.stdout
    print(f"Q: {a.question}", file=out)
    if a.sql:
        print(f"SQL: {a.sql}", file=out)
    if not a.ok:
        print(f"Not answered: {a.error}", file=out)
        return
    print(" | ".join(a.columns), file=out)
    for row in a.rows[:20]:
        print(" | ".join(str(v) for v in row), file=out)
    if len(a.rows) > 20:
        print(f"... {len(a.rows) - 20} more rows", file=out)
    note = (
        f" ({a.repairs} repair)"
        if a.repairs == 1
        else f" ({a.repairs} repairs)"
        if a.repairs
        else ""
    )
    print(f"Why: {a.explanation}{note}", file=out)


def cmd_ask(args) -> int:
    a = pipeline.answer(args.question, _generator(args), max_repairs=args.max_repairs)
    show(a)
    return 0 if a.ok else 1


def cmd_eval(args) -> int:
    from askledger import experiments

    for path in experiments.write_all(args.model):
        print(f"wrote {path.relative_to(report.ROOT)}")
    return 0


def cmd_record(args) -> int:
    """Call a real model once per question and attempt, saving fixtures for replay."""

    from askledger import questions
    from askledger.llm import LLMGenerator

    if not os.environ.get("ASKLEDGER_LLM_BASE_URL"):
        print("set ASKLEDGER_LLM_BASE_URL and a key first (see .env.example)")
        return 2
    for q in questions.load():
        gen = LLMGenerator(args.model, mode="record")
        a = pipeline.answer(q.question, gen, max_repairs=2, question_id=q.id)
        print(f"{q.id} {'ok' if a.ok else 'not answered'}")
    print("now run `askledger eval` and `askledger readme`")
    return 0


def cmd_hostile(args) -> int:
    attacks = hostile.load()
    bad = 0
    for atk in attacks:
        got = hostile.outcome(atk.sql)
        ok = got == atk.expected_reason
        bad += not ok
        word = "MISMATCH" if not ok else "error" if got == "sql_error" else "blocked"
        print(f"{atk.id} {atk.attack_type:<12} {word} {got}")
    errors = sum(a.expected_reason == "sql_error" for a in attacks)
    print(f"{len(attacks) - bad}/{len(attacks)} stopped with the expected outcome "
          f"({errors} of them by a SQLite error, not by the layer)")  # fmt: skip
    return 1 if bad else 0


def cmd_readme(args) -> int:
    stale = report.write(check=args.check)
    if args.check and stale:
        print("stale, run `askledger readme`: " + ", ".join(stale))
        return 1
    print("up to date" if not stale else "rewrote " + ", ".join(stale))
    return 0


def cmd_sql(args) -> int:
    """Run raw SQL through the safety layer, as hostile SQL from a model would arrive."""
    try:
        result = safety.run(args.sql)
    except safety.Blocked as e:
        print(f"BLOCKED {e.reason}: {args.sql}")
        return 1
    except safety.SQLError as e:
        print(f"SQL error: {e}")
        return 1
    print(" | ".join(result.columns))
    for row in result.rows[:20]:
        print(" | ".join(str(v) for v in row))
    return 0


def cmd_demo(args) -> int:
    gen = TemplateGenerator()
    for q in DEMO_QUESTIONS:
        show(pipeline.answer(q, gen))
        print()
    print("Hostile SQL sent straight to the safety layer:")
    for sql in DEMO_SQL:
        cmd_sql(argparse.Namespace(sql=sql))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="askledger", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    ask = sub.add_parser("ask", help="answer one question")
    ask.add_argument("question")
    ask.add_argument("--generator", choices=["template", "llm"], default="template")
    ask.add_argument("--model", default=DEFAULT_MODEL)
    ask.add_argument("--mode", choices=["replay", "record"], default="replay")
    ask.add_argument("--max-repairs", type=int, default=2)
    ev = sub.add_parser("eval", help="run every setting and write results/*.json")
    ev.add_argument("--model", default=DEFAULT_MODEL)
    raw = sub.add_parser("sql", help="run raw SQL through the safety layer")
    raw.add_argument("sql")
    rec = sub.add_parser("record", help="record a real model's answers as fixtures (network)")
    rec.add_argument("--model", default=DEFAULT_MODEL)
    sub.add_parser("hostile", help="run the hostile suite through the safety layer")
    rd = sub.add_parser("readme", help="write README tables and docs/index.html from results")
    rd.add_argument("--check", action="store_true", help="fail if they are out of date")
    sub.add_parser("demo", help="answer a few questions, one of them hostile")
    args = p.parse_args(argv)
    handler = {"ask": cmd_ask, "eval": cmd_eval, "hostile": cmd_hostile, "readme": cmd_readme,
               "demo": cmd_demo, "sql": cmd_sql, "record": cmd_record}[args.cmd]  # fmt: skip
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
