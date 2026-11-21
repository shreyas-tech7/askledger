import collections

from askledger import db, hostile, safety


def test_suite_size_and_attack_types():
    attacks = hostile.load()
    assert len(attacks) >= 40
    kinds = collections.Counter(a.attack_type for a in attacks)
    for kind in ("drop", "update", "delete", "insert", "attach", "read_file", "endless", "pragma"):
        assert kinds[kind] >= 2, kind
    assert all(a.question.strip() and a.sql.strip() and a.expected_reason for a in attacks)


def test_safety_layer_blocks_every_hostile_query_with_its_reason():
    """Feed the hostile SQL straight to the safety layer, as if the model wrote it.

    Broken case: an empty allowlist check (authorizer returning OK) lets the CTE writes and
    the schema reads through. See test_safety.test_authorizer_alone_blocks_a_write.
    """
    before = db.content_hash(db.DB_PATH)
    for a in hostile.load():
        got = hostile.outcome(a.sql, time_limit_s=0.5)
        assert got != "allowed", a.id
        assert got == a.expected_reason, (a.id, got)
    assert db.content_hash(db.DB_PATH) == before


def test_public_run_blocks_every_hostile_query():
    for a in hostile.load():
        try:
            safety.run(a.sql, time_limit_s=0.5)
        except (safety.Blocked, safety.SQLError):
            continue
        raise AssertionError(f"{a.id} ran")


def test_layer_matrix_full_stack_blocks_all_and_layers_overlap():
    rows = hostile.layer_matrix(time_limit_s=0.3)
    assert all(r["full"] != "allowed" for r in rows)
    writes = [r for r in rows if r["attack_type"] in hostile.WRITE_TYPES]
    assert all(r["authorizer_only"] != "allowed" for r in writes)
    # Pinned finding: the read-only URI alone still lets CREATE TEMP TABLE run, because the
    # temp schema lives in memory. The authorizer is what stops it.
    temp = [r for r in writes if r["id"] == "h19"]
    assert temp and temp[0]["read_only_only"] == "allowed"
    assert all(r["read_only_only"] != "allowed" for r in writes if r["id"] != "h19")
