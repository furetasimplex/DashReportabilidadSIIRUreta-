# importar_mov_cam.py (tu página Dash)
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
from sqlalchemy.sql import text
from db_connection import get_engine

dash.register_page(__name__, path="/importar_mov_cam", name="Importar mov_cam")

layout = html.Div([
    html.H4("Carga de datos operacionales de mina (mov_cam)"),
    dcc.Upload(
        id='upload-mov-cam',
        children=html.Div(['Arrastra o selecciona el archivo Excel con hoja Base_Datos']),
        style={
            'width': '80%',
            'padding': '20px',
            'border': '1px dashed #aaa',
            'textAlign': 'center',
        },
        multiple=False
    ),
    html.Div(id='status-mov-cam', style={'marginTop': 20})
])

def register_callbacks(app):
    @app.callback(
        Output('status-mov-cam', 'children'),
        Input('upload-mov-cam', 'contents'),
        State('upload-mov-cam', 'filename')
    )
    def procesar_mov_cam(contenido, nombre_archivo):
        if contenido is None:
            return "No se ha cargado ningún archivo."

        try:
            # --- Leer Excel en memoria ---
            content_type, content_string = contenido.split(',')
            decoded = base64.b64decode(content_string)
            excel_data = io.BytesIO(decoded)

            df = pd.read_excel(excel_data, sheet_name="Base_Datos", header=0)

            # --- Filtrado básico por año y existencia ---
            df = df[df["Año"].notna()]
            df = df[df["Año"] < 2030]

            # --- Construcción segura de Fecha ---
            df["Año"] = df["Año"].fillna(0).astype(int).astype(str).str.zfill(4)
            df["Mes"] = df["Mes"].fillna(0).astype(int).astype(str).str.zfill(2)
            df["Dia"] = df["Dia"].fillna(0).astype(int).astype(str).str.zfill(2)
            df["Fecha_str"] = df["Año"] + "-" + df["Mes"] + "-" + df["Dia"]
            df["Fecha"] = pd.to_datetime(df["Fecha_str"], errors="coerce")

            # Fechas válidas y razonables
            df = df[df["Fecha"].notna()]
            df = df[df["Fecha"].dt.year < 2030]

            # --- Reordenar columnas: Fecha primero ---
            columnas = ["Fecha"] + [c for c in df.columns if c not in ["Año", "Mes", "Dia", "Fecha", "Fecha_str"]]
            df = df[columnas].copy()

            # --- Claves para deduplicación ---
            columnas_clave = ["Fecha", "Turno", "Origen", "Solido", "Ton", "Poligono_CIO"]
            for c in columnas_clave:
                if c not in df.columns:
                    return f"Error: Falta la columna clave requerida '{c}' en el Excel."

            # --- Rango de fechas para traer existentes ---
            fecha_min = df["Fecha"].min().strftime('%Y-%m-%d')
            fecha_max = df["Fecha"].max().strftime('%Y-%m-%d')

            engine = get_engine()

            query = text("""
                SELECT Fecha, Turno, Origen, Solido, Ton, Poligono_CIO
                FROM mov_cam
                WHERE Fecha BETWEEN :fecha_min AND :fecha_max
            """)
            df_existente = pd.read_sql(query, con=engine, params={"fecha_min": fecha_min, "fecha_max": fecha_max})

            # Normalizar tipos (evitar falsos distintos)
            df_existente["Fecha"] = pd.to_datetime(df_existente["Fecha"], errors="coerce")
            df[columnas_clave[1:]] = df[columnas_clave[1:]].apply(lambda s: s.astype(object).where(pd.notnull(s), None))

            # --- Determinar filas nuevas (anti-join) ---
            if df_existente.empty:
                df_nuevos = df.copy()
            else:
                # Para comparar, creamos una clave compuesta como string (robusto y rápido)
                def clave_compuesta(x):
                    return (
                        x["Fecha"].dt.strftime("%Y-%m-%d") + "||" +
                        x["Turno"].astype(str).fillna("") + "||" +
                        x["Origen"].astype(str).fillna("") + "||" +
                        x["Solido"].astype(str).fillna("") + "||" +
                        x["Ton"].astype(str).fillna("") + "||" +
                        x["Poligono_CIO"].astype(str).fillna("")
                    )

                df["__key__"] = clave_compuesta(df)
                df_existente["__key__"] = clave_compuesta(df_existente)

                set_existentes = set(df_existente["__key__"].unique())
                df_nuevos = df[~df["__key__"].isin(set_existentes)].drop(columns="__key__")

            # --- Insertar ---
            total_archivo = len(df)
            nuevos = len(df_nuevos)

            if nuevos > 0:
                # Inserción por lotes; en MSSQL usará fast_executemany (pyodbc) o multi-VALUES (pytds)
                df_nuevos.to_sql(
                    "mov_cam",
                    con=engine,
                    if_exists="append",
                    index=False,
                    method="multi",
                    chunksize=1000
                )

            return (
                f"Archivo '{nombre_archivo}' procesado. "
                f"Registros en archivo: {total_archivo}. "
                f"Nuevos insertados: {nuevos}."
            )

        except Exception as e:
            return f"Error: {str(e)}"
