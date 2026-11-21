"""Template baseline: regular expressions for common question shapes, then fixed SQL.

Built by reading the development questions only. Slot values (cities, categories, names)
come from the database itself, not from the questions. A question that fits no shape gets
no SQL, which counts as wrong.
"""

from __future__ import annotations

import re
import sqlite3
from functools import cache

from askledger import errorfix
from askledger.db import DB_PATH

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]  # fmt: skip
ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}
LINE = "oi.quantity * oi.unit_price * (1 - COALESCE(oi.discount, 0))"
COUNT = r"\b(how many|count|number of|order count)\b"


@cache
def vocab() -> dict[str, list[str]]:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    def col(sql):
        return sorted({r[0] for r in con.execute(sql) if r[0]}, key=len, reverse=True)

    v = {
        "city": col("SELECT city FROM customers"),
        "category": col("SELECT category FROM products"),
        "ecat": col("SELECT category FROM expenses"),
        "employee": col("SELECT name FROM employees"),
        "customer": col("SELECT name FROM customers"),
        "role": col("SELECT role FROM employees"),
        "method": col("SELECT method FROM payments"),
    }
    con.close()
    return v


def find(kind: str, q: str) -> str | None:
    for value in vocab()[kind]:
        if re.search(rf"\b{re.escape(value.lower())}", q.lower()):
            return value
    return None


