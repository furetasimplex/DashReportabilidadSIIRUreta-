from datetime import date

import pandas as pd

from rl_series import (aggregate_weighted_rl, common_positive_dates,
                        align_values_to_calendar)


def test_common_support_handles_offset_dates_gaps_and_zero_rl():
    days = [date(2026, 5, 22), date(2026, 5, 23), date(2026, 5, 24), date(2026, 5, 25)]
    recovery = {days[0]: 2.0, days[1]: 3.0, days[2]: 4.0, days[3]: None}
    rl = {days[0]: 0.0, days[2]: 0.2, date(2026, 5, 26): 0.3}

    support = common_positive_dates(days, recovery, rl)

    # Only May 24 is observed and strictly positive in both original series.
    assert support == {pd.Timestamp(days[2])}
    display_recovery = align_values_to_calendar(days, list(recovery.values()), days, support)
    display_rl = align_values_to_calendar(days, [rl.get(day) for day in days], days, support)
    positive_rec_dates = {pd.Timestamp(day) for day, value in zip(days, display_recovery)
                          if value is not None and value > 0}
    positive_rl_dates = {pd.Timestamp(day) for day, value in zip(days, display_rl)
                         if value is not None and value > 0}
    assert positive_rec_dates == positive_rl_dates == support
    assert recovery[days[0]] == 2.0  # presentation filter never mutates sources
    assert rl[days[0]] == 0.0       # explicit Q=0 remains a real zero


def test_group_weighted_rl_alignment_uses_same_positive_date_set():
    days = [date(2026, 5, 22), date(2026, 5, 23), date(2026, 5, 24)]
    group_rl = aggregate_weighted_rl(
        {
            'a': {days[0]: 1.0, days[1]: 0.0, days[2]: None},
            'b': {days[0]: 1.0, days[1]: 0.0, days[2]: 2.0},
        },
        {'a': 100.0, 'b': 100.0},
    )
    recovery = {days[0]: 1.0, days[1]: 2.0, days[2]: 3.0}
    support = common_positive_dates(days, recovery, group_rl)

    assert support == {pd.Timestamp(days[0])}
    positive_recovery = {pd.Timestamp(day) for day, value in recovery.items() if value > 0}
    positive_group_rl = {pd.Timestamp(day) for day, value in group_rl.items()
                         if value is not None and value > 0}
    assert support == positive_recovery & positive_group_rl
    assert group_rl[days[1]] == 0.0
    assert group_rl[days[2]] is None


def test_nonpositive_or_invalid_values_are_not_comparable():
    days = [date(2026, 10, 7), date(2026, 10, 8), date(2026, 10, 9)]
    recovery = {days[0]: 1.5, days[1]: 0.0, days[2]: 2.0}
    rl = {days[0]: 0.0, days[1]: 0.3, days[2]: float('nan')}

    assert common_positive_dates(days, recovery, rl) == set()


def test_alignment_preserves_date_specific_customdata_and_sources():
    source_dates = [date(2026, 9, 30), date(2026, 10, 2)]
    calendar = [date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 2)]
    original_y = [12.0, 14.0]
    original_hover = [['legacy', 8.0], ['case', 9.0]]
    support = {pd.Timestamp(calendar[0]), pd.Timestamp(calendar[2])}

    aligned_y = align_values_to_calendar(source_dates, original_y, calendar, support)
    aligned_hover = align_values_to_calendar(source_dates, original_hover, calendar, support)

    assert aligned_y == [12.0, None, 14.0]
    assert aligned_hover == [['legacy', 8.0], None, ['case', 9.0]]
    assert original_y == [12.0, 14.0]
    assert original_hover == [['legacy', 8.0], ['case', 9.0]]
