# importar_mov_cam.py
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
        import traceback

        if contenido is None:
            return "No se ha cargado ningún archivo."

        try:
            print(">>> Procesando archivo:", nombre_archivo)

            if ',' not in contenido:
                return "Error: el archivo subido no tiene el formato esperado (faltan datos base64)."

            # Decodificar contenido
            content_type, content_string = contenido.split(',', 1)
            decoded = base64.b64decode(content_string)
            excel_data = io.BytesIO(decoded)

            # Leer Excel
            xls = pd.ExcelFile(excel_data)
            if "Base_Datos" not in xls.sheet_names:
                return "Error: el archivo no contiene la hoja 'Base_Datos'."
            df = pd.read_excel(xls, sheet_name="Base_Datos")
            df.columns = df.columns.str.strip()

            print("Columnas iniciales:", df.columns.tolist())

            # --- Filtrado básico ---
            if "Año" not in df.columns:
                return "Error: falta la columna 'Año'."

            df = df[df["Año"].notna()]
            df = df[df["Año"] < 2030]

            # Construcción de Fecha
            for col in ["Año", "Mes", "Dia"]:
                if col not in df.columns:
                    return f"Error: falta la columna '{col}' en el Excel."

            df["Año"] = df["Año"].fillna(0).astype(int).astype(str).str.zfill(4)
            df["Mes"] = df["Mes"].fillna(0).astype(int).astype(str).str.zfill(2)
            df["Dia"] = df["Dia"].fillna(0).astype(int).astype(str).str.zfill(2)
            df["Fecha_str"] = df["Año"] + "-" + df["Mes"] + "-" + df["Dia"]
            df["Fecha"] = pd.to_datetime(df["Fecha_str"], errors="coerce")

            df = df[df["Fecha"].notna()]
            df = df[df["Fecha"].dt.year < 2030]

            # --- Reordenar columnas ---
            columnas = ["Fecha"] + [c for c in df.columns if c not in ["Año", "Mes", "Dia", "Fecha", "Fecha_str"]]
            df = df[columnas].copy()

            # --- Claves requeridas ---
            columnas_clave = ["Fecha", "Turno", "Origen", "Solido", "Ton", "Poligono_CIO"]
            for c in columnas_clave:
                if c not in df.columns:
                    return f"Error: falta la columna clave '{c}' en el Excel."

            # Rango de fechas
            fecha_min = df["Fecha"].min().strftime('%Y-%m-%d')
            fecha_max = df["Fecha"].max().strftime('%Y-%m-%d')

            engine = get_engine()

            # --- Obtener esquema de tabla para validar tipos ---
            schema_query = """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'inventar_SpcHidr' AND TABLE_NAME = 'mov_cam'
            """
            df_schema = pd.read_sql(schema_query, engine)
            tipos = dict(zip(df_schema['COLUMN_NAME'], df_schema['DATA_TYPE']))
            print(tipos)

            # --- Convertir columnas según tipo ---
            for col, sql_type in tipos.items():
                if col not in df.columns:
                    continue
                if sql_type in ('int', 'bigint', 'smallint', 'tinyint'):
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                elif sql_type in ('decimal', 'numeric', 'float', 'real'):
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                elif sql_type in ('datetime', 'date', 'smalldatetime'):
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                else:
                    df[col] = df[col].astype(str).fillna('')

            # --- Detectar registros nuevos ---
            query_exist = text("""
                SELECT Fecha, Turno, Origen, Solido, Ton, Poligono_CIO
                FROM inventar_SpcHidr.mov_cam
                WHERE Fecha BETWEEN :fecha_min AND :fecha_max
            """)
            df_existente = pd.read_sql(query_exist, con=engine, params={"fecha_min": fecha_min, "fecha_max": fecha_max})
            df_existente["Fecha"] = pd.to_datetime(df_existente["Fecha"], errors="coerce")

            def clave_compuesta(df_):
                return (
                    df_["Fecha"].dt.strftime("%Y-%m-%d") + "||" +
                    df_["Turno"].astype(str).fillna("") + "||" +
                    df_["Origen"].astype(str).fillna("") + "||" +
                    df_["Solido"].astype(str).fillna("") + "||" +
                    df_["Ton"].astype(str).fillna("") + "||" +
                    df_["Poligono_CIO"].astype(str).fillna("")
                )

            if not df_existente.empty:
                df["__key__"] = clave_compuesta(df)
                df_existente["__key__"] = clave_compuesta(df_existente)
                set_existentes = set(df_existente["__key__"].unique())
                df_nuevos = df[~df["__key__"].isin(set_existentes)].drop(columns="__key__")
            else:
                df_nuevos = df.copy()

            total_archivo = len(df)
            nuevos = len(df_nuevos)

            # --- Función de inserción por chunks ---
            def insert_chunks(df, table_name, schema_name, rows_per_chunk=20,skip_id=""):
                cols_to_insert = [c for c in df.columns if c in tipos.keys() and c!= skip_id]
                df_to_insert = df[cols_to_insert]
                for i in range(0, len(df_to_insert), rows_per_chunk):
                    chunk = df_to_insert.iloc[i:i+rows_per_chunk]
                    chunk.to_sql(
                        name=table_name,
                        con=engine,
                        schema=schema_name,
                        if_exists='append',
                        index=False
                    )
                    #print(f"Insertadas filas {i} a {i + len(chunk)-1}")

            # --- Insertar registros nuevos ---
            if nuevos > 0:
                insert_chunks(df_nuevos, table_name="mov_cam", schema_name="inventar_SpcHidr", rows_per_chunk=20,skip_id='mov_id')

            return (
                f"Archivo '{nombre_archivo}' procesado correctamente. "
                f"Registros en archivo: {total_archivo}. "
                f"Nuevos insertados: {nuevos}."
            )

        except Exception as e:
            traceback.print_exc()
            return f"Error procesando el archivo: {str(e)}"



