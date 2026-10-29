import importlib.util
from pathlib import Path

import pandas as pd

PATH = Path(__file__).with_name("detalle_reconstituido.py")
spec = importlib.util.spec_from_file_location("detalle_reconstituido_staging", PATH)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def fixture():
    day = pd.Timestamp("2026-10-04")
    itinerary = pd.DataFrame([
        {"id": "row-A", "pad_id": 2, "campana": 10009, "modulo": 15, "fecha": day, "turno": "TA", "masa_turno_asignada": 100},
        {"id": "row-B", "pad_id": 2, "campana": 10013, "modulo": 15, "fecha": day, "turno": "TA", "masa_turno_asignada": 700},
        {"id": "row-C", "pad_id": 1, "campana": 10009, "modulo": 2, "fecha": day, "turno": "TA", "masa_turno_asignada": 50},
    ])
    st = pd.DataFrame([
        {"pad_id": 2, "campana": 10009, "modulo": 15, "fecha": day, "masa_turno1": 100, "masa_turno2": 40, "masa_total": 140},
        {"pad_id": 2, "campana": 10013, "modulo": 15, "fecha": day, "masa_turno1": 700, "masa_turno2": 60, "masa_total": 760},
        {"pad_id": 1, "campana": 10009, "modulo": 2, "fecha": day, "masa_turno1": 50, "masa_turno2": 10, "masa_total": 60},
    ])
    res = {"shift_table": st, "perfil_turnos": pd.DataFrame([
        {"fecha": day, "turno": "A", "tmh": 120, "humedad": 8.0},
        {"fecha": day, "turno": "B", "tmh": 100, "humedad": 9.0},
    ])}
    quality = pd.DataFrame([
        {"fecha": day, "turno": "A", "FeT": 3.2, "CuT": 0.45, "origen_stock": 0.2},
        {"fecha": day, "turno": "B", "FeT": 3.0, "CuT": 0.4, "origen_stock": 0.1},
    ])
    return day, itinerary, res, quality


def test_resolve_row_preserves_complete_identity_and_parcela_convention():
    _, it, _, _ = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    assert (row["caso_id"], row["pad_id"], row["campana"], row["parcela"], row["modulo"], row["turno"]) == (77, 2, 10009, 3, 15, "TA")
    assert d.resolve_itinerary_record(it, "forged", caso_id=77) is None
    it.loc[it.id.eq("row-A"), "caso_id"] = 76
    assert d.resolve_itinerary_record(it, "row-A", caso_id=77) is None
    assert d.parcela_de(2, 1) == 1 and d.parcela_de(3, 2) == 1 and d.parcela_de(15, 2) == 3


def test_report_values_only_use_exact_case_pad_campaign_module_day_shift_mass():
    day, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    fields = d.consolidate_report_fields(res, row, quality)
    mass = fields.loc[fields.campo.eq("TMS asignada al módulo/turno"), "valor"].iloc[0]
    cu = fields.loc[fields.campo.eq("CuT"), "valor"].iloc[0]
    assert mass == 100  # not another campaign's 700 t, and not duplicated piece mass
    assert cu == 0.45
    assert fields.loc[fields.campo.eq("CuT"), "fuente"].iloc[0] == "calidad_turno · CuT_Real"
    assert "no es ensayo exclusivo" in fields.loc[fields.campo.eq("CuT"), "alcance"].iloc[0]
    assert fields.loc[fields.campo.eq("TMS asignada al módulo/turno"), "unidad"].iloc[0] == "t"


def test_official_attributes_require_all_identity_keys_including_campaign_and_parcela():
    _, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    official = pd.DataFrame([
        {"caso_id": 77, "pad_id": 2, "campana": 10013, "parcela": 3, "modulo": 15, "fecha": row["fecha"], "turno": "TA", "ACF03": 91},
        {"caso_id": 77, "pad_id": 2, "campana": 10009, "parcela": 3, "modulo": 15, "fecha": row["fecha"], "turno": "TA", "ACF03": 84},
    ])
    fields = d.consolidate_report_fields(res, row, quality, official)
    acf = fields.loc[fields.campo.eq("ACF03")].iloc[0]
    assert acf.valor == 84 and "Observado" in acf.alcance


def test_duplicate_shift_identity_fails_and_csv_keeps_provenance():
    _, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    res["shift_table"] = pd.concat([res["shift_table"], res["shift_table"].iloc[[0]]], ignore_index=True)
    try:
        d.consolidate_report_fields(res, row, quality)
    except ValueError as exc:
        assert "identidad duplicada" in str(exc)
    else:
        raise AssertionError("duplicate shift rows must fail closed")
    res["shift_table"] = res["shift_table"].iloc[:-1]
    csv = d.report_csv(d.consolidate_report_fields(res, row, quality))
    assert "caso_id,pad_id,campana,parcela,modulo,fecha,turno,clase,campo,valor,unidad,fuente,alcance,formula" in csv


def test_renderer_makes_movement_data_secondary_and_explicitly_nonattributed():
    _, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    fields = d.consolidate_report_fields(res, row, quality)
    popup = d.render_detail(fields, row, movement_frame=pd.DataFrame([{"mov_id": 1, "Fecha": "2026-10-04"}]))
    children = list(walk(popup))
    assert popup.id == "reconstitucion-tabla-detalle"
    details = next(component for component in children if type(component).__name__ == "Details")
    assert "no son movimientos comprobados de este módulo" in str(details)


def walk(component):
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from walk(child)
    elif hasattr(children, "children"):
        yield from walk(children)

