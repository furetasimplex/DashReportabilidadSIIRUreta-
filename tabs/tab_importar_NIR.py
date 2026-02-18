import dash
from dash import html, dcc, Input, Output, State
import base64
import io
import pandas as pd
import pdfplumber
from sqlalchemy import text
from db_connection import get_engine

# =========================
# Destino SQL (mismo patrón que Recuperaciones)
# =========================
SCHEMA_NAME = "inventar_SpcHidr"
TABLE_NAME = "NIR"
FULL_TABLE_NAME = f"[{SCHEMA_NAME}].[{TABLE_NAME}]"

layout = html.Div([
    html.H4("Carga NIR desde PDF (Tabla FY/DIA/TORRE/TURNO/MUESTRA/CaolBeta)"),
    dcc.Upload(
        id='upload-nir-pdf',
        children=html.Div([
            html.I(className="bi bi-file-earmark-pdf fs-1 text-danger"),
            html.H5("Subir PDF NIR (BHP)", className="mt-2 mb-1 fw-semibold"),
            html.P("Se extrae la tabla del PDF y se carga a NIR usando SQL (DELETE por clave + INSERT masivo)."),
        ]),
        className="border-dashed border-danger text-center py-4 rounded-3 bg-light-subtle",
        style={"cursor": "pointer", "transition": "all 0.25s ease-in-out", "border": "1px dashed #aaa"},
        multiple=False
    ),
    html.Div(id='status-nir-pdf', style={'marginTop': 20})
])

def _parse_pdf_table(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Extrae la tabla del PDF.
    Estrategia:
    - Intentar extract_table() (estructura tabular)
    - Fallback: parseo por texto si viene linealizado
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[0]

        table = page.extract_table()
        if table and len(table) >= 2:
            headers = [h.strip() if h else "" for h in table[0]]
            rows = table[1:]
            df = pd.DataFrame(rows, columns=headers)
        else:
            text_content = page.extract_text() or ""
            lines = [ln.strip() for ln in text_content.splitlines() if ln.strip()]

            start_idx = None
            for i, ln in enumerate(lines):
                if ln.replace("  ", " ").strip() == "FY DIA TORRE TURNO MUESTRA CaolBeta":
                    start_idx = i + 1
                    break
            if start_idx is None:
                raise ValueError("No se encontró el encabezado de tabla en el PDF.")

            data = []
            for ln in lines[start_idx:]:
                parts = ln.split()
                if len(parts) < 6:
                    continue

                fy, dia, torre, turno = parts[0], parts[1], parts[2], parts[3]
                caolbeta = parts[-1]
                muestra = " ".join(parts[4:-1])
                data.append([fy, dia, torre, turno, muestra, caolbeta])

            df = pd.DataFrame(data, columns=["FY", "DIA", "TORRE", "TURNO", "MUESTRA", "CaolBeta"])

    # Normalización
    df["DIA"] = pd.to_datetime(df["DIA"], format="%d-%b-%Y", errors="coerce").dt.date
    df["CaolBeta"] = pd.to_numeric(df["CaolBeta"], errors="coerce")

    df = df.dropna(subset=["FY", "DIA", "TORRE", "TURNO", "MUESTRA", "CaolBeta"]).copy()

    df = df.rename(columns={
        "FY": "fy",
        "DIA": "dia",
        "TORRE": "torre",
        "TURNO": "turno",
        "MUESTRA": "muestra",
        "CaolBeta": "caolbeta",
    })

    for c in ["fy", "torre", "turno", "muestra"]:
        df[c] = df[c].astype(str).str.strip()

    return df

def eliminar_y_cargar_nir(df: pd.DataFrame, engine) -> int:
    """
    Patrón consistente con Tabs existentes:
    1) DELETE por clave natural (fy, dia, torre, turno, muestra)
    2) INSERT masivo con to_sql(append) usando method="multi"

    Nota: id y fecha_carga se gestionan en SQL Server (IDENTITY / DEFAULT).
    """
    if df is None or df.empty:
        return 0

    # Insertar solo columnas existentes en la tabla
    df_to_insert = df[["fy", "dia", "torre", "turno", "muestra", "caolbeta"]].copy()

    # Claves únicas (anti-duplicados)
    df_keys = df_to_insert[["fy", "dia", "torre", "turno", "muestra"]].drop_duplicates()

    delete_sql = text(f"""
        DELETE FROM {FULL_TABLE_NAME}
        WHERE [fy] = :fy
          AND CAST([dia] AS DATE) = :dia
          AND [torre] = :torre
          AND [turno] = :turno
          AND [muestra] = :muestra
    """)

    with engine.begin() as conn:
        # 1) DELETE por cada clave única
        for _, k in df_keys.iterrows():
            conn.execute(delete_sql, {
                "fy": k["fy"],
                "dia": pd.to_datetime(k["dia"]).strftime("%Y-%m-%d"),
                "torre": k["torre"],
                "turno": k["turno"],
                "muestra": k["muestra"],
            })

        # 2) INSERT masivo (mismo patrón que Recuperaciones)
        df_to_insert.to_sql(
            TABLE_NAME,
            con=conn,
            schema=SCHEMA_NAME,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=50
        )

    return len(df_to_insert)

def register_callbacks(app):
    @app.callback(
        Output('status-nir-pdf', 'children'),
        Input('upload-nir-pdf', 'contents'),
        State('upload-nir-pdf', 'filename')
    )
    def procesar_nir_pdf(contenido, nombre_archivo):
        if contenido is None:
            return "Esperando archivo..."

        try:
            _, content_string = contenido.split(',')
            pdf_bytes = base64.b64decode(content_string)

            df = _parse_pdf_table(pdf_bytes)

            if df is None or df.empty:
                return html.Div("❌ No se encontraron filas válidas en el PDF.", style={'color': 'red'})

            engine = get_engine()
            n = eliminar_y_cargar_nir(df, engine)

            return html.Div([
                html.Div(f"✅ Éxito: {n} registros cargados/actualizados en {SCHEMA_NAME}.{TABLE_NAME}.",
                         style={'color': 'green'}),
                html.Div("ℹ️ Se aplica DELETE por clave natural + INSERT masivo (to_sql). Re-subidas no duplican.",
                         style={'fontSize': '0.9em', 'color': 'gray'})
            ])

        except Exception as e:
            return html.Div([
                html.H5("❌ Error en la carga NIR (PDF)"),
                html.P(f"Archivo: {nombre_archivo}"),
                html.P(f"Detalle: {str(e)}")
            ], style={'color': 'red'})
