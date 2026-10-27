"""Pure RL/recovery series helpers staged for curvas_recon integration.

Daily leach rate (Tasa de lixiviación) is daily volume (m3/day) / TMS (t).
Campaign cumulative RL is total volume (m3) / TMS (t); legacy API names remain.
This module deliberately does not load operational history or query the database.
"""
from __future__ import annotations

from math import isfinite

import plotly.graph_objects as go


def cached_tms_map(cache, key, loader):
    """Load authoritative TMS lazily once for a validated Case/cut key."""
    if key not in cache:
        cache[key] = loader()
    return cache[key]


def overlay_case_flows(measured_daily_m3h, case_daily_m3h):
    """Use final Case irrigation on Case dates and preserve measured history elsewhere."""
    result = dict(measured_daily_m3h)
    result.update(case_daily_m3h)
    return result


def flows_for_mode(measured_daily_m3h, case_daily_m3h, mode):
    """Choose measured history or Case substitution for RL."""
    if mode == "medido":
        return dict(measured_daily_m3h)
    if mode == "reconciliado":
        return overlay_case_flows(measured_daily_m3h, case_daily_m3h)
    raise ValueError("RL mode must be 'medido' or 'reconciliado'")


def campaign_daily_flows(measured_daily_m3h, case_daily_m3h, campaign_start, asof):
    """Window riego to its own stack f0 and keep calendar gaps explicit."""
    import pandas as pd

    start, end = pd.Timestamp(campaign_start).normalize(), pd.Timestamp(asof).normalize()
    measured = {pd.Timestamp(day).normalize(): value for day, value in measured_daily_m3h.items()
                if start <= pd.Timestamp(day).normalize() <= end}
    case = {pd.Timestamp(day).normalize(): value for day, value in case_daily_m3h.items()
            if start <= pd.Timestamp(day).normalize() <= end}
    positive_days = []
    for day, value in list(measured.items()) + list(case.items()):
        try:
            if value is not None and isfinite(float(value)) and float(value) > 0:
                positive_days.append(day)
        except (TypeError, ValueError):
            continue
    if not positive_days:
        return None
    first = min(positive_days)
    days = pd.date_range(first, end, freq="D")
    series = {day: measured.get(day) for day in days}
    return overlay_case_flows(series, case)


def case_irrigation_rows(raw, label, pile_number, window_start, window_end):
    """Extract q_riego_final from either supported local payload daily shape."""
    import pandas as pd

    res = (raw or {}).get("res") or {}
    rows = res.get("daily") or []
    if not rows:
        rows = [dict(row, label=row.get("label", pile.get("label")),
                     parcela=row.get("parcela", row.get("p", pile.get("parcela", pile.get("p")))))
                for pile in (res.get("piles") or []) for row in (pile.get("daily") or [])]
    start, end = pd.Timestamp(window_start).normalize(), pd.Timestamp(window_end).normalize()
    result = {}
    for row in rows:
        try:
            row_num = str(row.get("parcela", row.get("p", ""))).strip().upper().removeprefix("P")
            if row.get("label", label) != label or int(row_num) != int(pile_number):
                continue
            day = pd.Timestamp(row["date"]).normalize()
            if start <= day <= end:
                value = row.get("q_riego_final")
                result[day] = float(value) if value is not None and isfinite(float(value)) else None
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return result


def measured_irrigation_rows(raw, label, pile_number, window_start, window_end):
    """Extract measured Q from either supported raw daily payload shape."""
    import pandas as pd

    res = (raw or {}).get("res") or {}
    rows = res.get("daily") or []
    if not rows:
        rows = [dict(row, label=row.get("label", pile.get("label")),
                     parcela=row.get("parcela", row.get("p",
                                 pile.get("parcela", pile.get("p")))))
                for pile in (res.get("piles") or [])
                for row in (pile.get("daily") or [])]
    start, end = pd.Timestamp(window_start).normalize(), pd.Timestamp(window_end).normalize()
    result = {}
    for row in rows:
        try:
            row_num = str(row.get("parcela", row.get("p", ""))).strip().upper().removeprefix("P")
            if row.get("label", label) != label or int(row_num) != int(pile_number):
                continue
            day = pd.Timestamp(row["date"]).normalize()
            if start <= day <= end:
                value = row.get("q_riego_medido")
                result[day] = float(value) if value is not None and isfinite(float(value)) else None
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return result


