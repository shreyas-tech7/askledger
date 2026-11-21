"""Write the frozen question set: src/askledger/data/questions.jsonl.

Written and run once, before any generator existed. After the freeze, nobody edits this file
or the jsonl. tests/test_questions.py checks the jsonl against its sha256 and checks that this
script still writes the same bytes.

42 families x 5 questions = 210. Tier 1: one table. Tier 2: joins with aggregates.
Tier 3: multi-step questions with dates or window functions.
The split is by family: a held-out family never appears in development, so the held-out score
shows how a generator does on question shapes it was not built for.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "askledger" / "data" / "questions.jsonl"
SPLIT_SEED = 7

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def m(name: str, year: int) -> dict:
    """Month params: the words and the 'YYYY-MM' key."""
    return {"month": name, "year": year, "ym": f"{year}-{MONTHS.index(name) + 1:02d}"}


# Revenue of order lines, used by many gold queries.
LINE = "oi.quantity * oi.unit_price * (1 - COALESCE(oi.discount, 0))"

FAMILIES = [
    # ---------------- tier 1: one table ----------------
    dict(
        id="t1_customers_in_city",
        tier=1,
        ordered=False,
        q=[
            "How many customers live in {city}?",
            "What is the number of customers based in {city}?",
        ],
        sql="SELECT COUNT(*) FROM customers WHERE city = '{city}'",
        params=[
            {"city": c} for c in ["Ashford", "Brookvale", "Cedar Point", "Dunmore", "Elmstead"]
        ],
    ),
    dict(
        id="t1_products_in_category",
        tier=1,
        ordered=False,
        q=[
            "How many products are in the {cat} category?",
            "Count the products we list under {cat}.",
        ],
        sql="SELECT COUNT(*) FROM products WHERE category = '{cat}'",
        params=[{"cat": c} for c in ["Coffee", "Tea", "Mugs", "Brewing Gear", "Candles"]],
    ),
    dict(
        id="t1_expense_category_year",
        tier=1,
        ordered=False,
        q=["What did we spend on {ecat} in {year}?", "Total {ecat} expenses for {year}?"],
        sql="SELECT ROUND(SUM(amount), 2) FROM expenses WHERE category = '{ecat}' AND strftime('%Y', expense_date) = '{year}'",
        params=[
            {"ecat": "rent", "year": 2025},
            {"ecat": "utilities", "year": 2025},
            {"ecat": "supplies", "year": 2026},
            {"ecat": "marketing", "year": 2025},
            {"ecat": "payroll", "year": 2026},
        ],
    ),
    dict(
        id="t1_orders_channel_month",
        tier=1,
        ordered=False,
        q=[
            "How many {channel} orders were placed in {month} {year}?",
            "Number of {channel} orders in {month} {year}?",
        ],
        sql="SELECT COUNT(*) FROM orders WHERE channel = '{channel}' AND strftime('%Y-%m', order_date) = '{ym}'",
        params=[
            {"channel": "online", **m("March", 2025)},
            {"channel": "store", **m("July", 2025)},
            {"channel": "online", **m("December", 2025)},
            {"channel": "store", **m("February", 2026)},
            {"channel": "online", **m("May", 2026)},
        ],
    ),
    dict(
        id="t1_products_by_price",
        tier=1,
        ordered=True,
        q=[
            "List the {cat} products from most to least expensive.",
            "Show {cat} products and prices, priciest first.",
        ],
        sql="SELECT name, unit_price FROM products WHERE category = '{cat}' ORDER BY unit_price DESC, name",
        params=[{"cat": c} for c in ["Coffee", "Tea", "Mugs", "Brewing Gear", "Gift Cards"]],
    ),
    dict(
        id="t1_customers_no_email",
        tier=1,
        ordered=False,
        q=[
            "How many customers in {city} have no email on file?",
            "Count {city} customers with a missing email address.",
        ],
        sql="SELECT COUNT(*) FROM customers WHERE city = '{city}' AND email IS NULL",
        params=[
            {"city": c} for c in ["Ashford", "Brookvale", "Cedar Point", "Dunmore", "Elmstead"]
        ],
    ),
    dict(
        id="t1_avg_invoice_month",
        tier=1,
        ordered=False,
        q=[
            "What was the average invoice amount in {month} {year}?",
            "Average invoice size for {month} {year}?",
        ],
        sql="SELECT ROUND(AVG(amount), 2) FROM invoices WHERE strftime('%Y-%m', issue_date) = '{ym}'",
        params=[
            m("January", 2025),
            m("April", 2025),
            m("August", 2025),
            m("November", 2025),
            m("March", 2026),
        ],
    ),
    dict(
        id="t1_refunds_total",
        tier=1,
        ordered=False,
        q=["How much money did we refund {how}in {year}?", "Total refunds {how}for {year}?"],
        sql="SELECT ROUND(-SUM(amount), 2) FROM payments WHERE amount < 0 {where}AND strftime('%Y', payment_date) = '{year}'",
        params=[
            {"how": "", "where": "", "year": 2025},
            {"how": "", "where": "", "year": 2026},
            {"how": "by card ", "where": "AND method = 'card' ", "year": 2025},
            {"how": "by cash ", "where": "AND method = 'cash' ", "year": 2025},
            {"how": "by bank transfer ", "where": "AND method = 'transfer' ", "year": 2026},
        ],
    ),
    dict(
        id="t1_staff_by_role",
        tier=1,
        ordered=False,
        q=["Who are our {role}s?", "List the names of employees whose role is {role}."],
        sql="SELECT name FROM employees WHERE role = '{role}'",
        params=[{"role": r} for r in ["barista", "roaster", "manager", "bookkeeper", "delivery"]],
    ),
    dict(
        id="t1_largest_expense",
        tier=1,
        ordered=False,
        q=[
            "What was the largest single {ecat} expense, and when was it?",
            "When did we pay our biggest {ecat} bill and how much was it?",
        ],
        sql="SELECT expense_date, amount FROM expenses WHERE category = '{ecat}' ORDER BY amount DESC LIMIT 1",
        params=[{"ecat": c} for c in ["utilities", "supplies", "marketing", "repairs", "payroll"]],
    ),
    dict(
        id="t1_orders_by_status_year",
        tier=1,
        ordered=False,
        q=["How many orders were {status} in {year}?", "Count the {status} orders from {year}."],
        sql="SELECT COUNT(*) FROM orders WHERE status = '{status}' AND strftime('%Y', order_date) = '{year}'",
        params=[
            {"status": "cancelled", "year": 2025},
            {"status": "refunded", "year": 2025},
            {"status": "completed", "year": 2025},
            {"status": "cancelled", "year": 2026},
            {"status": "refunded", "year": 2026},
        ],
    ),
    dict(
        id="t1_products_still_sold",
        tier=1,
        ordered=False,
        q=[
            "Which {cat} products are still sold?",
            "List the {cat} products that are not discontinued.",
        ],
        sql="SELECT name FROM products WHERE category = '{cat}' AND discontinued = 0",
        params=[{"cat": c} for c in ["Coffee", "Tea", "Mugs", "Brewing Gear", "Gift Cards"]],
    ),
    dict(
        id="t1_net_by_method_month",
        tier=1,
        ordered=False,
        q=[
            "What was the net amount received by {method} in {month} {year}, after refunds?",
            "Net {method} payments for {month} {year}, refunds included?",
        ],
        sql="SELECT ROUND(SUM(amount), 2) FROM payments WHERE method = '{method}' AND strftime('%Y-%m', payment_date) = '{ym}'",
        params=[
            {"method": "card", **m("February", 2025)},
            {"method": "cash", **m("June", 2025)},
            {"method": "transfer", **m("October", 2025)},
            {"method": "card", **m("January", 2026)},
            {"method": "cash", **m("April", 2026)},
        ],
    ),
    dict(
        id="t1_online_not_shipped",
        tier=1,
        ordered=False,
        q=[
            "How many online orders from {month} {year} have no shipped date?",
            "Online orders placed in {month} {year} that never got a ship date: how many?",
        ],
        sql="SELECT COUNT(*) FROM orders WHERE channel = 'online' AND shipped_date IS NULL AND strftime('%Y-%m', order_date) = '{ym}'",
        params=[
            m("January", 2025),
            m("May", 2025),
            m("September", 2025),
            m("December", 2025),
            m("June", 2026),
        ],
    ),
    # ---------------- tier 2: joins with aggregates ----------------
    dict(
        id="t2_category_sales_year",
        tier=2,
        ordered=False,
        q=[
            "What were {cat} sales in {year}, not counting cancelled orders?",
            "Total {cat} revenue for {year}, excluding cancelled orders?",
        ],
        sql="SELECT ROUND(SUM("
        + LINE
        + "), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE p.category = '{cat}' AND o.status <> 'cancelled' AND strftime('%Y', o.order_date) = '{year}'",
        params=[
            {"cat": "Coffee", "year": 2025},
            {"cat": "Tea", "year": 2025},
            {"cat": "Mugs", "year": 2026},
            {"cat": "Candles", "year": 2025},
            {"cat": "Brewing Gear", "year": 2026},
        ],
    ),
    dict(
        id="t2_top_customers_invoiced",
        tier=2,
        ordered=True,
        q=[
            "Who were our top {n} customers by invoiced amount in {year}?",
            "Name the {n} customers with the highest invoice totals in {year}, highest first.",
        ],
        sql="SELECT c.name, ROUND(SUM(i.amount), 2) AS total FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE strftime('%Y', i.issue_date) = '{year}' GROUP BY c.customer_id ORDER BY total DESC, c.name LIMIT {n}",
        params=[
            {"n": 3, "year": 2025},
            {"n": 5, "year": 2025},
            {"n": 3, "year": 2026},
            {"n": 5, "year": 2026},
            {"n": 10, "year": 2025},
        ],
    ),
    dict(
        id="t2_units_of_product",
        tier=2,
        ordered=False,
        q=[
            "How many units of {product} did we sell in {year}, not counting cancelled orders?",
            "Units sold of {product} in {year}, excluding cancelled orders?",
        ],
        sql="SELECT SUM(oi.quantity) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE (p.name = '{product}' OR p.former_name = '{product}') AND o.status <> 'cancelled' AND strftime('%Y', o.order_date) = '{year}'",
        params=[
            {"product": "Morning Blend", "year": 2025},
            {"product": "Dark Roast", "year": 2025},
            {"product": "Earl Grey", "year": 2026},
            {"product": "Travel Mug", "year": 2025},
            {"product": "French Press", "year": 2026},
        ],
    ),
    dict(
        id="t2_orders_by_city_year",
        tier=2,
        ordered=False,
        q=[
            "How many orders did customers in {city} place in {year}?",
            "Order count from {city} customers during {year}?",
        ],
        sql="SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE c.city = '{city}' AND strftime('%Y', o.order_date) = '{year}'",
        params=[
            {"city": "Ashford", "year": 2025},
            {"city": "Brookvale", "year": 2026},
            {"city": "Cedar Point", "year": 2025},
            {"city": "Dunmore", "year": 2026},
            {"city": "Elmstead", "year": 2025},
        ],
    ),
    dict(
        id="t2_invoiced_by_employee",
        tier=2,
        ordered=False,
        q=[
            "What is the total invoiced amount for orders handled by {emp}?",
            "How much did orders taken by {emp} bring in, by invoice total?",
        ],
        sql="SELECT ROUND(SUM(i.amount), 2) FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN employees e ON e.employee_id = o.employee_id WHERE e.name = '{emp}'",
        params=[
            {"emp": e}
            for e in [
                "Avel Torlom",
                "Orla Norfen",
                "Mira Pelkes",
                "Soren Yarrowsel",
                "Mira Wickvane",
            ]
        ],
    ),
    dict(
        id="t2_sales_by_channel",
        tier=2,
        ordered=False,
        q=[
            "Break down item sales by channel for {period}, excluding cancelled orders.",
            "How much did each channel sell in {period}, not counting cancelled orders?",
        ],
        sql="SELECT o.channel, ROUND(SUM("
        + LINE
        + "), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.status <> 'cancelled' AND o.order_date BETWEEN '{start}' AND '{end}' GROUP BY o.channel",
        params=[
            {"period": "2025", "start": "2025-01-01", "end": "2025-12-31"},
            {"period": "the first half of 2026", "start": "2026-01-01", "end": "2026-06-30"},
            {"period": "March 2025", "start": "2025-03-01", "end": "2025-03-31"},
            {"period": "the second half of 2025", "start": "2025-07-01", "end": "2025-12-31"},
            {"period": "May 2026", "start": "2026-05-01", "end": "2026-05-31"},
        ],
    ),
    dict(
        id="t2_invoices_without_payment",
        tier=2,
        ordered=False,
        q=[
            "How many invoices for customers in {city} have no payment recorded?",
            "Count the unpaid invoices of {city} customers, meaning no payment row at all.",
        ],
        sql="SELECT COUNT(*) FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id LEFT JOIN payments p ON p.invoice_id = i.invoice_id WHERE c.city = '{city}' AND p.payment_id IS NULL",
        params=[
            {"city": c} for c in ["Ashford", "Brookvale", "Cedar Point", "Dunmore", "Elmstead"]
        ],
    ),
    dict(
        id="t2_avg_invoice_segment",
        tier=2,
        ordered=False,
        q=[
            "What is the average invoice amount for {who} in {year}?",
            "Average invoice for {who} during {year}?",
        ],
        sql="SELECT ROUND(AVG(i.amount), 2) FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE {where} AND strftime('%Y', i.issue_date) = '{year}'",
        params=[
            {"who": "retail customers", "where": "c.segment = 'retail'", "year": 2025},
            {"who": "wholesale customers", "where": "c.segment = 'wholesale'", "year": 2025},
            {"who": "retail customers", "where": "c.segment = 'retail'", "year": 2026},
            {"who": "wholesale customers", "where": "c.segment = 'wholesale'", "year": 2026},
            {
                "who": "retail customers in Dunmore",
                "where": "c.segment = 'retail' AND c.city = 'Dunmore'",
                "year": 2025,
            },
        ],
    ),
    dict(
        id="t2_low_category_units_month",
        tier=2,
        ordered=False,
        q=[
            "Of the categories that sold anything in {month} {year}, which sold the fewest units? Exclude cancelled orders.",
            "Among categories with any sales in {month} {year}, which had the lowest unit count, not counting cancelled orders?",
        ],
        sql="SELECT p.category FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE o.status <> 'cancelled' AND strftime('%Y-%m', o.order_date) = '{ym}' GROUP BY p.category ORDER BY SUM(oi.quantity), p.category LIMIT 1",
        params=[
            m("February", 2025),
            m("June", 2025),
            m("October", 2025),
            m("January", 2026),
            m("June", 2026),
        ],
    ),
    dict(
        id="t2_refunded_orders_city",
        tier=2,
        ordered=False,
        q=[
            "How many refunded orders came from customers in {city}?",
            "Number of orders with status refunded for {city} customers?",
        ],
        sql="SELECT COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE o.status = 'refunded' AND c.city = '{city}'",
        params=[
            {"city": c} for c in ["Ashford", "Brookvale", "Cedar Point", "Dunmore", "Elmstead"]
        ],
    ),
    dict(
        id="t2_customer_net_paid",
        tier=2,
        ordered=False,
        q=[
            "How much has {cust} paid us in total, after refunds?",
            "Net payments received from {cust}, refunds included?",
        ],
        sql="SELECT ROUND(SUM(p.amount), 2) FROM payments p JOIN invoices i ON i.invoice_id = p.invoice_id JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE c.name = '{cust}'",
        params=[
            {"cust": c}
            for c in ["Quin Vanetor", "Rhea Pelgor", "Nev Norwick", "Bryn Fenfen", "Emra Kessel"]
        ],
    ),
    dict(
        id="t2_discounted_lines_category",
        tier=2,
        ordered=False,
        q=[
            "How many order lines for {cat} products had a discount?",
            "Count discounted order lines in the {cat} category.",
        ],
        sql="SELECT COUNT(*) FROM order_items oi JOIN products p ON p.product_id = oi.product_id WHERE p.category = '{cat}' AND oi.discount IS NOT NULL",
        params=[{"cat": c} for c in ["Coffee", "Tea", "Mugs", "Brewing Gear", "Candles"]],
    ),
    dict(
        id="t2_reports_to",
        tier=2,
        ordered=False,
        q=["Who reports directly to {boss}?", "List the employees whose manager is {boss}."],
        sql="SELECT e.name FROM employees e JOIN employees b ON b.employee_id = e.manager_id WHERE b.name = '{boss}'{extra}",
        params=[
            {"boss": "Quin Pelwick", "extra": ""},
            {"boss": "Soren Yarrowsel", "extra": ""},
            {"boss": "Soren Yarrowsel", "extra": " AND e.role = 'barista'"},
            {"boss": "Soren Yarrowsel", "extra": " AND e.role = 'roaster'"},
            {"boss": "Quin Pelwick", "extra": " AND e.role = 'bookkeeper'"},
        ],
        variants=[
            "Who reports directly to {boss}?",
            "List the employees whose manager is {boss}.",
            "Which baristas report to {boss}?",
            "Which roasters report to {boss}?",
            "Is there a bookkeeper who reports to {boss}? Give the name.",
        ],
    ),
    dict(
        id="t2_payroll_for_employee",
        tier=2,
        ordered=False,
        q=["How much payroll did we pay {emp} in {year}?", "Total {year} payroll cost for {emp}?"],
        sql="SELECT ROUND(SUM(x.amount), 2) FROM expenses x JOIN employees e ON e.employee_id = x.employee_id WHERE x.category = 'payroll' AND e.name = '{emp}' AND strftime('%Y', x.expense_date) = '{year}'",
        params=[
            {"emp": "Avel Torlom", "year": 2025},
            {"emp": "Rhea Dunyarrow", "year": 2025},
            {"emp": "Orla Quillquill", "year": 2026},
            {"emp": "Mira Wickvane", "year": 2026},
            {"emp": "Soren Yarrowsel", "year": 2025},
        ],
    ),
    # ---------------- tier 3: multi-step, dates, windows ----------------
    dict(
        id="t3_invoiced_by_month",
        tier=3,
        ordered=True,
        q=[
            "Show the invoiced amount for each month of {period}, in order.",
            "Month by month, how much did we invoice during {period}?",
        ],
        sql="SELECT strftime('%Y-%m', issue_date) AS month, ROUND(SUM(amount), 2) FROM invoices WHERE issue_date BETWEEN '{start}' AND '{end}' GROUP BY month ORDER BY month",
        params=[
            {"period": "2025", "start": "2025-01-01", "end": "2025-12-31"},
            {"period": "the first half of 2026", "start": "2026-01-01", "end": "2026-06-30"},
            {"period": "the first quarter of 2025", "start": "2025-01-01", "end": "2025-03-31"},
            {"period": "the fourth quarter of 2025", "start": "2025-10-01", "end": "2025-12-31"},
            {"period": "the second quarter of 2026", "start": "2026-04-01", "end": "2026-06-30"},
        ],
    ),
    dict(
        id="t3_biggest_mom_increase",
        tier=3,
        ordered=False,
        q=[
            "Which month in {period} had the biggest increase in invoiced amount over the month before?",
            "In {period}, which month grew invoicing the most compared with the previous month?",
        ],
        sql="WITH monthly AS (SELECT strftime('%Y-%m', issue_date) AS month, SUM(amount) AS total FROM invoices GROUP BY month), diffs AS (SELECT month, total - LAG(total) OVER (ORDER BY month) AS change FROM monthly) SELECT month FROM diffs WHERE month BETWEEN '{start}' AND '{end}' AND change IS NOT NULL ORDER BY change DESC LIMIT 1",
        params=[
            {"period": "2025", "start": "2025-01", "end": "2025-12"},
            {"period": "the first half of 2026", "start": "2026-01", "end": "2026-06"},
            {"period": "the second half of 2025", "start": "2025-07", "end": "2025-12"},
            {"period": "the first half of 2025", "start": "2025-01", "end": "2025-06"},
            {"period": "the whole period on record", "start": "0000", "end": "9999"},
        ],
    ),
    dict(
        id="t3_running_expense_total",
        tier=3,
        ordered=True,
        q=[
            "Give the running total of {ecat} spending by month in {year}.",
            "Cumulative {ecat} expenses month by month for {year}?",
        ],
        sql="SELECT month, ROUND(SUM(total) OVER (ORDER BY month), 2) FROM (SELECT strftime('%Y-%m', expense_date) AS month, SUM(amount) AS total FROM expenses WHERE category = '{ecat}' AND strftime('%Y', expense_date) = '{year}' GROUP BY month) ORDER BY month",
        params=[
            {"ecat": "supplies", "year": 2025},
            {"ecat": "utilities", "year": 2025},
            {"ecat": "payroll", "year": 2026},
            {"ecat": "marketing", "year": 2025},
            {"ecat": "supplies", "year": 2026},
        ],
    ),
    dict(
        id="t3_cash_profit_month",
        tier=3,
        ordered=False,
        q=[
            "What was our cash profit in {month} {year}, meaning payments received minus expenses?",
            "For {month} {year}, how much did payments exceed expenses (net of refunds)?",
        ],
        sql="SELECT ROUND((SELECT COALESCE(SUM(amount), 0) FROM payments WHERE strftime('%Y-%m', payment_date) = '{ym}') - (SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE strftime('%Y-%m', expense_date) = '{ym}'), 2)",
        params=[
            m("March", 2025),
            m("July", 2025),
            m("November", 2025),
            m("February", 2026),
            m("May", 2026),
        ],
    ),
    dict(
        id="t3_best_product_per_category",
        tier=3,
        ordered=True,
        q=[
            "What was the best-selling product by units in each category in {year}? Sort by category.",
            "For {year}, name the top product by units sold within every category, ordered by category.",
        ],
        sql="WITH units AS (SELECT p.category, p.name, SUM(oi.quantity) AS u FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE o.status <> 'cancelled' AND strftime('%Y', o.order_date) = '{year}'{extra} GROUP BY p.product_id), ranked AS (SELECT category, name, u, ROW_NUMBER() OVER (PARTITION BY category ORDER BY u DESC, name) AS rn FROM units) SELECT category, name, u FROM ranked WHERE rn = 1 ORDER BY category",
        params=[
            {"year": 2025, "extra": ""},
            {"year": 2026, "extra": ""},
            {"year": 2025, "extra": " AND o.channel = 'online'"},
            {"year": 2025, "extra": " AND o.channel = 'store'"},
            {"year": 2026, "extra": " AND o.channel = 'online'"},
        ],
        variants=[
            "What was the best-selling product by units in each category in {year}? Sort by category.",
            "For {year}, name the top product by units sold within every category, ordered by category.",
            "Among online orders in {year}, which product sold the most units in each category? Sort by category.",
            "Among store orders in {year}, which product sold the most units in each category? Sort by category.",
            "For online orders in {year}, give the top product by units in each category, ordered by category.",
        ],
    ),
    dict(
        id="t3_customers_both_years",
        tier=3,
        ordered=False,
        q=[
            "How many customers{from} ordered in both 2025 and 2026?",
            "Count the customers{from} who placed orders in 2025 and again in 2026.",
        ],
        sql="SELECT COUNT(*) FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND strftime('%Y', o.order_date) = '2025') AND EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND strftime('%Y', o.order_date) = '2026'){where}",
        params=[
            {"from": "", "where": ""},
            {"from": " from Ashford", "where": " AND c.city = 'Ashford'"},
            {"from": " from Dunmore", "where": " AND c.city = 'Dunmore'"},
            {"from": " in the wholesale segment", "where": " AND c.segment = 'wholesale'"},
            {"from": " from Elmstead", "where": " AND c.city = 'Elmstead'"},
        ],
    ),
    dict(
        id="t3_first_time_customers_month",
        tier=3,
        ordered=False,
        q=[
            "How many customers placed their first ever order in {month} {year}?",
            "New customers in {month} {year}, counted by the month of their first order?",
        ],
        sql="SELECT COUNT(*) FROM (SELECT customer_id, MIN(order_date) AS first_order FROM orders GROUP BY customer_id) WHERE strftime('%Y-%m', first_order) = '{ym}'",
        params=[
            m("January", 2025),
            m("February", 2025),
            m("June", 2025),
            m("October", 2025),
            m("March", 2026),
        ],
    ),
    dict(
        id="t3_days_to_pay",
        tier=3,
        ordered=False,
        q=[
            "On average, how many days did {who} take to make their first payment on an invoice issued in {year}?",
            "Average days from invoice date to first payment for {who}, invoices from {year}?",
        ],
        sql="SELECT ROUND(AVG(julianday(fp.first_paid) - julianday(i.issue_date)), 2) FROM invoices i JOIN (SELECT invoice_id, MIN(payment_date) AS first_paid FROM payments GROUP BY invoice_id) fp ON fp.invoice_id = i.invoice_id JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE strftime('%Y', i.issue_date) = '{year}'{where}",
        params=[
            {"who": "wholesale customers", "where": " AND c.segment = 'wholesale'", "year": 2025},
            {"who": "wholesale customers", "where": " AND c.segment = 'wholesale'", "year": 2026},
            {"who": "all customers", "where": "", "year": 2025},
            {"who": "Brookvale customers", "where": " AND c.city = 'Brookvale'", "year": 2025},
            {
                "who": "wholesale customers in Ashford",
                "where": " AND c.segment = 'wholesale' AND c.city = 'Ashford'",
                "year": 2025,
            },
        ],
    ),
    dict(
        id="t3_overdue_invoices",
        tier=3,
        ordered=False,
        q=[
            "As of 2026-06-30, how many invoices still had money owing more than {n} days after their due date?",
            "Count invoices with an unpaid balance that were over {n} days past due on 2026-06-30.",
        ],
        sql="SELECT COUNT(*) FROM invoices i LEFT JOIN (SELECT invoice_id, SUM(amount) AS paid FROM payments GROUP BY invoice_id) p ON p.invoice_id = i.invoice_id WHERE i.amount - COALESCE(p.paid, 0) > 0.005 AND julianday('2026-06-30') - julianday(i.due_date) > {n}",
        params=[{"n": n} for n in [0, 15, 30, 60, 90]],
    ),
    dict(
        id="t3_category_share",
        tier=3,
        ordered=False,
        q=[
            "What percent of {year} item sales came from {cat}, excluding cancelled orders? Round to 2 decimals.",
            "{cat} as a share of all {year} item sales, in percent, not counting cancelled orders?",
        ],
        sql="SELECT ROUND(100.0 * SUM(CASE WHEN p.category = '{cat}' THEN "
        + LINE
        + " ELSE 0 END) / SUM("
        + LINE
        + "), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE o.status <> 'cancelled' AND strftime('%Y', o.order_date) = '{year}'",
        params=[
            {"cat": "Coffee", "year": 2025},
            {"cat": "Tea", "year": 2026},
            {"cat": "Brewing Gear", "year": 2025},
            {"cat": "Gift Cards", "year": 2026},
            {"cat": "Candles", "year": 2025},
        ],
    ),
    dict(
        id="t3_quarter_change",
        tier=3,
        ordered=False,
        q=[
            "How did {cat} sales in Q{q} {year} change from the quarter before? Give the difference in dollars.",
            "Dollar change in {cat} item sales from the previous quarter to Q{q} {year}, excluding cancelled orders?",
        ],
        sql="WITH s AS (SELECT o.order_date AS d, "
        + LINE
        + " AS v FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id WHERE o.status <> 'cancelled' AND p.category = '{cat}') SELECT ROUND((SELECT COALESCE(SUM(v), 0) FROM s WHERE d BETWEEN '{cs}' AND '{ce}') - (SELECT COALESCE(SUM(v), 0) FROM s WHERE d BETWEEN '{ps}' AND '{pe}'), 2)",
        params=[
            {
                "cat": "Coffee",
                "q": 2,
                "year": 2025,
                "cs": "2025-04-01",
                "ce": "2025-06-30",
                "ps": "2025-01-01",
                "pe": "2025-03-31",
            },
            {
                "cat": "Tea",
                "q": 3,
                "year": 2025,
                "cs": "2025-07-01",
                "ce": "2025-09-30",
                "ps": "2025-04-01",
                "pe": "2025-06-30",
            },
            {
                "cat": "Mugs",
                "q": 4,
                "year": 2025,
                "cs": "2025-10-01",
                "ce": "2025-12-31",
                "ps": "2025-07-01",
                "pe": "2025-09-30",
            },
            {
                "cat": "Coffee",
                "q": 1,
                "year": 2026,
                "cs": "2026-01-01",
                "ce": "2026-03-31",
                "ps": "2025-10-01",
                "pe": "2025-12-31",
            },
            {
                "cat": "Brewing Gear",
                "q": 2,
                "year": 2026,
                "cs": "2026-04-01",
                "ce": "2026-06-30",
                "ps": "2026-01-01",
                "pe": "2026-03-31",
            },
        ],
    ),
    dict(
        id="t3_top_customer_per_city",
        tier=3,
        ordered=True,
        q=[
            "Who was the top customer by invoiced amount in each city in {year}? Sort by city.",
            "For each city, name the customer with the highest {year} invoice total, ordered by city.",
        ],
        sql="WITH t AS (SELECT c.city, c.name, SUM(i.amount) AS total FROM invoices i JOIN orders o ON o.order_id = i.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE strftime('%Y', i.issue_date) = '{year}'{where} GROUP BY c.customer_id), r AS (SELECT city, name, total, ROW_NUMBER() OVER (PARTITION BY city ORDER BY total DESC, name) AS rn FROM t) SELECT city, name, ROUND(total, 2) FROM r WHERE rn = 1 ORDER BY city",
        params=[
            {"year": 2025, "where": ""},
            {"year": 2026, "where": ""},
            {"year": 2025, "where": " AND c.segment = 'retail'"},
            {"year": 2026, "where": " AND c.segment = 'retail'"},
            {"year": 2025, "where": " AND c.segment = 'wholesale'"},
        ],
        variants=[
            "Who was the top customer by invoiced amount in each city in {year}? Sort by city.",
            "For each city, name the customer with the highest {year} invoice total, ordered by city.",
            "Among retail customers, who had the highest {year} invoice total in each city? Sort by city.",
            "For each city, which retail customer was invoiced the most in {year}? Order by city.",
            "Among wholesale customers, who had the highest {year} invoice total in each city? Sort by city.",
        ],
    ),
    dict(
        id="t3_busiest_weekday",
        tier=3,
        ordered=False,
        q=[
            "Which day of the week had the most {channel} orders in {year}?",
            "On which weekday did we get the most {channel} orders during {year}?",
        ],
        sql="SELECT CASE strftime('%w', order_date) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' ELSE 'Saturday' END AS weekday FROM orders WHERE channel = '{channel}' AND strftime('%Y', order_date) = '{year}' GROUP BY strftime('%w', order_date) ORDER BY COUNT(*) DESC, strftime('%w', order_date) LIMIT 1",
        params=[
            {"channel": "store", "year": 2025},
            {"channel": "online", "year": 2025},
            {"channel": "store", "year": 2026},
            {"channel": "online", "year": 2026},
            {"channel": "store", "year": 2025},
        ],
        variants=[
            "Which day of the week had the most {channel} orders in {year}?",
            "On which weekday did we get the most {channel} orders during {year}?",
            "Which day of the week had the most {channel} orders in {year}?",
            "On which weekday did we get the most {channel} orders during {year}?",
            "What was the busiest weekday for {channel} orders in {year}, by order count?",
        ],
    ),
    dict(
        id="t3_rank_staff_orders",
        tier=3,
        ordered=True,
        q=[
            "Rank the {role}s by the number of orders they took in {period}, most first.",
            "Order the {role}s by how many orders each handled during {period}, highest first, with their rank.",
        ],
        sql="SELECT e.name, COUNT(o.order_id) AS n, RANK() OVER (ORDER BY COUNT(o.order_id) DESC) AS rnk FROM employees e JOIN orders o ON o.employee_id = e.employee_id WHERE e.role = '{role}' AND o.order_date BETWEEN '{start}' AND '{end}' GROUP BY e.employee_id ORDER BY n DESC, e.name",
        params=[
            {"role": "barista", "period": "2025", "start": "2025-01-01", "end": "2025-12-31"},
            {
                "role": "barista",
                "period": "the first half of 2026",
                "start": "2026-01-01",
                "end": "2026-06-30",
            },
            {
                "role": "barista",
                "period": "the fourth quarter of 2025",
                "start": "2025-10-01",
                "end": "2025-12-31",
            },
            {"role": "barista", "period": "March 2026", "start": "2026-03-01", "end": "2026-03-31"},
            {
                "role": "barista",
                "period": "the first quarter of 2025",
                "start": "2025-01-01",
                "end": "2025-03-31",
            },
        ],
    ),
]


def build() -> list[dict]:
    rng = random.Random(SPLIT_SEED)
    held = set()
    for tier, n_held in ((1, 4), (2, 5), (3, 5)):
        ids = [f["id"] for f in FAMILIES if f["tier"] == tier]
        rng.shuffle(ids)
        held.update(ids[:n_held])
    rows = []
    for fam in FAMILIES:
        phrasings = fam.get("variants")
        for i, p in enumerate(fam["params"]):
            text = phrasings[i] if phrasings else fam["q"][i % len(fam["q"])]
            rows.append(
                {
                    "id": f"{fam['id']}_{i + 1}",
                    "family": fam["id"],
                    "tier": fam["tier"],
                    "split": "heldout" if fam["id"] in held else "dev",
                    "ordered": fam["ordered"],
                    "question": text.format(**p),
                    "gold_sql": fam["sql"].format(**p),
                }
            )
    return rows


def render(rows: list[dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


if __name__ == "__main__":
    text = render(build())
    OUT.write_text(text)
    (OUT.parent / "questions.sha256").write_text(hashlib.sha256(text.encode()).hexdigest() + "\n")
    print(f"wrote {OUT} ({text.count(chr(10))} questions)")
