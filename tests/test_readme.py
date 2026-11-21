"""The README numbers come from results/*.json through `askledger readme`, never by hand."""

import json
import re

from askledger import hostile, report

# Numbers allowed in hand written prose: version, Python version, list markers, tier names,
# "95%" for the interval level, "10 minutes", BM25 and the 0 to 1 range.
ALLOWED = {"0.1.0", "3.11", "1.", "2.", "3.", "4.", "5.", "95%", "1", "2", "3", "10", "25", "0",
           "1,"}  # fmt: skip


def prose(text: str) -> str:
    text = re.sub(
        r"<!-- askledger:(\w+):start -->.*?<!-- askledger:\1:end -->", "", text, flags=re.S
    )
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`]*`", "", text)
    return re.sub(r"\]\([^)]*\)", "]", text)


def test_readme_and_page_match_the_result_files():
    assert report.write(check=True) == []


def test_render_puts_result_numbers_in_the_blocks():
    results = report.load()
    acc = results["template"]["by_repairs"]["2"]["summary"]["heldout/all"]
    text = report.render(report.README.read_text(), results)
    assert f"{acc['correct']}/{acc['n']}" in text


def test_render_changes_when_a_result_changes():
    results = report.load()
    results = json.loads(json.dumps(results))
    s = results["template"]["by_repairs"]["2"]["summary"]["dev/all"]
    s["correct"] -= 1
    assert report.render(report.README.read_text(), results) != report.README.read_text()


def test_no_typed_numbers_in_readme_prose():
    found = set(re.findall(r"\d[\d.,%]*", prose(report.README.read_text())))
    assert found <= ALLOWED, f"typed numbers: {sorted(found - ALLOWED)}"


def test_layer_claim_in_readme_matches_results():
    rows = report.load()["hostile"]["rows"]
    assert all(r["full"] != "allowed" for r in rows)
    for name in hostile.LAYERS:
        if name != "full":
            assert any(r[name] == "allowed" for r in rows), name
    assert "The full stack stops every attack. No single layer does." in report.README.read_text()
