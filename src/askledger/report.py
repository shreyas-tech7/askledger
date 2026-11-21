"""Writes the README tables and docs/index.html from results/*.json. Never by hand."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from askledger import hostile
from askledger.experiments import RESULTS

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
PAGE = ROOT / "docs" / "index.html"
BLOCK = re.compile(r"(<!-- askledger:(\w+):start -->\n)(.*?)(<!-- askledger:\2:end -->)", re.S)
SPLITS = (("dev", "dev (140)"), ("heldout", "held-out (70)"))


def load() -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted(RESULTS.glob("*.json"))}


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def cell(s: dict) -> str:
    lo, hi = s["ci95"]
    return f"{s['correct']}/{s['n']} = {pct(s['accuracy'])} [{pct(lo)}, {pct(hi)}]"


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def accuracy(r: dict) -> str:
    rows = []
    t = r["template"]["by_repairs"]["2"]["summary"]
    for split, label in SPLITS:
        rows.append(["template baseline", label]
                    + [cell(t[f"{split}/tier{n}"]) for n in (1, 2, 3)] + [cell(t[f"{split}/all"])])  # fmt: skip
    llm = r["llm"]
    for split, label in SPLITS:
        if llm["status"] == "not run":
            rows.append([f"LLM `{llm['meta']['model']}`", label] + ["not run"] * 4)
        else:
            s = llm["by_repairs"]["2"]["summary"]
            rows.append([f"LLM `{llm['meta']['model']}`", label]
                        + [cell(s[f"{split}/tier{n}"]) for n in (1, 2, 3)] + [cell(s[f"{split}/all"])])  # fmt: skip
    return table(["generator", "split", "tier 1", "tier 2", "tier 3", "all"], rows)


def repairs(r: dict) -> str:
    rows = []
    for b in ("0", "1", "2"):
        s = r["template"]["by_repairs"][b]
        rows.append(["template baseline, all 210", b, cell(s["summary"]["dev/all"]) + " dev, "
                     + cell(s["summary"]["heldout/all"]) + " held-out", str(s["repairs_used"]),
                     "0"])  # fmt: skip
    for name in sorted(k for k in r if k.startswith("repair_study")):
        study = r[name]
        for b in ("0", "1", "2"):
            s = study["by_repairs"][b]
            rows.append([f"simulated faults, seed {study['meta']['seed']}", b, cell(s), "",
                         str(s["valid_but_wrong"])])  # fmt: skip
    return table(["run", "max repairs", "correct", "repairs used", "valid SQL, wrong answer"],
                 rows)  # fmt: skip


def linking(r: dict) -> str:
    rec = r["linking"]["recall"]
    rows = [[f"{label}", *(pct(rec[split][k]) for k in ("1", "2", "3", "4"))]
            for split, label in SPLITS]  # fmt: skip
    return table(["split", "recall@1", "recall@2", "recall@3", "recall@4"], rows)


def attacks(r: dict) -> str:
    rows_in = r["hostile"]["rows"]
    by_type: dict[str, list[dict]] = {}
    for row in rows_in:
        by_type.setdefault(row["attack_type"], []).append(row)
    rows = []
    for kind, items in sorted(by_type.items()):
        reasons = sorted({i["full"] for i in items})
        blocked = sum(i["full"] == i["expected"] for i in items)
        rows.append([kind, str(len(items)), f"{blocked}/{len(items)}", ", ".join(reasons)])
    total = sum(r_["full"] == r_["expected"] for r_ in rows_in)
    errors = sum(r_["full"] == "sql_error" for r_ in rows_in)
    rows.append(["**all**", str(len(rows_in)), f"{total}/{len(rows_in)}",
                 f"{errors} stopped by a SQLite error, not by the layer"])  # fmt: skip
    return table(["attack type", "questions", "stopped as expected", "outcome"], rows)


def layers(r: dict) -> str:
    rows_in = r["hostile"]["rows"]
    rows = []
    for name in hostile.LAYERS:
        stopped = sum(row[name] not in ("allowed",) for row in rows_in)
        writes = [row for row in rows_in if row["attack_type"] in hostile.WRITE_TYPES]
        w = sum(row[name] != "allowed" for row in writes)
        rows.append([f"`{name}`", f"{stopped}/{len(rows_in)}", f"{w}/{len(writes)}"])
    return table(
        [
            "layers on",
            "attacks stopped",
            "write attacks stopped (" + ", ".join(hostile.WRITE_TYPES) + ")",
        ],
        rows,
    )


def cost(r: dict) -> str:
    t = r["template"]["by_repairs"]["2"]
    llm = r["llm"]
    rows = [["template baseline", "0", f"{1000 * t['mean_seconds']:.1f} ms", "none"]]
    if llm["status"] == "not run":
        rows.append([f"LLM `{llm['meta']['model']}`", "not run", "not run", "not run"])
    return table(["generator", "API cost per question (USD)", "mean time per question",
                  "network"], rows)  # fmt: skip


def run_info(r: dict) -> str:
    m = r["template"]["meta"]
    return (f"Measured on {m['date']} with Python {m['python']}, SQLite {m['sqlite']}, on "
            f"{m['cpu']}. Simulated-fault seeds: "
            + ", ".join(str(r[k]["meta"]["seed"]) for k in sorted(r) if k.startswith("repair_study"))
            + ". LLM status: " + r["llm"]["status"] + ".\n")  # fmt: skip


BLOCKS = {"accuracy": accuracy, "repairs": repairs, "linking": linking, "attacks": attacks,
          "layers": layers, "cost": cost, "runinfo": run_info}  # fmt: skip


def render(text: str, results: dict) -> str:
    def sub(m):
        return m.group(1) + BLOCKS[m.group(2)](results) + m.group(4)

    return BLOCK.sub(sub, text)


def page(results: dict) -> str:
    """A static page that opens from disk. Tables only, no scripts."""
    from askledger.mdtable import to_html

    parts = [
        to_html(BLOCKS[name](results)) for name in ("accuracy", "repairs", "attacks", "layers")
    ]
    titles = ["Execution accuracy by tier (95% Wilson intervals)", "Repair budget",
              "Hostile suite by attack type", "Each layer alone"]  # fmt: skip
    body = "\n".join(f"<h2>{html.escape(t)}</h2>\n{p}" for t, p in zip(titles, parts, strict=True))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>askledger results</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{font-family:system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;
color:#1b1f24;background:#fff}}table{{border-collapse:collapse;margin:1rem 0;font-size:.9rem}}
td,th{{border:1px solid #ccd;padding:.3rem .5rem;text-align:left}}th{{background:#eef}}
@media (prefers-color-scheme: dark){{body{{color:#e6e6e6;background:#16181c}}
th{{background:#262a33}}td,th{{border-color:#444}}}}
</style></head><body>
<h1>askledger results</h1>
<p>{html.escape(run_info(results))}</p>
{body}
<p>Written by <code>askledger readme</code> from <code>results/*.json</code>.</p>
</body></html>
"""


def write(check: bool = False) -> list[str]:
    """Rewrite README blocks and the page. With check, return the files that are stale."""
    results = load()
    stale = []
    for path, new in ((README, render(README.read_text(), results)), (PAGE, page(results))):
        old = path.read_text() if path.exists() else ""
        if old != new:
            stale.append(str(path.relative_to(ROOT)))
            if not check:
                path.parent.mkdir(exist_ok=True)
                path.write_text(new)
    return stale
