"""Staged tests for primary-reading fallback in campaign history."""
import ast
from pathlib import Path

import numpy as np
import pandas as pd


def historical_function():
    path = Path(__file__).with_name("pad_dashboard.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "_historical_recovery_values")
    ns = {"pd": pd, "np": np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), ns)
    return ns[node.name]


def test_primary_fallback_fills_gaps_without_changing_case_baseline():
    fn = historical_function()
    days = pd.date_range("2026-01-01", periods=3)
    cycles = [{"dates": list(days), "values": [10.0, 20.0, 30.0]}]
    rows = [
        {"date": days[1], "increment_tcu": 2.0},
        {"date": days[2], "increment_tcu": 5.0},
    ]
    points, baseline, official, sources = fn(
        "OXIDOS", 1, "2026-01-01", "2026-01-04", 100.0, cycles, rows, [], return_sources=True)

    assert points[days[0]] == 10.0  # anchor reading fills its missing recon point
    assert points[days[1]] == 12.0  # persisted increment remains authoritative
    assert points[days[2]] == 17.0  # reading cannot overwrite valid saved recon
    assert baseline == 17.0  # Case baseline remains the pre-fallback recon baseline
    assert official == set()
    assert sources[days[0]] == "Histórico reconciliado (registro histórico)"
    assert sources[days[1]] == "Histórico reconciliado guardado"


def test_official_fixture_value_keeps_priority_over_primary_fallback():
    fn = historical_function()
    day = pd.Timestamp("2026-01-02")
    cycles = [{"dates": [day], "values": [21.0]}]
    official_rows = [{"label": "OXIDOS", "parcela": "P01",
                      "date": day, "value_pct": 21.0}]
    points, baseline, official, sources = fn(
        "OXIDOS", 1, "2026-01-01", "2026-01-03", 100.0,
        cycles, [], official_rows, return_sources=True)

    assert points[day] == 21.0
    assert official == {day}
    assert sources[day] == "Histórico reconciliado (oficial)"
    assert baseline == 21.0  # validated official baseline retains existing behavior


def test_readings_before_campaign_start_are_excluded():
    fn = historical_function()
    old, current = pd.Timestamp("2025-12-31"), pd.Timestamp("2026-01-02")
    cycles = [{"dates": [old, current], "values": [80.0, 12.0]}]
    points, _baseline, _official, sources = fn(
        "OXIDOS", 1, "2026-01-01", "2026-01-03", 100.0,
        cycles, [], [], return_sources=True)
    assert old not in points
    assert points[current] == 12.0
    assert sources[current] == "Histórico reconciliado (registro histórico)"


def test_primary_only_fallback_does_not_become_reconstructed_case_baseline():
    fn = historical_function()
    days = pd.date_range("2026-01-01", periods=2)
    cycles = [{"dates": list(days), "values": [11.0, 14.0]}]
    points, baseline, _official, sources = fn(
        "OXIDOS", 1, "2026-01-01", "2026-01-03", 100.0, cycles, [], [], return_sources=True)
    assert points[days[-1]] == 14.0
    assert sources[days[-1]] == "Histórico reconciliado (registro histórico)"
    assert baseline is None



def test_return_contract_stays_three_by_default_and_four_with_sources():
    fn = historical_function()
    normal = fn("OXIDOS", 1, "2026-01-01", "2026-01-02", 100.0, [], [], [])
    sourced = fn("OXIDOS", 1, "2026-01-01", "2026-01-02", 100.0,
                 [], [], [], return_sources=True)
    assert len(normal) == 3
    assert len(sourced) == 4
    assert normal == ({}, None, set())
    assert sourced == ({}, None, set(), {})
