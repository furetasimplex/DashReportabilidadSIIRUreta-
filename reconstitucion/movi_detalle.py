"""Read-only movement detail sourced from the confirmed SIIR mov_cam table."""
import pandas as pd
from datetime import date, datetime
from decimal import Decimal
import math
from sqlalchemy import text
from dash import dash_table, html

SCHEMA = "inventar_SpcHidr.inventar_SpcHidr"
TABLE = "mov_cam"
SOURCE_LABEL = "Movimientos de camiones · mov_cam"
DESTINO = "CH01"
MAX_ROWS = 2000
FETCH_ROWS = MAX_ROWS + 1

# This fixed-source detail intentionally includes every real DB column.

def load_movimientos(engine, *, fecha, turno, destino=DESTINO):
    """Fetch original rows for one operational date/shift and CH01.

    echa and 	urno come from the selected itinerary item. mov_cam has no
    module, pad, campaign, or individual event-time key, so no such attribution
    or inferred timestamp is added here.
    """
    fecha = pd.Timestamp(fecha).normalize()
    turno = str(turno).strip().upper()
    if turno not in {"TA", "TB"}:
        raise ValueError("turno debe ser TA o TB")
    sql = f"""SELECT TOP (:limite) *
FROM {SCHEMA}.[{TABLE}]
WHERE [Fecha] = :fecha AND [Turno] = :turno AND [Destino] = :destino
ORDER BY [mov_id]"""
    df = pd.read_sql(text(sql), engine, params={
        "limite": FETCH_ROWS,
        "fecha": fecha.date(),
        "turno": turno,
        "destino": destino,
    })
    truncated = len(df) > MAX_ROWS
    return df.iloc[:MAX_ROWS].copy(), truncated


def _json_value(value):
    """Convert pandas/numpy scalars, timestamps and NaN to JSON-safe values."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _records(frame):
    return [{key: _json_value(value) for key, value in row.items()}
            for row in frame.to_dict(orient="records")]


def popup_movimientos(frame, *, caso, modulo, fecha, turno, truncated=False, error=None):
    """Render paginated, horizontal-scroll popup for full mov_cam rows."""
    header = html.Div([
        html.H3(SOURCE_LABEL),
        html.P(f"Caso {caso} · módulo {modulo} · {pd.Timestamp(fecha):%d-%m-%Y} · turno {turno}"),
        html.P("Registros del turno; la fuente no identifica módulo ni hora individual."),
    ])
    if error:
        body=html.P(error)
    elif frame is None or frame.empty:
        body = html.P("No hay registros mov_cam para esta fecha, turno y destino CH01.")
    else:
        body = dash_table.DataTable(
            id='reconstitucion-movimientos-tabla',
            data=_records(frame),
            columns=[{"name": c, "id": c} for c in frame.columns],
            page_action="native", page_size=20,
            sort_action="native", filter_action="native",
            style_table={"overflowX": "auto", "maxHeight": "55vh", "overflowY": "auto"},
        )
    children = [header, body]
    if truncated:
        children.append(html.P(f"Se muestran las primeras {MAX_ROWS} filas."))
    style={'position':'fixed','zIndex':1100,'inset':'5vh 5vw auto 5vw','maxHeight':'90vh',
           'overflowY':'auto','background':'white','border':'1px solid #ddd',
           'borderRadius':'10px','boxShadow':'0 10px 35px #0003','padding':'20px'}
    return html.Div([html.Div(children,style=style),
        html.Div(style={'position':'fixed','zIndex':1099,'inset':0,'background':'#1118'})],
        id='reconstitucion-tabla-detalle',style={'position':'fixed','inset':0,'zIndex':1099},
        role='dialog',**{"aria-modal":"true","aria-label":SOURCE_LABEL})
