from askledger.compare import same_result


def test_multiset_ignores_row_order_when_not_ordered():
    """Broken case: a plain list compare marks a correct GROUP BY answer wrong."""
    assert same_result([("a", 1), ("b", 2)], [("b", 2), ("a", 1)], ordered=False)


def test_multiset_counts_duplicates():
    assert not same_result([("a",), ("a",)], [("a",)], ordered=False)


def test_order_counts_when_question_asks_for_it():
    assert not same_result([("a", 1), ("b", 2)], [("b", 2), ("a", 1)], ordered=True)
    assert same_result([("a", 1), ("b", 2)], [("a", 1), ("b", 2)], ordered=True)


def test_floats_round_to_two_decimals():
    """Broken case: 14.999999 from SUM of floats against a gold ROUND(..., 2) of 15.0."""
    assert same_result([(14.999999,)], [(15.0,)], ordered=False)
    assert same_result([(3,)], [(3.0,)], ordered=False)
    assert not same_result([(14.98,)], [(15.0,)], ordered=False)
    assert same_result([(-0.001,)], [(0.0,)], ordered=False)


def test_column_names_are_ignored_but_column_order_counts():
    # names never reach the comparison: only row tuples do
    assert same_result([("Ashford", 27)], [("Ashford", 27)], ordered=False)
    assert not same_result([(27, "Ashford")], [("Ashford", 27)], ordered=False)


def test_nulls_and_text():
    assert same_result([(None,)], [(None,)], ordered=False)
    assert not same_result([("Tea",)], [("tea",)], ordered=False)
