"""Staged detail for one reconstructed case/pad/campaign/module/day/shift.

The movement table is supplementary context: mov_cam has no module key.
This module performs no I/O and never infers a truck-to-module relationship.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import numpy as np
import pandas as pd
from dash import dash_table, html

MODULES_PER_PARCELA = {1: 2, 2: 5}  # oxide pad 1, sulfide pad 2
CALIDAD = {
    "FeT_Real": "FeT", "FeS_Real": "FeS", "CuT_Real": "CuT",
    "CuS_Real": "CuS", "CO3_Real": "CO3", "ConsH_Real": "consumo_H",
    "Solubilidad_Real": "solubilidad", "CuFe_Real": "CuFe",
    "CaolBeta_Real": "beta_clay", "STOCK": "origen_stock",
    "MINA": "origen_mina", "SRR": "origen_srr",
    "Malla_Menos_100_Real": "malla_100", "Malla_Menos_1_2_Real": "malla_media",
}
ORIGEN_FIELDS = {"origen_stock", "origen_mina", "origen_srr"}
FIELD_META = {
    "masa_turno_asignada": ("Masa", "TMS asignada al módulo/turno", "t"),
    "masa_total_dia": ("Masa", "TMS asignada al módulo/fecha (A+B)", "t"),
    "masa_turno1": ("Masa", "TMS turno A del módulo/fecha", "t"),
    "masa_turno2": ("Masa", "TMS turno B del módulo/fecha", "t"),
    "tmh": ("Perfil de turno", "TMH perfil turno", "t"),
    "humedad": ("Perfil de turno", "Humedad perfil turno", "%"),
    "FeT": ("Química reporte turno", "FeT", "%"),
    "FeS": ("Química reporte turno", "FeS", "%"),
    "CuT": ("Química reporte turno", "CuT", "%"),
    "CuS": ("Química reporte turno", "CuS", "%"),
    "CO3": ("Química reporte turno", "CO3", "%"),
    "consumo_H": ("Química reporte turno", "Consumo H+", "kg/t"),
    "solubilidad": ("Química reporte turno", "Solubilidad", "fracción (0–1)"),
    "CuFe": ("Química reporte turno", "CuFe", "%"),
    "beta_clay": ("Química reporte turno", "Beta Clay", "%"),
    "origen_stock": ("Química reporte turno", "Origen stock", "%"),
    "origen_mina": ("Química reporte turno", "Origen mina", "%"),
    "origen_srr": ("Química reporte turno", "Origen SRR", "%"),
    "malla_100": ("Química reporte turno", "Malla -100", "%"),
    "malla_media": ("Química reporte turno", "Malla 1/2 in", "%"),
}


def parcela_de(modulo, pad):
    if int(pad) not in MODULES_PER_PARCELA:
        raise ValueError(f"Pad no reconocido: {pad}")
    return int(np.ceil(int(modulo) / MODULES_PER_PARCELA[int(pad)]))


def resolve_itinerary_record(itinerary_frame, row_id, *, caso_id):
    """Resolve one server-created itinerary row; never trust browser row_data."""
    if itinerary_frame is None or itinerary_frame.empty or "id" not in itinerary_frame:
        return None
    hits = itinerary_frame.loc[itinerary_frame.id.astype(str).eq(str(row_id))]
    if len(hits) != 1:
        return None
    row = hits.iloc[0].to_dict()
    if pd.notna(row.get('caso_id')) and int(row['caso_id'])!=int(caso_id):
        return None
    required = {"pad_id", "campana", "modulo", "fecha", "turno"}
    if not required.issubset(row):
        return None
    row["caso_id"] = int(caso_id)
    row["pad_id"] = int(row["pad_id"])
    row["campana"] = int(row["campana"])
    row["modulo"] = int(row["modulo"])
    row["parcela"] = parcela_de(row["modulo"], row["pad_id"])
    row["fecha"] = pd.Timestamp(row["fecha"]).normalize()
    row["turno"] = str(row["turno"]).strip().upper()
    if row["turno"] not in {"TA", "TB"}:
        return None
    return row


def _one_exact(frame, keys, values, label):
    if frame is None or frame.empty or not set(keys).issubset(frame.columns):
        return None
    mask = pd.Series(True, index=frame.index)
    for key, value in zip(keys, values):
        if key == "fecha":
            mask &= pd.to_datetime(frame[key], errors="coerce").dt.normalize().eq(pd.Timestamp(value).normalize())
        else:
            mask &= frame[key].eq(value)
    hits = frame.loc[mask]
    if len(hits) > 1:
        raise ValueError(f"{label}: identidad duplicada para {dict(zip(keys, values))}")
    return hits.iloc[0] if len(hits) else None


def _add(rows, identity, category, field, unit, value, source, status, formula=""):
    rows.append({**identity, "clase": category, "campo": field,
                 "valor": value if pd.notna(value) else None, "unidad": unit,
                 "fuente": source, "alcance": status, "formula": formula})


def _json_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _records(frame):
    return [{k: _json_value(v) for k, v in row.items()}
            for row in frame.to_dict(orient="records")]


def _movcam_pool(frame, record):
    """Pool evidenced CH01 Mina+Stock PONDs for the selected date/turn."""
    if frame is None or frame.empty:
        return [], "Sin filas MOV_CAM para validar perfil Mina+Stock."
    required = {"Fecha", "Turno", "Destino", "Origen", "Ton", "Fase"}
    if not required.issubset(frame.columns):
        return [], "No se calculó ACF/CSR: mov_cam no contiene el set de campos de alcance requerido."
    mov = frame.copy()
    mov["_fecha"] = pd.to_datetime(mov.Fecha, errors="coerce").dt.normalize()
    mov["_turno"] = mov.Turno.astype(str).str.strip().str.upper()
    wanted = record["turno"]
    mov = mov.loc[mov._fecha.eq(record["fecha"]) & mov._turno.eq(wanted)
                  & mov.Destino.astype(str).str.strip().str.upper().eq("CH01")].copy()
    origin = mov.Origen.astype(str).str.strip().str.casefold()
    mov = mov.loc[origin.isin({"mina", "stock"})].copy()
    # Stock+SRR is not part of this proxy. If Fase is unavailable, fail closed.
    is_srr = mov.Fase.astype(str).str.strip().str.casefold().eq("srr")
    is_stock = mov.Origen.astype(str).str.strip().str.casefold().eq("stock")
    fase_known = mov.Fase.notna() & mov.Fase.astype(str).str.strip().ne("")
    mov = mov.loc[~(is_stock & (~fase_known | is_srr))]
    if mov.empty:
        return [], "Sin filas CH01 Mina+Stock no-SRR para el turno; no se infiere SRR."
    ton = pd.to_numeric(mov.Ton, errors="coerce")
    outputs = []
    for value, pond in [(f"ACF0{i}", f"PONDACF0{i}") for i in range(3, 8)]:
        if pond not in mov:
            continue
        pv = pd.to_numeric(mov[pond], errors="coerce")
        valid = pv.notna() & ton.notna()
        den = ton[valid].sum(min_count=1)
        val = pv[valid].sum(min_count=1) / den if pd.notna(den) and den > 0 else np.nan
        outputs.append(("ACF", value, val, "%", f"Σ{pond}/ΣTon", int(valid.sum())))
    for value, pond in [(f"Calidad0{i}", f"PONDCalidad0{i}") for i in range(1, 4)]:
        if pond not in mov:
            continue
        pv = pd.to_numeric(mov[pond], errors="coerce")
        valid = pv.notna() & ton.notna()
        den = ton[valid].sum(min_count=1)
        val = pv[valid].sum(min_count=1) / den if pd.notna(den) and den > 0 else np.nan
        outputs.append(("Calidad control mineral", value, val, "%", f"Σ{pond}/ΣTon", int(valid.sum())))
    cut = pd.to_numeric(mov.get("CuTG00", pd.Series(np.nan, index=mov.index)), errors="coerce")
    csr = [("CSR", "csrCC", "PONDcsrCCG15"), ("CSR", "csrCV", "PONDcrsCVG16"),
           ("CSR", "csrCPY", "PONDcsrCPYG17"), ("CSR", "csrCUOXI", "PONDcsrCUOXI"),
           ("CSR", "csrCUINS", "PONDcsrCUINS")]
    for category, value, pond in csr:
        if pond not in mov:
            continue
        pv = pd.to_numeric(mov[pond], errors="coerce")
        valid = pv.notna() & ton.notna() & cut.notna()
        den = (ton[valid] * cut[valid]).sum(min_count=1)
        val = 100.0 * pv[valid].sum(min_count=1) / den if pd.notna(den) and den > 0 else np.nan
        outputs.append((category, value, val, "%", f"Σ{pond}/Σ(Ton×CuTG00)×100", int(valid.sum())))
    return outputs, "Pool mov_cam CH01 · Mina+Stock con Fase conocida; excluye Stock/SRR y stock sin Fase. No incluye SRR."


def consolidate_report_fields(res, record, calidad=None, official_profile=None,
                              raw_mov_cam=None):
    """Build long report rows for the exact selected module/day/shift.

    `calidad` follows informe_modulos.calidad_turno(): one profile row per
    Fecha/Turno and columns from CALIDAD. Its measured shift chemistry is
    attributed to the selected module as a derived profile value; per-module
    report-wide values can be supplied in `official_profile`, but only exact
    case/pad/campaign/module/date/shift matches are accepted.
    """
    if record is None:
        return pd.DataFrame()
    identity = {k: record[k] for k in ("caso_id", "pad_id", "campana", "parcela", "modulo", "fecha", "turno")}
    st = res.get("shift_table")
    keys = ["pad_id", "campana", "modulo", "fecha"]
    vals = [record[k] for k in keys]
    day = _one_exact(st, keys, vals, "shift_table")
    if day is None:
        return pd.DataFrame(columns=list(identity) + ["clase", "campo", "valor", "unidad", "fuente", "alcance"])

    mass_turn_col = "masa_turno1" if record["turno"] == "TA" else "masa_turno2"
    module_mass = pd.to_numeric(pd.Series([day.get(mass_turn_col)]), errors="coerce").iloc[0]
    pad_day = st.loc[st.pad_id.eq(record["pad_id"]) &
                     pd.to_datetime(st.fecha, errors="coerce").dt.normalize().eq(record["fecha"])].copy()
    keycols = ["pad_id", "campana", "modulo", "fecha"]
    if pad_day.duplicated(keycols).any():
        raise ValueError("shift_table: identidad pad/campaña/módulo/fecha duplicada en denominador")
    denominator_values = pd.to_numeric(pad_day[mass_turn_col], errors="coerce")
    denominator_complete = denominator_values.notna().all()
    pad_shift_tms = denominator_values.sum(min_count=1)
    coefficient = (float(module_mass / pad_shift_tms)
                   if denominator_complete and pd.notna(module_mass) and pd.notna(pad_shift_tms) and pad_shift_tms > 0 else np.nan)
    rows = []
    _add(rows, identity, "Masa", "TMS total pad/turno", "t", pad_shift_tms,
         "shift_table · contexto pad/fecha/turno", "Denominador completo" if denominator_complete else "Denominador incompleto; no se asigna perfil por módulo",
         "Σ TMS turno en shift_table por pad+fecha+turno")
    _add(rows, identity, *FIELD_META["masa_turno_asignada"], module_mass, "shift_table · motor", "Asignación por módulo/turno")
    _add(rows, identity, "Masa", "Coeficiente de asignación", "fracción", coefficient,
         "shift_table · motor", "TMS del módulo dividida por TMS total del pad en fecha/turno",
         "TMS módulo/turno ÷ Σ TMS pad/turno")
    _add(rows, identity, *FIELD_META["masa_total_dia"], day.get("masa_total"), "shift_table · motor", "Asignación por módulo/día; no sumar nuevamente con TMS turno A+B")
    _add(rows, identity, *FIELD_META["masa_turno1"], day.get("masa_turno1"), "shift_table · motor", "Asignación por módulo/fecha")
    _add(rows, identity, *FIELD_META["masa_turno2"], day.get("masa_turno2"), "shift_table · motor", "Asignación por módulo/fecha")

    # Perfil TMH/humedad is keyed only by operational date and shift. A mass
    # weighted profile is scoped to this module by its own shift_table TMS.
    prof = res.get("perfil_turnos")
    if prof is not None and not prof.empty and {"fecha", "turno"}.issubset(prof.columns):
        p = prof.copy()
        p["fecha"] = pd.to_datetime(p["fecha"], errors="coerce").dt.normalize()
        p["turno_norm"] = p.turno.astype(str).str.strip().str.upper().str[-1]
        target = "A" if record["turno"] == "TA" else "B"
        p = p.loc[p.fecha.eq(record["fecha"]) & p.turno_norm.eq(target)]
        if 'pad_id' in p:
            p=p.loc[p.pad_id.eq(record['pad_id'])]
        competing=st.loc[pd.to_datetime(st.fecha).dt.normalize().eq(record['fecha']) &
                         pd.to_numeric(st[mass_turn_col],errors='coerce').gt(0),'pad_id'].nunique()
        wet_route_known='pad_id' in prof.columns or competing<=1
        for field in ("tmh", "humedad"):
            if field in p:
                numeric = pd.to_numeric(p[field], errors="coerce")
                weights = pd.to_numeric(p.get("tmh", pd.Series(1., index=p.index)), errors="coerce")
                weights = weights.where(numeric.notna(), 0).clip(lower=0)
                value = (numeric.fillna(0).mul(weights).sum() / weights.sum()) if weights.sum() else np.nan
                if field == "tmh":
                    value=numeric.sum(min_count=1) if numeric.notna().all() else np.nan
                    if not wet_route_known:
                        value=np.nan
                    elif pd.notna(value) and value==0 and module_mass==0 and pad_shift_tms==0:
                        value=0.
                    else:
                        value *= coefficient if pd.notna(coefficient) else np.nan
                    label = "TMH perfil turno asignada al módulo"
                    formula = "TMH perfil global fecha/turno × coeficiente de asignación"
                else:
                    label = FIELD_META[field][1]
                    formula = "Atributo perfil global de fecha/turno; no se escala"
                _add(rows, identity, FIELD_META[field][0], label, FIELD_META[field][2], value,
                     "perfil_turnos · global fecha/turno", "Estimado para el módulo por coeficiente TMS; no medido por módulo", formula)

    q = _one_exact(calidad, ["fecha", "turno"], [record["fecha"], "A" if record["turno"] == "TA" else "B"], "calidad turno")
    if q is not None:
        for src, field in CALIDAD.items():
            if field not in FIELD_META:
                continue
            value = q.get(field)
            # calidad_turno already normalizes origins to 0..100; 0.5 is 0.5%, not 50%.
            _add(rows, identity, *FIELD_META[field], value, f"calidad_turno · {src}", "Perfil del turno asignado al módulo; no es ensayo exclusivo del módulo",
                 "Valor real reportado a pad/fecha/turno; la masa del módulo se pondera con su TMS asignada")

    mov_metrics, mov_scope = _movcam_pool(raw_mov_cam, record)
    for category, field, value, unit, formula, nrows in mov_metrics:
        _add(rows, identity, category, field, unit, value,
             "mov_cam · POND · CH01 Mina+Stock (Mina/Stock con Fase conocida)",
             f"Atribución estimada al módulo mediante coeficiente TMS; {mov_scope} ({nrows} movimientos válidos)",
             f"{formula}; módulo = perfil turno aplicado con coeficiente {coefficient:.6g}" if pd.notna(coefficient) else formula)

    # Official ACF/CSR/etc can be included only when source rows expose the
    # complete key. Do not fabricate keys or use mov_cam as a module source.
    official_keys = ["caso_id", "pad_id", "campana", "parcela", "modulo", "fecha", "turno"]
    official = _one_exact(official_profile, official_keys,
                          [record[k] for k in official_keys], "informe oficial")
    if official is not None:
        for field in official.index:
            if field in official_keys or field in {"parcela", "fuente"}:
                continue
            value = official[field]
            if pd.isna(value):
                continue
            unit = ""; category = "Atributo reporte oficial"
            if field.upper().startswith(("ACF", "CSR", "CUOXI", "CUINS")):
                unit = "%"
            _add(rows, identity, category, field, unit, value,
                 f"informe oficial · {official.get('fuente', 'fila exacta')}",
                 "Observado en la fuente oficial con identidad completa")
    return pd.DataFrame(rows)


def report_csv(frame):
    """CSV proposal preserving long-row provenance and identity columns."""
    return frame.to_csv(index=False, encoding="utf-8-sig")


def consolidate_module_profile(res, record, calidad=None):
    """TMS-weight report chemistry across the selected module's own shifts.

    This mirrors informe_modulos.preparar_modulos_desde_resultado: each
    Fecha/Turno profile is weighted by that exact module's assigned TMS. The
    campaign and module filter is applied before any weights or joins, so a
    repeated module number in another campaign/pad cannot contribute.
    """
    if record is None:
        return pd.DataFrame()
    identity = {k: record[k] for k in ("caso_id", "pad_id", "campana", "parcela", "modulo")}
    st = res.get("shift_table")
    if st is None or st.empty or calidad is None or calidad.empty:
        return pd.DataFrame()
    module = st.loc[
        st.pad_id.eq(record["pad_id"]) & st.campana.eq(record["campana"])
        & st.modulo.eq(record["modulo"])
    ].copy()
    if module.empty:
        return pd.DataFrame()
    module["fecha"] = pd.to_datetime(module.fecha, errors="coerce").dt.normalize()
    q = calidad.copy()
    q["fecha"] = pd.to_datetime(q.fecha, errors="coerce").dt.normalize()
    q["turno"] = q.turno.astype(str).str.strip().str.upper().str[-1]
    parts = []
    for turno, col in (("A", "masa_turno1"), ("B", "masa_turno2")):
        piece = module[["fecha", col]].rename(columns={col: "peso_tms"})
        piece["turno"] = turno
        parts.append(piece)
    weights = pd.concat(parts, ignore_index=True)
    weights["peso_tms"] = pd.to_numeric(weights.peso_tms, errors="coerce").clip(lower=0)
    merged = weights.merge(q, on=["fecha", "turno"], how="left", validate="many_to_one")
    rows = []
    coverage = []
    for _, field in CALIDAD.items():
        if field not in merged:
            continue
        val = pd.to_numeric(merged[field], errors="coerce")
        w = merged.peso_tms.where(val.notna(), 0.0)
        denom = w.sum(min_count=1)
        out = float((val.fillna(0.0) * w).sum() / denom) if pd.notna(denom) and denom > 0 else np.nan
        meta = FIELD_META.get(field)
        if meta:
            _add(rows, {**identity, "fecha_inicio": module.fecha.min(), "fecha_fin": module.fecha.max(), "turno": "A+B ponderado"},
                 meta[0], meta[1], meta[2], out,
                 "calidad_turno · ponderado por TMS módulo/turno",
                 "Perfil de turno ponderado por TMS asignada al módulo; no es ensayo exclusivo")
        if field == "solubilidad":
            covered = w.sum(min_count=1)
            total = pd.to_numeric(merged.peso_tms, errors="coerce").sum(min_count=1)
            coverage.append(float(covered / total) if pd.notna(total) and total > 0 else np.nan)
    if coverage:
        _add(rows, {**identity, "fecha_inicio": module.fecha.min(), "fecha_fin": module.fecha.max(), "turno": "A+B ponderado"},
             "Cobertura", "Cobertura de calidad", "%", coverage[0] * 100,
             "calidad_turno · solubilidad disponible ponderada por TMS",
             "Fracción de TMS del módulo con perfil de solubilidad")
    return pd.DataFrame(rows)


def render_detail(frame, record, *, movement_frame=None, movement_truncated=False):
    """Render reconstructed record first; mov_cam is optional secondary context."""
    if record is None:
        return html.Div("Fila no disponible para la selección actual.", className="reconstdialog")
    header = html.Div([
        html.H3(f"Caso {record['caso_id']} · Pad {record['pad_id']} · Campaña {record['campana']} · Parcela {record['parcela']} · Módulo {record['modulo']}"),
        html.P(f"Fecha {record['fecha']:%d-%m-%Y} · Turno {record['turno']}"),
        html.P('Masas del registro seleccionado y atributos de su perfil de turno. Los valores asignados no son ensayos independientes del modulo.'),
    ])
    if frame is None or frame.empty:
        body = html.P("Sin atributos reconstruidos para esta clave.")
    else:
        body = dash_table.DataTable(
        data=_records(frame),
            columns=[{"name": c, "id": c} for c in ['clase','campo','valor','unidad','fuente']],
            id='reconstitucion-registro-reconstituido',
            page_action="native", page_size=20, sort_action="native",
            style_table={"overflowX": "auto", "maxHeight": "48vh", "overflowY": "auto"},
            style_cell={'textAlign':'left','whiteSpace':'normal','height':'auto','minWidth':'85px','maxWidth':'340px','padding':'9px'},
        )
    children = [header, body]
    if movement_frame is not None:
        records = _records(movement_frame)
        children.append(html.Details([
            html.Summary("Contexto secundario: movimientos del turno (sin atribución a módulo)"),
            html.P("mov_cam solo identifica fecha, turno y destino; estas filas no son movimientos comprobados de este módulo."),
            dash_table.DataTable(data=records,
                id='reconstitucion-movimientos-tabla',
                columns=[{"name": c, "id": c} for c in movement_frame.columns],
                page_action="native", page_size=20, sort_action="native",
                style_table={"overflowX": "auto", "maxHeight": "40vh", "overflowY": "auto"}),
            html.P("Se muestran las primeras 2000 filas." if movement_truncated else ""),
        ]))
    style={'position':'fixed','zIndex':1100,'inset':'5vh 5vw auto 5vw','maxHeight':'90vh',
           'overflowY':'auto','background':'white','border':'1px solid #ddd','borderRadius':'10px',
           'boxShadow':'0 10px 35px #0003','padding':'20px'}
    return html.Div([html.Div(children,style=style),
        html.Div(style={'position':'fixed','zIndex':1099,'inset':0,'background':'#1118'})],
                    id='reconstitucion-tabla-detalle',style={'position':'fixed','inset':0,'zIndex':1099},role="dialog",
                    **{"aria-modal": "true", "aria-label": "Detalle reconstituido"})


