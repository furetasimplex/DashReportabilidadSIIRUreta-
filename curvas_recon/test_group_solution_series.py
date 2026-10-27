import pandas as pd
import pytest

from group_solution_series import aggregate_group_solution_series


def _by_date(rows):
    return {row["date"].date().isoformat(): row for row in rows}


def test_concentration_is_weighted_by_each_flow_not_averaged():
    rows = aggregate_group_solution_series({
        "a": {"2026-10-01": {"q_riego": 10, "cu_riego": 2,
                              "q_pls": 4, "cu_pls": 5}},
        "b": {"2026-10-01": {"q_riego": 30, "cu_riego": 6,
                              "q_pls": 6, "cu_pls": 11}},
    })
    row = rows[0]
    assert row["q_riego"] == 40
    assert row["cu_riego"] == pytest.approx((10 * 2 + 30 * 6) / 40)
    assert row["q_pls"] == 10
    assert row["cu_pls"] == pytest.approx((4 * 5 + 6 * 11) / 10)


def test_zero_flow_with_missing_copper_is_zero_contribution():
    rows = aggregate_group_solution_series({
        "zero": {"2026-10-01": {"q_riego": 0, "cu_riego": None,
                                 "q_pls": 0, "cu_pls": float("nan")}},
        "flow": {"2026-10-01": {"q_riego": 12, "cu_riego": 3,
                                 "q_pls": 8, "cu_pls": 4}},
    })
    assert rows[0]["q_riego"] == 12
    assert rows[0]["cu_riego"] == 3
    assert rows[0]["q_pls"] == 8
    assert rows[0]["cu_pls"] == 4


def test_missing_member_and_omitted_calendar_dates_remain_unknown():
    rows = _by_date(aggregate_group_solution_series({
        "a": {"2026-10-01": {"q_riego": 4, "cu_riego": 2,
                              "q_pls": 2, "cu_pls": 3},
              "2026-10-03": {"q_riego": 0, "cu_riego": None,
                              "q_pls": 0, "cu_pls": None}},
        "b": {"2026-10-01": {"q_riego": 6, "cu_riego": 5,
                              "q_pls": 3, "cu_pls": 7}},
    }))
    assert list(rows) == ["2026-10-01", "2026-10-02", "2026-10-03"]
    assert rows["2026-10-01"]["q_riego"] == 10
    assert rows["2026-10-02"]["q_riego"] is None
    assert rows["2026-10-02"]["cu_riego"] is None
    # On day 3, member b is absent; its contribution is unknown, not zero.
    assert rows["2026-10-03"]["q_riego"] is None
    assert rows["2026-10-03"]["q_pls"] is None


def test_zero_total_flow_has_known_sum_but_undefined_concentration():
    rows = aggregate_group_solution_series({
        "a": {pd.Timestamp("2026-10-01 17:00"): {
            "q_riego": 0, "cu_riego": None, "q_pls": 0, "cu_pls": None}},
        "b": {pd.Timestamp("2026-10-01"): {
            "q_riego": 0, "cu_riego": 99, "q_pls": 0, "cu_pls": 1}},
    })
    assert rows[0]["date"] == pd.Timestamp("2026-10-01")
    assert rows[0]["q_riego"] == 0
    assert rows[0]["cu_riego"] is None
    assert rows[0]["q_pls"] == 0
    assert rows[0]["cu_pls"] is None


@pytest.mark.parametrize("bad_flow", [None, float("nan"), -1, "bad"])
def test_invalid_flow_does_not_become_zero_or_partial_sum(bad_flow):
    rows = aggregate_group_solution_series({
        "a": {"2026-10-01": {"q_riego": bad_flow, "cu_riego": 8,
                              "q_pls": 2, "cu_pls": 3}},
        "b": {"2026-10-01": {"q_riego": 7, "cu_riego": 4,
                              "q_pls": 3, "cu_pls": 5}},
    })
    assert rows[0]["q_riego"] is None
    assert rows[0]["cu_riego"] is None
    assert rows[0]["q_pls"] == 5
    assert rows[0]["cu_pls"] == pytest.approx((2 * 3 + 3 * 5) / 5)


def test_positive_flow_with_missing_concentration_keeps_flow_sum():
    rows = aggregate_group_solution_series({
        "a": {"2026-10-01": {"q_riego": 2, "cu_riego": None,
                              "q_pls": 1, "cu_pls": 5}},
        "b": {"2026-10-01": {"q_riego": 3, "cu_riego": 4,
                              "q_pls": 2, "cu_pls": 7}},
    })
    assert rows[0]["q_riego"] == 5
    assert rows[0]["cu_riego"] is None
    assert rows[0]["q_pls"] == 3
    assert rows[0]["cu_pls"] == pytest.approx((1 * 5 + 2 * 7) / 3)


def test_dates_are_normalized_to_timestamp():
    rows = aggregate_group_solution_series({
        "a": {pd.Timestamp("2026-10-01 23:45"): {
            "q_riego": 1, "cu_riego": 2, "q_pls": 1, "cu_pls": 3}},
    })
    assert rows[0]["date"] == pd.Timestamp("2026-10-01")
    assert isinstance(rows[0]["date"], pd.Timestamp)