def cumulative_rl(daily_m3h, tms):
    """Return daily (Q m3/h * 24) / pile TMS; gaps affect their date only."""
    try:
        tms = float(tms)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return {}
    if not isfinite(tms) or tms <= 0:
        return {}
    out = {}
    for day, q in daily_m3h.items():
        try:
            value = float(q) if q is not None else float('nan')
        except (TypeError, ValueError, OverflowError):
            value = float('nan')
        out[day] = value * 24.0 / tms if isfinite(value) and value >= 0 else None
    return dict(sorted(out.items()))


def cumulative_campaign_rl(member_daily_m3h, member_tms, f0_by_member):
    """Campaign RL through each date; strict gaps keep the remaining sum unknown.

    Start each member at its first observed positive irrigation within f0.
    The earlier prefix does not contribute volume. If there is no positive
    irrigation, only explicit continuous zeros establish a known zero total.
    Missing days after operation starts make subsequent totals unknown.
    Sum member volumes and divide by total TMS; never average member RL.
    """
    import pandas as pd

    if (not member_daily_m3h or set(member_daily_m3h) != set(member_tms)
            or set(member_daily_m3h) != set(f0_by_member)):
        return {}
    try:
        tms = {member: float(value) for member, value in member_tms.items()}
    except (AttributeError, TypeError, ValueError, OverflowError):
        return {}
    if any(not isfinite(value) or value <= 0 for value in tms.values()):
        return {}
    try:
        starts = {member: pd.Timestamp(value).normalize()
                  for member, value in f0_by_member.items()}
    except (AttributeError, TypeError, ValueError, OverflowError):
        return {}
    if any(pd.isna(value) for value in starts.values()):
        return {}
    first_positive = {}
    normalized_series = {}
    for member, series in member_daily_m3h.items():
        normalized_series[member] = {}
        for day, value in series.items():
            try:
                normalized_series[member][pd.Timestamp(day).normalize()] = value
            except (AttributeError, TypeError, ValueError, OverflowError):
                continue
        positives = []
        for day, q in normalized_series[member].items():
            try:
                if (pd.Timestamp(day).normalize() >= starts[member]
                        and q is not None and isfinite(float(q)) and float(q) > 0):
                    positives.append(pd.Timestamp(day).normalize())
            except (TypeError, ValueError, OverflowError):
                pass
        first_positive[member] = min(positives) if positives else None
    data_dates = [day for series in normalized_series.values() for day in series]
    first_day = min([*starts.values(), *data_dates])
    last_day = max([*starts.values(), *data_dates])
    dates = list(pd.date_range(first_day, last_day, freq='D'))
    totals = {member: 0.0 for member in member_daily_m3h}
    unknown = {member: False for member in member_daily_m3h}
    out = {}
    for day in dates:
        complete = True
        for member, series in member_daily_m3h.items():
            if day < starts[member]:
                continue
            if first_positive[member] is not None and day < first_positive[member]:
                continue
            q = normalized_series[member].get(day)
            try:
                q = float(q) if q is not None else float('nan')
            except (TypeError, ValueError, OverflowError):
                q = float('nan')
            if not isfinite(q) or q < 0:
                unknown[member] = True
            elif not unknown[member]:
                totals[member] += q * 24.0
            if unknown[member]:
                complete = False
        out[day] = (sum(totals.values()) / sum(tms.values())
                    if complete else None)
    return out


def aggregate_weighted_rl(member_daily_m3h, member_tms):
    """Daily group RL = sum daily Q volumes / total member TMS."""
    if (not member_daily_m3h or set(member_daily_m3h) != set(member_tms)
            or any(v is None or not isfinite(float(v)) or float(v) <= 0
                   for v in member_tms.values())):
        return {}
    dates = sorted({day for series in member_daily_m3h.values() for day in series})
    weights = {member: float(value) for member, value in member_tms.items()}
    total_tms = sum(weights.values())
    result = {}
    for day in dates:
        flows = []
        for series in member_daily_m3h.values():
            first = min(series) if series else None
            if first is not None and day < first:
                flows.append(0.0)
                continue
            try:
                q = float(series.get(day)) if series.get(day) is not None else float('nan')
            except (TypeError, ValueError, OverflowError):
                q = float('nan')
            if not isfinite(q) or q < 0:
                flows = []
                break
            flows.append(q)
        result[day] = sum(flows) * 24.0 / total_tms if len(flows) == len(weights) else None
    return result


