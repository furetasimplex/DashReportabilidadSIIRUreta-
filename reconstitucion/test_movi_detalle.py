import importlib.util
from pathlib import Path
from unittest.mock import patch

import pandas as pd

MODULE_PATH = Path(__file__).with_name("movi_detalle.py")
spec = importlib.util.spec_from_file_location("movi_detalle_staging", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def walk(component):
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from walk(child)
    elif hasattr(children, "children"):
        yield from walk(children)


def test_query_is_fixed_source_shift_date_destination_and_full_rows():
    captured = {}
    expected = pd.DataFrame([{"mov_id": 7, "Fecha": pd.Timestamp("2026-10-01"), "Turno": "TA", "Destino": "CH01"}])

    def fake_read_sql(sql, engine, params):
        captured.update(sql=str(sql), engine=engine, params=params)
        return expected

    with patch.object(mod.pd, "read_sql", fake_read_sql):
        frame, truncated = mod.load_movimientos("fake-engine", fecha="2026-10-01", turno="TA")

    assert frame.equals(expected) and not truncated
    assert captured["engine"] == "fake-engine"
    assert "FROM inventar_SpcHidr.inventar_SpcHidr.[mov_cam]" in captured["sql"]
    assert "SELECT TOP (:limite) *" in captured["sql"]
    assert "[Fecha] = :fecha AND [Turno] = :turno AND [Destino] = :destino" in captured["sql"]
    assert "GROUP BY" not in captured["sql"] and "SUM(" not in captured["sql"]
    assert captured["params"] == {"limite": 2001, "fecha": pd.Timestamp("2026-10-01").date(), "turno": "TA", "destino": "CH01"}


def test_popup_has_scope_warning_all_columns_and_json_safe_rows():
    frame = pd.DataFrame({"Fecha": [pd.Timestamp("2026-10-01")], "Ton": [float("nan")], "mov_id": [3]})
    popup = mod.popup_movimientos(frame, caso="C1", modulo=15, fecha="2026-10-01", turno="TA")
    text = str(popup)
    assert "Registros del turno; la fuente no identifica módulo ni hora individual." in text
    assert popup.id == "reconstitucion-tabla-detalle"
    table = next(component for component in walk(popup) if type(component).__name__ == "DataTable")
    assert [c["id"] for c in table.columns] == ["Fecha", "Ton", "mov_id"]
    assert table.data == [{"Fecha": "2026-10-01T00:00:00", "Ton": None, "mov_id": 3}]
    assert table.page_action == "native" and table.page_size == 20


def test_loader_rejects_invalid_shift_without_query():
    with patch.object(mod.pd, "read_sql") as read_sql:
        try:
            mod.load_movimientos("unused", fecha="2026-10-01", turno="A")
        except ValueError:
            pass
        else:
            raise AssertionError("expected invalid shift to raise")
        read_sql.assert_not_called()

