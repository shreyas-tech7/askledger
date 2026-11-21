from askledger import linking, questions


def test_link_finds_the_tables_a_question_needs():
    tables = linking.link("How many units of House Blend were sold in March 2025?")
    assert {"order_items", "products"} <= set(tables)


def test_join_closure_adds_the_tables_between_two_hits():
    # payments and customers only meet through invoices, so invoices must come along
    tables = linking.link("Total payments by customer city")
    assert "invoices" in tables


def test_recall_at_3_on_dev_is_high_enough():
    assert linking.recall(questions.load("dev"), k=3) >= 0.8


def test_recall_drops_when_the_index_is_broken(monkeypatch):
    monkeypatch.setattr(linking, "link", lambda q, k=3: ["employees"])
    assert linking.recall(questions.load("dev"), k=3) < 0.2


def test_gold_tables_reads_table_names_from_sql():
    sql = "SELECT c.name FROM customers c JOIN orders o ON o.customer_id = c.customer_id"
    assert linking.gold_tables(sql) == {"customers", "orders"}
