"""Plain descriptions of every table and column. Schema linking and the LLM prompt use them."""

from __future__ import annotations

TABLES = {
    "customers": (
        "People and businesses who buy from us: retail shoppers and wholesale cafes.",
        {
            "customer_id": "customer id",
            "name": "customer name",
            "city": "city where the customer lives or is based",
            "email": "email address, can be missing (null)",
            "segment": "retail or wholesale customer segment",
            "signup_date": "date the customer signed up",
        },
    ),
    "products": (
        "Items we sell: coffee, tea, mugs, brewing gear, gift cards and discontinued candles.",
        {
            "product_id": "product id",
            "name": "current product name",
            "former_name": "old product name before a rename, usually null",
            "category": "product category such as Coffee, Tea, Mugs, Brewing Gear, Gift Cards, Candles",
            "unit_price": "list price of one unit",
            "discontinued": "1 if the product is no longer sold, else 0",
        },
    ),
    "employees": (
        "Staff: owner, manager, baristas, roasters, bookkeeper, delivery driver.",
        {
            "employee_id": "employee id",
            "name": "employee name",
            "role": "job role such as barista, roaster, manager, bookkeeper, delivery, owner",
            "hire_date": "date hired",
            "hourly_rate": "pay per hour",
            "manager_id": "employee id of the manager this employee reports to",
        },
    ),
    "orders": (
        "Orders placed by customers in the store or online, taken by an employee.",
        {
            "order_id": "order id",
            "customer_id": "customer who placed the order",
            "employee_id": "employee who took or handled the order",
            "order_date": "date the order was placed",
            "shipped_date": "date an online order shipped, null if not shipped",
            "channel": "store or online sales channel",
            "status": "completed, cancelled or refunded order status",
        },
    ),
    "order_items": (
        "Order lines: which products and how many units each order had. Sales and revenue "
        "are quantity times unit price less discount.",
        {
            "order_item_id": "order line id",
            "order_id": "order this line belongs to",
            "product_id": "product sold on this line",
            "quantity": "units sold",
            "unit_price": "price per unit on this line",
            "discount": "discount fraction such as 0.1, null when no discount",
        },
    ),
    "invoices": (
        "Invoices billed to customers for orders. The invoiced amount is what we billed.",
        {
            "invoice_id": "invoice id",
            "order_id": "order the invoice bills",
            "issue_date": "date the invoice was issued",
            "due_date": "date payment is due",
            "amount": "invoice total amount billed",
        },
    ),
    "payments": (
        "Money received against invoices. Refunds are negative payments.",
        {
            "payment_id": "payment id",
            "invoice_id": "invoice this payment pays",
            "payment_date": "date the money was received or refunded",
            "amount": "amount paid, negative for a refund",
            "method": "card, cash or transfer payment method",
        },
    ),
    "expenses": (
        "Money we spend: rent, utilities, supplies, marketing, repairs and payroll costs.",
        {
            "expense_id": "expense id",
            "expense_date": "date of the expense",
            "category": "expense category: rent, utilities, supplies, marketing, repairs, payroll",
            "vendor": "who we paid, null for payroll or unknown",
            "amount": "amount spent",
            "employee_id": "employee paid, for payroll rows",
        },
    ),
}

# Foreign keys as an undirected graph, for join paths.
JOINS = {
    ("customers", "orders"): "orders.customer_id = customers.customer_id",
    ("employees", "orders"): "orders.employee_id = employees.employee_id",
    ("order_items", "orders"): "order_items.order_id = orders.order_id",
    ("order_items", "products"): "order_items.product_id = products.product_id",
    ("invoices", "orders"): "invoices.order_id = orders.order_id",
    ("invoices", "payments"): "payments.invoice_id = invoices.invoice_id",
    ("employees", "expenses"): "expenses.employee_id = employees.employee_id",
}


def describe(table: str) -> str:
    text, cols = TABLES[table]
    lines = [f"{table}: {text}"]
    lines += [f"  {c}: {d}" for c, d in cols.items()]
    return "\n".join(lines)


def prompt_schema(tables=None) -> str:
    return "\n".join(describe(t) for t in (tables or TABLES))
