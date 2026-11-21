import random

from askledger import errorfix, experiments, pipeline


class Fixed:
    """A fake generator: returns a given first query and a given list of repairs."""

    name = "fake"

    def __init__(self, first, repairs=()):
        self.first = first
        self.repairs = list(repairs)
        self.calls = 0

    def generate(self, question, tables):
        return self.first

    def repair(self, question, sql, error, tables):
        self.calls += 1
        return self.repairs.pop(0) if self.repairs else None


GOOD = "SELECT COUNT(*) FROM customers"
BAD = "SELECT COUNT(*) FROM customer"


def test_fix_replaces_a_wrong_column_with_the_closest_real_one():
    sql = "SELECT SUM(qty) FROM order_items"
    assert errorfix.fix(sql, "no such column: qty") == "SELECT SUM(quantity) FROM order_items"


def test_fix_replaces_a_wrong_table():
    assert errorfix.fix(BAD, "no such table: customer") == GOOD


def test_fix_gives_up_on_an_error_it_does_not_know():
    assert errorfix.fix(GOOD, 'near "FROM": syntax error') is None


def test_repair_budget_zero_never_calls_repair():
    gen = Fixed(BAD, [GOOD])
    a = pipeline.answer("q", gen, max_repairs=0)
    assert not a.ok and gen.calls == 0 and a.repairs == 0


def test_one_repair_fixes_one_error():
    a = pipeline.answer("q", Fixed(BAD, [GOOD]), max_repairs=1)
    assert a.ok and a.repairs == 1 and a.attempts == 2 and a.sql == GOOD


def test_repairs_stop_at_the_budget():
    gen = Fixed(BAD, [BAD, BAD, GOOD])
    a = pipeline.answer("q", gen, max_repairs=2)
    assert not a.ok and gen.calls == 2 and "no such table" in a.error


def test_a_blocked_query_is_never_repaired():
    gen = Fixed("DELETE FROM customers", [GOOD])
    a = pipeline.answer("q", gen, max_repairs=2)
    assert a.blocked == "not_select" and gen.calls == 0


def test_corrupt_swaps_real_names_for_plausible_wrong_ones():
    sql, picked = experiments.corrupt("SELECT SUM(amount) FROM payments", random.Random(0))
    assert picked and sql != "SELECT SUM(amount) FROM payments"
    for name in picked:
        assert experiments.MISTAKES[name] in sql


def test_repair_study_more_budget_never_fixes_fewer():
    study = experiments.repair_study(seed=1)["by_repairs"]
    assert study["0"]["correct"] == 0
    assert study["0"]["correct"] <= study["1"]["correct"] <= study["2"]["correct"]


def test_fix_looks_only_at_columns_of_the_tables_in_the_query():
    cols = errorfix.columns_in_scope("SELECT 1 FROM expenses")
    assert "expense_date" in cols and "order_date" not in cols


def test_a_repair_can_make_a_valid_query_with_the_wrong_meaning():
    # "date" is close to several real date columns. The fixer picks one, and it can be wrong.
    sql = (
        "SELECT COUNT(*) FROM orders o JOIN invoices i ON i.order_id = o.order_id "
        "WHERE date > '2026'"
    )
    fixed = errorfix.fix(sql, "no such column: date")
    # the question meant order_date, the fixer picked another real date column
    assert fixed is not None and "order_date" not in fixed
