"""Turns the small markdown tables that report.py writes into HTML."""

from __future__ import annotations

import html
import re


def _inline(text: str) -> str:
    text = html.escape(text.strip())
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", text)


def to_html(md: str) -> str:
    lines = [ln for ln in md.strip().splitlines() if ln.startswith("|")]
    head = [c for c in lines[0].strip("|").split("|")]
    out = ["<table>", "<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr>"]
    for ln in lines[2:]:
        cells = ln.strip().strip("|").split("|")
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)
