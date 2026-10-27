"""Pure daily aggregation for grouped pile flows and concentrations.

The caller supplies explicit zero rows for members that are known to have no
flow yet. Missing member/day records remain unknown and are never treated as
zero. Concentrations are flow weighted, using only a complete set of member
contributions for that day.
"""

from collections.abc import Mapping
import numpy as np
import pandas as pd


_FIELDS = ("q_riego", "q_pls")
_CONCENTRATIONS = {"q_riego": "cu_riego", "q_pls": "cu_pls"}


def _finite_number(value):
    """Return a finite float, or None for absent/non-numeric values."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if np.isfinite(number) else None


def _normalize_rows(member_rows):
    normalized = {}
    if not isinstance(member_rows, Mapping):
        return normalized
    for raw_day, values in member_rows.items():
        try:
            day = pd.Timestamp(raw_day).normalize()
        except (TypeError, ValueError, OverflowError):
            continue
        if pd.isna(day) or not isinstance(values, Mapping):
            continue
        normalized[day] = values
    return normalized


def aggregate_group_solution_series(member_series):
    """Aggregate per-member daily data into a complete calendar series.

    Args:
        member_series: ``{member_id: {date: {q_riego, q_pls, cu_riego,
            cu_pls}}}``. A member/date omitted from the input is unknown.

    Returns:
        A list of dictionaries, one per calendar day between the earliest and
        latest supplied valid date, with normalized ``Timestamp`` dates and
        ``q_riego``, ``q_pls``, ``cu_riego`` and ``cu_pls`` values. A flow sum
        is present only when every member has a valid nonnegative flow that
        day. Concentration is present only when all positive-flow member
        concentrations are valid and total flow is positive.
    """
    if not isinstance(member_series, Mapping) or not member_series:
        return []
    members = [(member, _normalize_rows(rows))
               for member, rows in member_series.items()]
    all_days = [day for _, rows in members for day in rows]
    if not all_days:
        return []
    calendar = pd.date_range(min(all_days), max(all_days), freq="D")
    result = []
    for day in calendar:
        output = {"date": day}
        for q_field in _FIELDS:
            cu_field = _CONCENTRATIONS[q_field]
            q_values = []
            contributions = []
            q_complete = True
            cu_complete = True
            for _, rows in members:
                daily = rows.get(day)
                if daily is None:
                    q_complete = cu_complete = False
                    continue
                q = _finite_number(daily.get(q_field))
                if q is None or q < 0:
                    q_complete = cu_complete = False
                    continue
                q_values.append(q)
                if q == 0:
                    # Zero flow has known zero mass even when concentration
                    # is undefined or absent.
                    contributions.append(0.0)
                    continue
                cu = _finite_number(daily.get(cu_field))
                if cu is None:
                    cu_complete = False
                else:
                    contributions.append(q * cu)

            total_q = sum(q_values) if q_complete else None
            output[q_field] = total_q
            if (q_complete and cu_complete and total_q is not None
                    and total_q > 0 and len(contributions) == len(members)):
                output[cu_field] = sum(contributions) / total_q
            else:
                output[cu_field] = None
        result.append(output)
    return result
