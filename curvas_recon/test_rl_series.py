from rl_series import (aggregate_recovery, aggregate_weighted_rl, cached_tms_map,
                       build_rl_recovery_figure, campaign_daily_flows,
                       case_irrigation_rows, cumulative_rl, cumulative_campaign_rl,
                       flows_for_mode)


def test_rl_is_daily_volume_over_tms_and_missing_is_date_local():
    q = {"d1": 1.0, "d2": 2.0}
    assert cumulative_rl(q, 24) == {"d1": 1.0, "d2": 2.0}
    assert cumulative_rl(q, None) == {}
    assert cumulative_rl({"d1": 1.0, "d2": None, "d3": 1.0}, 24) == {
        "d1": 1.0, "d2": None, "d3": 1.0,
    }


def test_group_daily_rl_aggregates_physical_volume_and_tms_before_division():
    # Daily physical volume 72 m3 / combined TMS 40 = 1.8 m3/t/day.
    result = aggregate_weighted_rl({"a": {"d1": 1}, "b": {"d1": 2}},
                                   {"a": 10, "b": 30})
    assert result == {"d1": 1.8}
    assert aggregate_weighted_rl({"a": {"d1": 1}, "b": {"d1": 2}},
                                 {"a": 10, "b": None}) == {}


def test_group_gaps_are_local_and_member_before_start_contributes_zero():
    # B is zero before its start; a missing date does not invalidate later dates.
    result = aggregate_weighted_rl(
        {"a": {"d1": 1, "d2": 1}, "b": {"d2": 2}},
        {"a": 10, "b": 30},
    )
    assert result == {"d1": 0.6, "d2": 1.8}


def test_group_recovery_sums_cu_and_missing_dates_remain_gaps():
    result = aggregate_recovery({"a": {"d1": 1, "d2": None},
                                 "b": {"d1": 3, "d2": 4}},
                                {"a": 10, "b": 30})
    assert result["d1"] == 10.0
    assert result["d2"] is None


def test_figure_uses_two_axes_and_omits_missing_series():
    fig = build_rl_recovery_figure(["d1", "d2"], [10, 20], [1.2, None])
    assert len(fig.data) == 2
    assert fig.data[0].yaxis == "y"
    assert fig.data[1].yaxis == "y2"
    assert fig.data[1].name == "Tasa de lixiviaci\u00f3n"
    assert "m\u00b3/t/d\u00eda" in fig.layout.yaxis2.title.text
    empty = build_rl_recovery_figure([], [], [])
    assert len(empty.data) == 0 and empty.layout.annotations


def test_authoritative_tms_load_is_lazy_and_cached_per_key():
    cache, calls = {}, []
    assert calls == []  # mounting or displaying another tab does not call the loader
    loader = lambda: calls.append("read") or {("OXIDOS", 1): {"tms": 10}}
    first = cached_tms_map(cache, ("run-1", "2026-10-01"), loader)
    again = cached_tms_map(cache, ("run-1", "2026-10-01"), loader)
    assert first is again
    assert calls == ["read"]


def test_case_q_overrides_measured_flow_only_on_case_dates():
    import pandas as pd
    result = campaign_daily_flows(
        {pd.Timestamp("2026-09-29"): 500, pd.Timestamp("2026-10-01"): 100,
         pd.Timestamp("2026-10-03"): 100},
        {pd.Timestamp("2026-10-02"): 150}, "2026-10-01", "2026-10-03",
    )
    assert result == {
        pd.Timestamp("2026-10-01"): 100,
        pd.Timestamp("2026-10-02"): 150,
        pd.Timestamp("2026-10-03"): 100,
    }


def test_group_younger_campaign_ignores_old_pile_positive_flow():
    import pandas as pd
    result = campaign_daily_flows(
        {pd.Timestamp("2026-09-20"): 900, pd.Timestamp("2026-10-02"): 100}, {},
        "2026-10-01", "2026-10-03",
    )
    assert list(result.values()) == [100, None]


def test_case_payload_nested_pile_rows_inherit_p21_and_override_q():
    import pandas as pd
    raw = {"res": {"piles": [{"label": "SULFUROS", "parcela": "P21",
                                "daily": [{"date": "2026-10-02", "q_riego_final": 150}]}]}}
    case = case_irrigation_rows(raw, "SULFUROS", 21, "2026-10-01", "2026-10-03")
    assert case == {pd.Timestamp("2026-10-02"): 150.0}
    daily = campaign_daily_flows(
        {pd.Timestamp("2026-10-01"): 100, pd.Timestamp("2026-10-02"): 100,
         pd.Timestamp("2026-10-03"): 100}, case, "2026-10-01", "2026-10-03")
    assert list(daily.values()) == [100, 150.0, 100]