def test_module_profile_quality_is_weighted_by_exact_campaign_module_tms():
    day, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    second = day + pd.Timedelta(days=1)
    extra = {"pad_id": 2, "campana": 10009, "modulo": 15, "fecha": second,
             "masa_turno1": 300, "masa_turno2": 0, "masa_total": 300}
    other_campaign = {"pad_id": 2, "campana": 10013, "modulo": 15, "fecha": second,
                      "masa_turno1": 900, "masa_turno2": 0, "masa_total": 900}
    res["shift_table"] = pd.concat([res["shift_table"], pd.DataFrame([extra, other_campaign])], ignore_index=True)
    quality = pd.concat([quality, pd.DataFrame([{"fecha": second, "turno": "A", "FeT": 4.0, "CuT": 0.55}])], ignore_index=True)
    summary = d.consolidate_module_profile(res, row, quality)
    cut = summary.loc[summary.campo.eq("CuT")].iloc[0]
    assert cut.valor == (100 * .45 + 40 * .40 + 300 * .55) / 440  # includes both turns; campaign 10013 excluded
    assert cut.turno == "A+B ponderado"
    assert cut.fuente == "calidad_turno · ponderado por TMS módulo/turno"


def test_profile_coefficient_uses_all_modules_in_same_pad_shift_and_scales_tmh():
    _, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    fields = d.consolidate_report_fields(res, row, quality)
    coef = fields.loc[fields.campo.eq("Coeficiente de asignación"), "valor"].iloc[0]
    tmh = fields.loc[fields.campo.eq("TMH perfil turno asignada al módulo"), "valor"].iloc[0]
    assert coef == 100 / 800  # includes the other campaign's module, excludes pad 1
    assert pd.isna(tmh)  # no pad_id and positive TMS on two pads


def test_profile_sums_tmh_from_two_belts_with_explicit_pad_identity():
    _, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    res["perfil_turnos"] = pd.DataFrame([
        {"pad_id": 2, "fecha": row["fecha"], "turno": "A", "tmh": 70, "humedad": 8.0},
        {"pad_id": 2, "fecha": row["fecha"], "turno": "TA", "tmh": 50, "humedad": 9.0},
        {"pad_id": 1, "fecha": row["fecha"], "turno": "A", "tmh": 900, "humedad": 2.0},
    ])
    fields = d.consolidate_report_fields(res, row, quality)
    tmh = fields.loc[fields.campo.eq("TMH perfil turno asignada al módulo"), "valor"].iloc[0]
    assert tmh == 120 * (100 / 800)


def test_origin_fraction_0_5_remains_0_5_in_shift_report():
    _, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    quality.loc[quality.turno.eq("A"), "origen_stock"] = 0.5
    fields = d.consolidate_report_fields(res, row, quality)
    assert fields.loc[fields.campo.eq("Origen stock"), "valor"].iloc[0] == 0.5


def test_popup_shows_identity_profile_attributes_and_exact_assigned_mass():
    _, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    fields = d.consolidate_report_fields(res, row, quality)
    popup = d.render_detail(fields, row)
    components = list(walk(popup))
    rendered = " ".join(str(component) for component in components)
    for label in ("Caso 77", "Pad 2", "Campaña 10009", "Parcela 3", "Módulo 15", "04-10-2026", "TA"):
        assert label in rendered
    table = next(component for component in components if type(component).__name__ == "DataTable")
    assert {"clase", "campo", "valor", "unidad", "fuente"}.issubset({c["id"] for c in table.columns})
    mass = next(record["valor"] for record in table.data if record["campo"] == "TMS asignada al módulo/turno")
    assert mass == 100


def test_movcam_pond_pool_uses_mina_stock_excludes_srr_and_scales_csr_by_copper():
    day, it, res, quality = fixture()
    row = d.resolve_itinerary_record(it, "row-A", caso_id=77)
    raw = pd.DataFrame([
        {"Fecha": day, "Turno": "TA", "Destino": "CH01", "Origen": "Mina", "Fase": "OXB", "Ton": 40, "CuTG00": 1.0, "ACF03": 50, "PONDACF03": 2000, "csrCCG15": .2, "PONDcsrCCG15": 8},
        {"Fecha": day, "Turno": "TA", "Destino": "CH01", "Origen": "Stock", "Fase": "TAL", "Ton": 60, "CuTG00": 2.0, "ACF03": 80, "PONDACF03": 4800, "csrCCG15": .4, "PONDcsrCCG15": 48},
        {"Fecha": day, "Turno": "TA", "Destino": "CH01", "Origen": "Stock", "Fase": "SRR", "Ton": 100, "CuTG00": 9.0, "ACF03": 99, "PONDACF03": 9900, "csrCCG15": .9, "PONDcsrCCG15": 810},
        {"Fecha": day, "Turno": "TA", "Destino": "CH01", "Origen": "Stock", "Fase": None, "Ton": 200, "CuTG00": 8.0, "ACF03": 99, "PONDACF03": 19800, "csrCCG15": .9, "PONDcsrCCG15": 1440},
        {"Fecha": day, "Turno": "TA", "Destino": "prueba", "Origen": "Mina", "Fase": "OXB", "Ton": 500, "CuTG00": 9.0, "ACF03": 1, "PONDACF03": 500, "csrCCG15": .1, "PONDcsrCCG15": 450},
    ])
    fields = d.consolidate_report_fields(res, row, quality, raw_mov_cam=raw)
    acf = fields.loc[fields.campo.eq("ACF03")].iloc[0]
    csr = fields.loc[fields.campo.eq("csrCC")].iloc[0]
    assert acf.valor == 68 and acf.unidad == "%"
    assert csr.valor == 35 and csr.unidad == "%"
    assert "CH01 Mina+Stock" in acf.fuente and "No incluye SRR" in acf.alcance
    assert "ΣPONDcsrCCG15/Σ(Ton×CuTG00)×100" in csr.formula
