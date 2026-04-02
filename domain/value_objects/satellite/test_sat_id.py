from src.domain.value_objects.satellite.sat_id import SAT_ID_PATTERN


def test_re_sat_id():
    pattern = SAT_ID_PATTERN
    assert pattern.match("SCHX-0895-2361-9925-0309")
    assert pattern.match("TQZR-2957-1817-1062-1606")
    assert pattern.match(
        "IIII-0000-0000-0000-0000"
    )  # warn: в оригинальном shortuuid не должно быть I
    assert pattern.match("AAAA-0000-0000-0000-0000")

    assert pattern.match("AAAA--000-0000-0000-0000") is None
    assert pattern.match("1AAA-0000-0000-0000-0000") is None
    assert pattern.match("AAAA-z000-0000-0000-0000") is None
    assert pattern.match("AAAA-0000-b000-0000-0000") is None
    assert pattern.match("AAAA-0000-0000-c000-d000") is None
    assert pattern.match("AAAA-0000-0000-0000-000d") is None
    assert pattern.match("ZZ11-") is None
    assert pattern.match("AAAA00000000000000000000") is None
