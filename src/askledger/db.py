"""Seeded generator for the synthetic small-business database.

The business is invented: "Juniper Lane Coffee", a small roaster with a shop and a web store.
Every name is made from syllables, so no row describes a real person.

Real-world quirks on purpose:
- refunds are negative payments
- the product "House Blend" was renamed from "Morning Blend" (see products.former_name)
- nulls: customers.email, orders.shipped_date, order_items.discount, expenses.vendor
- the whole "Candles" category is discontinued
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random
import sqlite3
from pathlib import Path

SEED = 2026
START = dt.date(2025, 1, 1)
END = dt.date(2026, 6, 30)
CANDLES_STOPPED = dt.date(2025, 7, 1)
DB_PATH = Path(__file__).parent / "data" / "ledger.db"

SCHEMA = """
CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  city TEXT NOT NULL,
  email TEXT,
  segment TEXT NOT NULL,
  signup_date TEXT NOT NULL
);
CREATE TABLE products (
  product_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  former_name TEXT,
  category TEXT NOT NULL,
  unit_price REAL NOT NULL,
  discontinued INTEGER NOT NULL
);
CREATE TABLE employees (
  employee_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  hire_date TEXT NOT NULL,
  hourly_rate REAL NOT NULL,
  manager_id INTEGER REFERENCES employees(employee_id)
);
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
  employee_id INTEGER NOT NULL REFERENCES employees(employee_id),
  order_date TEXT NOT NULL,
  shipped_date TEXT,
  channel TEXT NOT NULL,
  status TEXT NOT NULL
);
CREATE TABLE order_items (
  order_item_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  product_id INTEGER NOT NULL REFERENCES products(product_id),
  quantity INTEGER NOT NULL,
  unit_price REAL NOT NULL,
  discount REAL
);
CREATE TABLE invoices (
  invoice_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  issue_date TEXT NOT NULL,
  due_date TEXT NOT NULL,
  amount REAL NOT NULL
);
CREATE TABLE payments (
  payment_id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id),
  payment_date TEXT NOT NULL,
  amount REAL NOT NULL,
  method TEXT NOT NULL
);
CREATE TABLE expenses (
  expense_id INTEGER PRIMARY KEY,
  expense_date TEXT NOT NULL,
  category TEXT NOT NULL,
  vendor TEXT,
  amount REAL NOT NULL,
  employee_id INTEGER REFERENCES employees(employee_id)
);
"""

TABLES = [
    "customers",
    "products",
    "employees",
    "orders",
    "order_items",
    "invoices",
    "payments",
    "expenses",
]

FIRST = [
    "Avel",
    "Bryn",
    "Cato",
    "Dara",
    "Emra",
    "Finn",
    "Galen",
    "Hesta",
    "Ilo",
    "Jory",
    "Kesh",
    "Lune",
    "Mira",
    "Nev",
    "Orla",
    "Pell",
    "Quin",
    "Rhea",
    "Soren",
    "Tamsin",
]
SYL = [
    "bar",
    "cal",
    "dun",
    "fen",
    "gor",
    "hal",
    "kes",
    "lom",
    "mar",
    "nor",
    "pel",
    "quill",
    "ros",
    "sel",
    "tor",
    "vane",
    "wick",
    "yarrow",
]
CITIES = ["Ashford", "Brookvale", "Cedar Point", "Dunmore", "Elmstead"]
PRODUCTS = [
    # name, former name, category, price
    ("House Blend", "Morning Blend", "Coffee", 14.0),
    ("Dark Roast", None, "Coffee", 15.5),
    ("Single Origin Kenya", None, "Coffee", 19.0),
    ("Decaf Blend", None, "Coffee", 14.5),
    ("Espresso Roast", None, "Coffee", 16.0),
    ("Cold Brew Pack", None, "Coffee", 12.0),
    ("Green Tea", None, "Tea", 9.0),
    ("Earl Grey", None, "Tea", 9.5),
    ("Chai Mix", None, "Tea", 11.0),
    ("Mint Tea", None, "Tea", 8.5),
    ("Ceramic Mug", None, "Mugs", 18.0),
    ("Travel Mug", None, "Mugs", 24.0),
    ("Glass Mug", None, "Mugs", 16.0),
    ("Pour Over Kit", None, "Brewing Gear", 35.0),
    ("French Press", None, "Brewing Gear", 42.0),
    ("Burr Grinder", None, "Brewing Gear", 89.0),
    ("Paper Filters", None, "Brewing Gear", 6.0),
    ("Gift Card 25", None, "Gift Cards", 25.0),
    ("Gift Card 50", None, "Gift Cards", 50.0),
    ("Vanilla Candle", None, "Candles", 21.0),
    ("Cedar Candle", None, "Candles", 21.0),
    ("Espresso Candle", None, "Candles", 23.0),
]
ROLES = [
    "owner",
    "manager",
    "barista",
    "barista",
    "barista",
    "barista",
    "roaster",
    "roaster",
    "bookkeeper",
    "barista",
    "delivery",
    "barista",
]
EXPENSE_VENDORS = {
    "rent": ["Halvorsen Property"],
    "utilities": ["Brookvale Power", "Cedar Water"],
    "supplies": ["Kestrel Packaging", "Marlo Beans Import", "Tamsel Dairy"],
    "marketing": ["Pellwick Print", "Orla Media"],
    "repairs": ["Dunmore Fixit"],
}


def _name(rng: random.Random) -> str:
    last = (rng.choice(SYL) + rng.choice(SYL)).capitalize()
    return f"{rng.choice(FIRST)} {last}"


def _day(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    return start + dt.timedelta(days=rng.randrange((end - start).days + 1))


def build(path: Path, seed: int = SEED) -> Path:
    """Write a fresh database to ``path``. Same seed, same bytes of content."""
    path = Path(path)
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    names: set[str] = set()

    def unique_name() -> str:
        while True:
            n = _name(rng)
            if n not in names:
                names.add(n)
                return n

    # employees: id 1 is the owner, managers report to the owner, the rest to the manager
    for i, role in enumerate(ROLES, start=1):
        manager = None if i == 1 else (1 if role in ("manager", "bookkeeper") else 2)
        rate = {
            "owner": 0.0,
            "manager": 26.0,
            "bookkeeper": 30.0,
            "roaster": 22.0,
            "delivery": 18.0,
        }.get(role, 17.0) + rng.choice([0, 0.5, 1.0, 1.5])
        hire = (
            _day(rng, dt.date(2019, 1, 1), dt.date(2026, 1, 31)) if i > 1 else dt.date(2018, 3, 1)
        )
        con.execute(
            "INSERT INTO employees VALUES (?,?,?,?,?,?)",
            (i, unique_name(), role, hire.isoformat(), rate, manager),
        )
    staff = [i for i, r in enumerate(ROLES, start=1) if r in ("barista", "manager", "delivery")]

    for i, (name, former, cat, price) in enumerate(PRODUCTS, start=1):
        con.execute(
            "INSERT INTO products VALUES (?,?,?,?,?,?)",
            (i, name, former, cat, price, 1 if cat == "Candles" else 0),
        )

    customers = []
    for i in range(1, 121):
        segment = "wholesale" if i % 8 == 0 else "retail"
        name = unique_name()
        email = None if rng.random() < 0.15 else f"{name.lower().replace(' ', '.')}@mail.invalid"
        signup = _day(rng, dt.date(2024, 1, 1), dt.date(2026, 5, 31))
        con.execute(
            "INSERT INTO customers VALUES (?,?,?,?,?,?)",
            (i, name, rng.choice(CITIES), email, segment, signup.isoformat()),
        )
        customers.append((i, segment, signup))

    order_id = item_id = invoice_id = payment_id = 0
    for _ in range(1400):
        cid, segment, signup = rng.choice(customers)
        first = max(START, signup)
        if first > END:
            continue
        day = _day(rng, first, END)
        order_id += 1
        channel = "online" if rng.random() < 0.4 else "store"
        roll = rng.random()
        status = "cancelled" if roll < 0.04 else ("refunded" if roll < 0.09 else "completed")
        shipped = None
        if channel == "online" and status != "cancelled" and rng.random() < 0.9:
            shipped = (day + dt.timedelta(days=rng.randint(1, 5))).isoformat()
        con.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?)",
            (order_id, cid, rng.choice(staff), day.isoformat(), shipped, channel, status),
        )
        total = 0.0
        pids = rng.sample(range(1, len(PRODUCTS) + 1), rng.randint(1, 4))
        for pid in pids:
            _, _, cat, price = PRODUCTS[pid - 1]
            if cat == "Candles" and day >= CANDLES_STOPPED:
                continue
            qty = rng.randint(1, 3) * (5 if segment == "wholesale" else 1)
            discount = None if rng.random() < 0.8 else rng.choice([0.05, 0.1, 0.15])
            item_id += 1
            con.execute(
                "INSERT INTO order_items VALUES (?,?,?,?,?,?)",
                (item_id, order_id, pid, qty, price, discount),
            )
            total += qty * price * (1 - (discount or 0))
        if total == 0:  # every chosen product was a stopped candle: sell paper filters instead
            item_id += 1
            con.execute(
                "INSERT INTO order_items VALUES (?,?,?,?,?,?)",
                (item_id, order_id, 17, 1, 6.0, None),
            )
            total = 6.0
        total = round(total, 2)
        if status == "cancelled":
            continue
        invoice_id += 1
        terms = 30 if segment == "wholesale" else 0
        due = day + dt.timedelta(days=terms)
        con.execute(
            "INSERT INTO invoices VALUES (?,?,?,?,?)",
            (invoice_id, order_id, day.isoformat(), due.isoformat(), total),
        )
        method = (
            rng.choice(["card", "card", "cash", "transfer"]) if segment == "retail" else "transfer"
        )
        pay_roll = rng.random()
        if segment == "wholesale" and pay_roll < 0.25:
            continue  # unpaid invoice
        paid_day = day if terms == 0 else day + dt.timedelta(days=rng.randint(5, 45))
        if paid_day > END:
            continue
        if segment == "wholesale" and pay_roll < 0.40:
            first_part = round(total / 2, 2)  # partial payment
            payment_id += 1
            con.execute(
                "INSERT INTO payments VALUES (?,?,?,?,?)",
                (payment_id, invoice_id, paid_day.isoformat(), first_part, method),
            )
        else:
            payment_id += 1
            con.execute(
                "INSERT INTO payments VALUES (?,?,?,?,?)",
                (payment_id, invoice_id, paid_day.isoformat(), total, method),
            )
        if status == "refunded":
            refund_day = paid_day + dt.timedelta(days=rng.randint(1, 14))
            payment_id += 1
            con.execute(
                "INSERT INTO payments VALUES (?,?,?,?,?)",
                (payment_id, invoice_id, refund_day.isoformat(), -total, method),
            )

    expense_id = 0
    month = dt.date(2025, 1, 1)
    while month <= END:
        rows = [
            ("rent", "Halvorsen Property", 1800.0, None),
            (
                "utilities",
                rng.choice(EXPENSE_VENDORS["utilities"]),
                round(rng.uniform(380, 620), 2),
                None,
            ),
        ]
        for _ in range(rng.randint(3, 6)):
            rows.append(
                (
                    "supplies",
                    rng.choice(EXPENSE_VENDORS["supplies"] + [None]),
                    round(rng.uniform(150, 1400), 2),
                    None,
                )
            )
        for _ in range(rng.randint(0, 2)):
            rows.append(
                (
                    "marketing",
                    rng.choice(EXPENSE_VENDORS["marketing"] + [None]),
                    round(rng.uniform(100, 900), 2),
                    None,
                )
            )
        if rng.random() < 0.3:
            rows.append(("repairs", "Dunmore Fixit", round(rng.uniform(80, 700), 2), None))
        for emp in range(2, len(ROLES) + 1):
            rows.append(("payroll", None, round(rng.uniform(250, 650), 2), emp))
        for cat, vendor, amount, emp in rows:
            next_month = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
            day = _day(rng, month, min(next_month - dt.timedelta(days=1), END))
            expense_id += 1
            con.execute(
                "INSERT INTO expenses VALUES (?,?,?,?,?,?)",
                (expense_id, day.isoformat(), cat, vendor, amount, emp),
            )
        month = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

    con.commit()
    con.execute("VACUUM")
    con.close()
    return path


def content_hash(path: Path) -> str:
    """Hash of the SQL dump, so two builds can be compared without byte-level noise."""
    con = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
    h = hashlib.sha256()
    for line in con.iterdump():
        h.update(line.encode())
    con.close()
    return h.hexdigest()


if __name__ == "__main__":
    print(build(DB_PATH))