def aggregate_recovery(member_recovered_t, member_cutf_t):
    """Date-wise recovery: sum recovered Cu / sum CuTf; never mean percentages."""
    if (not member_recovered_t or set(member_recovered_t) != set(member_cutf_t)
            or any(v is None or not isfinite(float(v)) or float(v) <= 0
                   for v in member_cutf_t.values())):
        return {}
    dates = sorted({day for series in member_recovered_t.values() for day in series})
    denominator = sum(float(v) for v in member_cutf_t.values())
    if denominator <= 0:
        return {}
    out = {}
    for day in dates:
        vals = [series.get(day) for series in member_recovered_t.values()]
        if not vals or any(v is None or not isfinite(float(v)) for v in vals):
            out[day] = None
        else:
            out[day] = sum(float(v) for v in vals) / denominator * 100.0
    return out



def common_positive_dates(dates, recovery_by_date, rl_by_date):
    """Return calendar dates where both displayed comparison series are positive.

    Dates missing from either input, gaps, zero Q/RL, and non-finite values are
    excluded without filling or changing the source dictionaries.
    """
    import pandas as pd

    def normalized_map(values):
        result = {}
        for day, value in values.items():
            try:
                result[pd.Timestamp(day).normalize()] = float(value) if value is not None else float('nan')
            except (TypeError, ValueError, OverflowError):
                result[pd.Timestamp(day).normalize()] = float('nan')
        return result

    recovery = normalized_map(recovery_by_date)
    rl = normalized_map(rl_by_date)
    support = set()
    for day in dates:
        stamp = pd.Timestamp(day).normalize()
        try:
            rec_value, rl_value = recovery[stamp], rl[stamp]
        except KeyError:
            continue
        if isfinite(rec_value) and rec_value > 0 and isfinite(rl_value) and rl_value > 0:
            support.add(stamp)
    return support



def align_values_to_calendar(source_dates, source_values, calendar, support=None):
    """Align a series (including hover customdata) to a calendar without mutation."""
    import pandas as pd

    source = {pd.Timestamp(day).normalize(): value
              for day, value in zip(source_dates, source_values)}
    return [source.get(pd.Timestamp(day).normalize())
            if support is None or pd.Timestamp(day).normalize() in support else None
            for day in calendar]

def visible_xaxis_range(series):
    """Return bounds from finite values actually present in plotted series.

    Zero is a valid plotted value. Source calendars and internal None gaps are
    unaffected; a single visible date gets a one-day axis interval.
    """
    import pandas as pd

    visible = []
    for dates, values in series:
        if dates is None or values is None:
            continue
        for day, value in zip(dates, values):
            try:
                number = float(value)
                stamp = pd.Timestamp(day).normalize()
            except (TypeError, ValueError, OverflowError):
                continue
            if pd.notna(stamp) and isfinite(number):
                visible.append(stamp)
    if not visible:
        return None
    first, last = min(visible), max(visible)
    if first == last:
        last = first + pd.Timedelta(days=1)
    return [first.isoformat(), last.isoformat()]


def build_rl_recovery_figure(dates, recovery_pct, rl_m3_per_t, title="Recuperaci\u00f3n y tasa de lixiviaci\u00f3n"):
    """One shared time axis; recovery on left, daily leach rate (m3/t/day) on right."""
    fig = go.Figure()
    if any(v is not None for v in recovery_pct):
        fig.add_trace(go.Scatter(x=dates, y=recovery_pct, mode="lines", name="Recuperación",
                                 line={"color": "#E86D1F", "width": 2.5}, connectgaps=False,
                                 yaxis="y"))
    if any(v is not None for v in rl_m3_per_t):
        fig.add_trace(go.Scatter(x=dates, y=rl_m3_per_t, mode="lines", name="Tasa de lixiviaci\u00f3n",
                                 line={"color": "#2a78d6", "width": 2.5}, connectgaps=False,
                                 yaxis="y2"))
    fig.update_layout(title=title, xaxis_title="Fecha", yaxis_title="Recuperación (%)",
                      yaxis={"gridcolor": "#E5E7EB"},
                      yaxis2={"title": "Tasa de lixiviaci\u00f3n (m\u00b3/t/d\u00eda)", "overlaying": "y",
                              "side": "right", "showgrid": False},
                      xaxis={"gridcolor": "#E5E7EB"}, hovermode="x unified",
                      paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                      legend={"bgcolor": "rgba(0,0,0,0)"})
    if not fig.data:
        fig.add_annotation(text="No hay datos suficientes para mostrar recuperaci\u00f3n y tasa de lixiviaci\u00f3n.",
                           x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    return fig