def test_rl_modes_use_measured_or_case_q_as_requested():
    measured = {"d1": 10, "d2": 20, "d3": 30}
    reconciled = {"d2": 99}
    assert flows_for_mode(measured, reconciled, "medido") == measured
    assert flows_for_mode(measured, reconciled, "reconciliado") == {
        "d1": 10, "d2": 99, "d3": 30,
    }


def test_group_gap_only_marks_missing_date_not_later_days():
    result = aggregate_weighted_rl(
        {"a": {"d1": 1, "d2": None, "d3": 2}, "b": {"d1": 1, "d2": 1, "d3": 1}},
        {"a": 10, "b": 30},
    )
    assert result == {"d1": 1.2, "d2": None, "d3": 1.8}
def test_cumulative_campaign_rl_uses_f0_and_known_zero_plateau():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=4)
    values = {'p1': dict(zip(days, [0, 2, 0, 1]))}
    result = cumulative_campaign_rl(values, {'p1': 100}, {'p1': days[0]})
    assert list(result.values()) == [0, 0.48, 0.48, 0.72]


def test_cumulative_campaign_rl_group_sums_volume_over_total_tms():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=3)
    values = {'p1': dict(zip(days, [1, 2, 0])),
              'p2': dict(zip(days[1:], [3, 0]))}
    result = cumulative_campaign_rl(values, {'p1': 100, 'p2': 300},
                                    {'p1': days[0], 'p2': days[1]})
    assert result[days[0]] == 0.06
    assert result[days[1]] == 0.36
    assert result[days[2]] == 0.36


def test_cumulative_campaign_rl_gap_makes_future_unknown_without_reset():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=4)
    values = {'p1': dict(zip(days, [0, 2, None, 1]))}
    result = cumulative_campaign_rl(values, {'p1': 100}, {'p1': days[0]})
    assert result[days[0]] == 0
    assert result[days[1]] == 0.48
    assert result[days[2]] is None
    assert result[days[3]] is None


def test_cumulative_campaign_rl_ignores_missing_prefix_before_first_riego():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=4)
    values = {'p1': {days[0]: None, days[1]: None, days[2]: 2, days[3]: 1}}
    result = cumulative_campaign_rl(values, {'p1': 100}, {'p1': days[0]})
    assert result[days[0]] == 0
    assert result[days[1]] == 0
    assert result[days[2]] == 0.48
    assert result[days[3]] == 0.72


def test_cumulative_campaign_rl_missing_calendar_date_is_explicit_gap():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=4)
    values = {'p1': {days[0]: 0, days[1]: 2, days[3]: 1}}
    result = cumulative_campaign_rl(values, {'p1': 100}, {'p1': days[0]})
    assert result[days[1]] == 0.48
    assert result[days[2]] is None
    assert result[days[3]] is None


def test_cumulative_campaign_rl_new_member_born_later_starts_at_zero():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=3)
    values = {'old': dict(zip(days, [1, 1, 1])),
              'new': {days[1]: 2, days[2]: 0}}
    result = cumulative_campaign_rl(values, {'old': 100, 'new': 100},
                                    {'old': days[0], 'new': days[1]})
    assert result[days[0]] == 0.12
    assert result[days[1]] == 0.48


def test_cumulative_campaign_rl_all_missing_without_positive_is_unknown_from_f0():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=2)
    result = cumulative_campaign_rl({'p1': {days[1]: None}}, {'p1': 100},
                                    {'p1': days[0]})
    assert result == {days[0]: None, days[1]: None}


def test_cumulative_campaign_rl_continuous_explicit_zeros_are_known_zero():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=3)
    result = cumulative_campaign_rl({'p1': dict.fromkeys(days, 0)}, {'p1': 100},
                                    {'p1': days[0]})
    assert list(result.values()) == [0, 0, 0]


def test_cumulative_campaign_rl_nonpositive_zero_then_gap_stays_unknown():
    import pandas as pd
    days = pd.date_range('2026-01-01', periods=4)
    result = cumulative_campaign_rl({'p1': {days[0]: 0, days[1]: None,
                                            days[2]: 0, days[3]: 0}},
                                    {'p1': 100}, {'p1': days[0]})
    assert result == {days[0]: 0, days[1]: None, days[2]: None, days[3]: None}


def test_cumulative_campaign_rl_invalid_tms_or_f0_returns_empty_without_raising():
    import pandas as pd
    day = pd.Timestamp('2026-01-01')
    values = {'p1': {day: 1}}
    assert cumulative_campaign_rl(values, {'p1': 'bad'}, {'p1': day}) == {}
    assert cumulative_campaign_rl(values, {'p1': 100}, {'p1': pd.NaT}) == {}