def period(q: str) -> tuple[str, str] | None:
    """Turn 'March 2025', 'Q2 2025', 'the first half of 2026' or '2025' into dates."""
    t = q.lower()
    m = re.search(r"\b(" + "|".join(MONTHS) + r") (20\d\d)\b", t)
    if m:
        mo, y = MONTHS.index(m.group(1)) + 1, int(m.group(2))
        end_day = [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
        return f"{y}-{mo:02d}-01", f"{y}-{mo:02d}-{end_day}"
    m = re.search(r"\bq([1-4]) (20\d\d)\b", t) or re.search(
        r"\b(first|second|third|fourth) quarter of (20\d\d)\b", t
    )
    if m:
        qn = int(m.group(1)) if m.group(1).isdigit() else ORDINAL[m.group(1)]
        y = int(m.group(2))
        start, end = (qn - 1) * 3 + 1, qn * 3
        return f"{y}-{start:02d}-01", f"{y}-{end:02d}-{30 if end in (6, 9) else 31}"
    m = re.search(r"\b(first|second) half of (20\d\d)\b", t)
    if m:
        y = int(m.group(2))
        return (
            (f"{y}-01-01", f"{y}-06-30") if m.group(1) == "first" else (f"{y}-07-01", f"{y}-12-31")
        )
    m = re.search(r"\b(20\d\d)\b", t)
    if m:
        return f"{m.group(1)}-01-01", f"{m.group(1)}-12-31"
    return None


def _between(col: str, q: str) -> str:
    p = period(q)
    return f" AND {col} BETWEEN '{p[0]}' AND '{p[1]}'" if p else ""


def _customer_filters(q: str) -> str:
    out = ""
    city = find("city", q)
    if city:
        out += f" AND c.city = '{city}'"
    for seg in ("wholesale", "retail"):
        if re.search(rf"\b{seg}\b", q.lower()):
            out += f" AND c.segment = '{seg}'"
    return out


def _role(q: str) -> str | None:
    for role in vocab()["role"]:
        if re.search(rf"\b{role}(s|es)?\b", q.lower()):
            return role
    return None


def _generate(q: str) -> str | None:
    t = q.lower()
    emp, cat, ecat = find("employee", q), find("category", q), find("ecat", q)
    not_cancelled = "o.status <> 'cancelled'"

    if emp and re.search(r"reports? (directly )?to|whose manager is", t):
        role = _role(q.replace(emp, ""))
        extra = f" AND e.role = '{role}'" if role else ""
        return f"SELECT e.name FROM employees e JOIN employees b ON b.employee_id = e.manager_id WHERE b.name = '{emp}'{extra}"
    if emp and "payroll" in t:
        return f"SELECT ROUND(SUM(x.amount), 2) FROM expenses x JOIN employees e ON e.employee_id = x.employee_id WHERE x.category = 'payroll' AND e.name = '{emp}'{_between('x.expense_date', q)}"
    if emp and "invoice" in t:
        return f"SELECT ROUND(SUM(i.amount), 2) FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN employees e ON e.employee_id = o.employee_id WHERE e.name = '{emp}'{_between('i.issue_date', q)}"
    role = _role(q)
    if role and re.search(r"\b(rank|order the)\b", t) and "orders" in t:
        return f"SELECT e.name, COUNT(o.order_id) AS n, RANK() OVER (ORDER BY COUNT(o.order_id) DESC) FROM employees e JOIN orders o ON o.employee_id = e.employee_id WHERE e.role = '{role}'{_between('o.order_date', q)} GROUP BY e.employee_id ORDER BY n DESC, e.name"
    if role and re.search(r"who are our|whose role is", t):
        return f"SELECT name FROM employees WHERE role = '{role}'"
    if re.search(r"day of the week|weekday", t):
        ch = "".join(f" AND channel = '{c}'" for c in ("store", "online") if c in t)
        days = "CASE strftime('%w', order_date) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' ELSE 'Saturday' END"
        return f"SELECT {days} FROM orders WHERE 1 = 1{ch}{_between('order_date', q)} GROUP BY strftime('%w', order_date) ORDER BY COUNT(*) DESC, strftime('%w', order_date) LIMIT 1"
    if re.search(r"first (ever )?order|new customers", t):
        p = period(q)
        return (
            f"SELECT COUNT(*) FROM (SELECT customer_id, MIN(order_date) AS f FROM orders GROUP BY customer_id) WHERE f BETWEEN '{p[0]}' AND '{p[1]}'"
            if p
            else None
        )
    if "days" in t and "pay" in t:
        return f"SELECT ROUND(AVG(julianday(fp.d) - julianday(i.issue_date)), 2) FROM invoices i JOIN (SELECT invoice_id, MIN(payment_date) AS d FROM payments GROUP BY invoice_id) fp ON fp.invoice_id = i.invoice_id JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE 1 = 1{_customer_filters(q)}{_between('i.issue_date', q)}"
    if re.search(r"cash profit|payments exceed expenses", t):
        p = period(q)
        if not p:
            return None
        return f"SELECT ROUND((SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_date BETWEEN '{p[0]}' AND '{p[1]}') - (SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date BETWEEN '{p[0]}' AND '{p[1]}'), 2)"
    m = re.search(r"top (\d+) customers|(\d+) customers with the highest", t)
    if m and "invoice" in t:
        n = m.group(1) or m.group(2)
        return f"SELECT c.name, ROUND(SUM(i.amount), 2) AS total FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE 1 = 1{_between('i.issue_date', q)} GROUP BY c.customer_id ORDER BY total DESC, c.name LIMIT {n}"
    if re.search(r"each month|month by month", t) and "invoic" in t:
        return f"SELECT strftime('%Y-%m', issue_date) AS m, ROUND(SUM(amount), 2) FROM invoices WHERE 1 = 1{_between('issue_date', q)} GROUP BY m ORDER BY m"
    if ecat and re.search(r"running total|cumulative", t):
        return f"SELECT m, ROUND(SUM(s) OVER (ORDER BY m), 2) FROM (SELECT strftime('%Y-%m', expense_date) AS m, SUM(amount) AS s FROM expenses WHERE category = '{ecat}'{_between('expense_date', q)} GROUP BY m) ORDER BY m"
    if ecat and re.search(r"largest|biggest", t):
        return f"SELECT expense_date, amount FROM expenses WHERE category = '{ecat}' ORDER BY amount DESC LIMIT 1"
    if ecat and re.search(r"spend|expense|cost", t):
        return f"SELECT ROUND(SUM(amount), 2) FROM expenses WHERE category = '{ecat}'{_between('expense_date', q)}"
    if cat and re.search(r"percent|share", t):
        return f"SELECT ROUND(100.0 * SUM(CASE WHEN p.category = '{cat}' THEN {LINE} ELSE 0 END) / SUM({LINE}), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE {not_cancelled}{_between('o.order_date', q)}"
    if cat and "change" in t and "quarter" in t:
        cur = period(q)
        if not cur:
            return None
        y, mo = int(cur[0][:4]), int(cur[0][5:7])
        py, pm = (y, mo - 3) if mo > 3 else (y - 1, mo + 9)
        pe = pm + 2
        prev = (f"{py}-{pm:02d}-01", f"{py}-{pe:02d}-{30 if pe in (6, 9) else 31}")
        base = f"FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE {not_cancelled} AND p.category = '{cat}'"
        return f"SELECT ROUND((SELECT COALESCE(SUM({LINE}), 0) {base} AND o.order_date BETWEEN '{cur[0]}' AND '{cur[1]}') - (SELECT COALESCE(SUM({LINE}), 0) {base} AND o.order_date BETWEEN '{prev[0]}' AND '{prev[1]}'), 2)"
    if re.search(r"fewest units|lowest unit", t):
        return f"SELECT p.category FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE {not_cancelled}{_between('o.order_date', q)} GROUP BY p.category ORDER BY SUM(oi.quantity), p.category LIMIT 1"
    if cat and re.search(r"sales|revenue", t):
        return f"SELECT ROUND(SUM({LINE}), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE p.category = '{cat}' AND {not_cancelled}{_between('o.order_date', q)}"
    if cat and "discount" in t:
        return f"SELECT COUNT(*) FROM order_items oi JOIN products p ON p.product_id = oi.product_id WHERE p.category = '{cat}' AND oi.discount IS NOT NULL"
    if cat and "product" in t and re.search(r"expensive|pric", t):
        return f"SELECT name, unit_price FROM products WHERE category = '{cat}' ORDER BY unit_price DESC, name"
    if cat and "product" in t and re.search(COUNT, t):
        return f"SELECT COUNT(*) FROM products WHERE category = '{cat}'"
    if "invoice" in t and re.search(r"no payment|unpaid", t):
        return f"SELECT COUNT(*) FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id LEFT JOIN payments p ON p.invoice_id = i.invoice_id WHERE p.payment_id IS NULL{_customer_filters(q)}"
    if re.search(r"average invoice", t):
        return f"SELECT ROUND(AVG(i.amount), 2) FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE 1 = 1{_customer_filters(q)}{_between('i.issue_date', q)}"
    method = find("method", q)
    if method and "net" in t:
        return f"SELECT ROUND(SUM(amount), 2) FROM payments WHERE method = '{method}'{_between('payment_date', q)}"
    if "order" in t and re.search(COUNT, t):
        where = "".join(
            f" AND o.status = '{s}'" for s in ("cancelled", "refunded", "completed") if s in t
        )
        where += "".join(f" AND o.channel = '{c}'" for c in ("store", "online") if c in t)
        where += _customer_filters(q) + _between("o.order_date", q)
        return f"SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE 1 = 1{where}"
    if "customer" in t and re.search(COUNT, t):
        where = _customer_filters(q)
        if re.search(r"no email|missing email", t):
            where += " AND c.email IS NULL"
        return f"SELECT COUNT(*) FROM customers c WHERE 1 = 1{where}"
    return None


class TemplateGenerator:
    name = "template"

    def generate(self, question: str, tables: list[str]) -> str | None:
        return _generate(question)

    def repair(self, question: str, sql: str, error: str, tables: list[str]) -> str | None:
        return errorfix.fix(sql, error)
