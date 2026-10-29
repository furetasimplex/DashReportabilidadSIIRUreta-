"""Focused regression tests for the added module report fields."""
import pandas as pd
import pytest

from reconstitucion import informe_modulos as im


def _sources():
    movements = []
    specs = [
        # Mina with unknown phase is retained; Stock with unknown phase is excluded.
        ("A", "Mina", None, 100.0, 1.0, 0.10),
        ("A", "Stock", None, 1000.0, 1.0, 0.99),
        ("B", "Stock", "Pila", 100.0, 2.0, 0.40),
    ]
    for turn, origin, phase, ton, cut, csr in specs:
        row = {"Fecha": pd.Timestamp("2026-10-01"), "Turno": turn,
               "Destino": "CH01", "Origen": origin, "Fase": phase,
               "Ton": ton, "CuTG00": cut}
        for i in range(3, 8):
            value = 10.0 if turn == "A" else 20.0
            row[f"ACF0{i}"] = value
            row[f"PONDACF0{i}"] = ton * value
        for i in range(1, 4):
            value = 30.0 if turn == "A" else 40.0
            row[f"Calidad0{i}"] = value
            row[f"PONDCalidad0{i}"] = ton * value
        for field, pond in [("csrCCG15", "PONDcsrCCG15"),
                            ("crsCVG16", "PONDcrsCVG16"),
                            ("csrCPYG17", "PONDcsrCPYG17"),
                            ("csrCUOXI", "PONDcsrCUOXI"),
                            ("csrCUINS", "PONDcsrCUINS")]:
            row[field] = csr
            row[pond] = ton * cut * csr
        movements.append(row)
    quality = pd.DataFrame([
        {"fecha": "2026-10-01", "turno": "A", "origen_mina": 60,
         "origen_stock": 30, "origen_srr": 10},
        {"fecha": "2026-10-01", "turno": "B", "origen_mina": 20,
         "origen_stock": 30, "origen_srr": 50},
    ])
    shifts = pd.DataFrame([
        {"pad_id": 2, "campana": 12, "modulo": 4,
         "fecha": pd.Timestamp("2026-10-01"), "masa_turno1": 10.0,
         "masa_turno2": 30.0},
    ])
    srr = pd.DataFrame([{
        "Fecha": pd.Timestamp("2026-10-01"), "Turno": "A",
        "SRR_TMS_Turno": 5.0, "CuT_SRR": .25, "CuS_SRR": .1,
        "ClayBeta_SRR": 5.0, "Malla100_SRR": 10.0, "CO3_SRR": .2,
        "Recuperacion_SRR": 70.0,
    }])  # Turn B is deliberately missing and must not be filled with zero.
    dco = pd.DataFrame([{
        "Fecha": pd.Timestamp("2026-10-01"), "Sal_turno_A": 1.0,
        "Sal_Turno_B": 2.0, "Apilado_TMH_turno_A": 100.0,
        "Apilado_TMH_turno_B": 200.0, "Humedad_Turno_A": 10.0,
        "Humedad_Turno_B": 20.0,
    }])
    return shifts, quality, pd.DataFrame(movements), srr, dco


def test_atribucion_mina_stock_srr_sal_y_denominadores():
    st, quality, movcam, srr, dco = _sources()
    out = im.derivar_campos_extra_por_modulo(st, quality, movcam, srr, dco).iloc[0]
    # Mina A: 10 t × 90%; Stock A with unknown phase is excluded.
    # Stock B: 30 t × 50%; ACF weights are 9 and 15.
    assert out.ACF03 == pytest.approx((10 * 9 + 20 * 15) / 24)
    # CSR weights additionally include primary CuT (1 for A, 2 for B).
    assert out.csrCC == pytest.approx(100 * (.1 * 9 + .4 * 30) / 39)
    assert out.cobertura_ACF03 == pytest.approx(24 / 40)
    assert out.cobertura_csrCC == pytest.approx(24 / 40)
    # SRR only has turn A; missing B is not treated as zero.
    assert out.CuT_SRR == pytest.approx(.25)
    assert out.cobertura_CuT_SRR == pytest.approx(1.0 / 40.0)
    assert out.sal_kg_t > 0
    assert out.cobertura_sal_kg_t == pytest.approx(1.0)


def test_default_runtime_loader_uses_read_only_source_adapter(monkeypatch):
    st, quality, movcam, srr, dco = _sources()
    captured = {"movcam": movcam, "srr": srr, "datos_turno": dco, "warnings": []}
    monkeypatch.setattr("reconstitucion.fuentes_informe.cargar_fuentes",
                        lambda engine, fecha_min, fecha_max: captured)
    monkeypatch.setattr("reconstitucion.fuentes_informe.cargar_reposo", lambda *args: (pd.DataFrame(), []))
    res = {"shift_table": st,
           "_informe_calidad_por_pad": {2: quality}}
    out = im.cargar_campos_extra(res, 2,
        {"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-01"}, object())
    assert len(out) == 1 and out.iloc[0].ACF03 > 0
    assert out.iloc[0].advertencias_fuentes == ""


def test_case_builder_keeps_mass_and_rejects_extra_module_outside_case():
    ap = pd.DataFrame([{
        "pad_id": 2, "campana": 12, "modulo": 4,
        "fecha": pd.Timestamp("2026-10-01"), "vol_diario": 1.0,
        "altura_prom": 10.0,
        "vol_acum_final": 1.0, "avance": 1.0,
    }])
    st = pd.DataFrame([{
        "pad_id": 2, "campana": 12, "modulo": 4,
        "fecha": pd.Timestamp("2026-10-01"), "TMH_dia": 100.0,
        "vol_dia_total": 1.0, "masa_total": 80.0,
        "masa_turno1": 40.0, "masa_turno2": 40.0,
    }])
    res = {"apilado": ap, "shift_table": st}
    quality = pd.DataFrame()
    extra = pd.DataFrame([{"campana": 12, "modulo": 4, "ACF03": 10.0}])
    frame = im.preparar_modulos_desde_resultado(res, 2, quality, extras=extra)
    assert frame.columns.is_unique
    assert frame.TMS.sum() == pytest.approx(80.0)
    extra.loc[0, "modulo"] = 99
    with pytest.raises(ValueError, match="fuera del Caso/pad"):
        im.preparar_modulos_desde_resultado(res, 2, quality, extras=extra)
