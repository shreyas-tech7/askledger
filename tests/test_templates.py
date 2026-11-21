from askledger import evaluate, questions, safety
from askledger.templates import TemplateGenerator, period


def test_period_parses_months_quarters_halves_and_years():
    assert period("in March 2025") == ("2025-03-01", "2025-03-31")
    assert period("in Q2 2025") == ("2025-04-01", "2025-06-30")
    assert period("in the first half of 2026") == ("2026-01-01", "2026-06-30")
    assert period("in 2025") == ("2025-01-01", "2025-12-31")
    assert period("no date here") is None


def test_template_answers_the_example_question():
    sql = TemplateGenerator().generate("How many customers live in Ashford?", [])
    assert sql is not None
    rows = safety.run(sql).rows
    assert rows[0][0] > 0


def test_template_gives_up_on_an_unknown_shape():
    assert TemplateGenerator().generate("Write me a poem about coffee", []) is None


def test_template_sql_always_passes_the_safety_layer():
    gen = TemplateGenerator()
    for q in questions.load():
        sql = gen.generate(q.question, [])
        if sql:
            safety.run(sql)  # raises if blocked or broken


def test_template_dev_accuracy_is_high_and_heldout_is_lower():
    gen = TemplateGenerator()
    dev = [evaluate.correct(gen.generate(q.question, []), q) for q in questions.load("dev")]
    held = [evaluate.correct(gen.generate(q.question, []), q) for q in questions.load("heldout")]
    assert sum(dev) / len(dev) > 0.9
    assert sum(held) / len(held) < sum(dev) / len(dev)


def test_slot_values_can_never_carry_a_quote():
    from askledger.templates import SAFE_VALUE, vocab

    for values in vocab().values():
        assert values, "every slot has values"
        for v in values:
            assert SAFE_VALUE.fullmatch(v) and "'" not in v
