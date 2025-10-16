# importar_datos_filtrados.py
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
import numpy as np
from sqlalchemy import text
from db_connection import get_engine


dash.register_page(__name__, path="/importar_datos_filtrados", name="Importar datos filtrados")


layout = html.Div([
    html.H4("Carga de datos planta (datos_filtrados)"),
    dcc.Upload(
        id='upload-datos-filtrados',
        children=html.Div([
                html.I(className="bi bi-file-earmark-arrow-up fs-1 text-primary"),  # ícono Bootstrap
                html.H5("Subir archivo Excel", className="mt-2 mb-1 fw-semibold"),
                html.P(
                    "Arrastra o selecciona un archivo .xlsx con hoja ",
                ),
                html.H5("'Datos filtrados'", className="mt-2 mb-1 fw-semibold"),
            ]),
            className=(
                "border-dashed border-primary text-center "
                "py-4 rounded-3 bg-light-subtle"
            ),
            style={
                "cursor": "pointer",
                "transition": "all 0.25s ease-in-out",
                "border":"1px dashed #aaa"
            },
        multiple=False
    ),
    html.Div(id='status-datos-filtrados', style={'marginTop': 20})
])


def register_callbacks(app):
    @app.callback(
        Output('status-datos-filtrados', 'children'),
        Input('upload-datos-filtrados', 'contents'),
        State('upload-datos-filtrados', 'filename')
    )
    def procesar_datos_filtrados(contenido, nombre_archivo):
        import traceback
        if contenido is None:
            return "No se ha cargado ningún archivo."


        try:
            # Decodificar Excel
            content_type, content_string = contenido.split(',', 1)
            decoded = base64.b64decode(content_string)
            excel_data = io.BytesIO(decoded)


            # Leer hoja y normalizar columnas
            df = pd.read_excel(excel_data, sheet_name="Datos filtrados", header=0, skiprows=[1], usecols="A:AB")
            df.columns = [str(col).strip().replace(" ", "_").replace(".", "_").lower() for col in df.columns]


            # Convertir numéricos
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass


            # Convertir fechas
            for fecha_col in ['fecha_inicial', 'fecha_final']:
                if fecha_col in df.columns:
                    df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')


            # Construir fecha_turno
            if 'fecha_inicial' not in df.columns:
                df['turno'] = None
                df['fecha_turno'] = None
            else:
                df['fecha_inicial'] = pd.to_datetime(df['fecha_inicial'], errors='coerce')

                horas = df['fecha_inicial'].dt.hour

                # Turno: A = 08:00–19:59, TB = 20:00–07:59
                df['turno'] = np.where(horas.between(8, 19, inclusive='both'), 'A', 'B')

                # Fecha del turno:
                #  - Para 00:00–07:59 (madrugada), pertenece al turno iniciado la noche anterior → restar 1 día
                df['fecha_turno'] = df['fecha_inicial'].dt.floor('D')
                mask_madrugada = horas < 8
                df.loc[mask_madrugada, 'fecha_turno'] = df.loc[mask_madrugada, 'fecha_turno'] - pd.Timedelta(days=1)

                # Tipos consistentes con SQL (date/nvarchar/texto)
                df['fecha_turno'] = pd.to_datetime(df['fecha_turno'], errors='coerce').dt.date
                df['turno'] = df['turno'].astype('string')


            engine = get_engine()


            # Obtener esquema de tabla para convertir tipos y detectar columnas IDENTITY
            schema_query = """
            SELECT COLUMN_NAME, DATA_TYPE, COLUMNPROPERTY(object_id(TABLE_SCHEMA+'.'+TABLE_NAME), COLUMN_NAME, 'IsIdentity') AS IsIdentity
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'inventar_SpcHidr' AND TABLE_NAME = 'datos_filtrados'
            """
            df_schema = pd.read_sql(schema_query, engine)
            tipos_db = dict(zip(df_schema['COLUMN_NAME'], df_schema['DATA_TYPE']))
            tipos_lc = {k.strip().lower(): v for k, v in tipos_db.items()}

            identity_cols_db = [row['COLUMN_NAME'] for _, row in df_schema.iterrows() if row['IsIdentity'] == 1]
            identity_cols_lc = [c.strip().lower() for c in identity_cols_db]

            for col_lc, sql_type in tipos_lc.items():
                if col_lc not in df.columns:
                    continue
                if sql_type in ('int', 'bigint', 'smallint', 'tinyint'):
                    df[col_lc] = pd.to_numeric(df[col_lc], errors='coerce').fillna(0).astype('Int64').astype(int)
                elif sql_type in ('decimal', 'numeric', 'float', 'real'):
                    df[col_lc] = (
                        df[col_lc].astype(str)
                                .str.replace(',', '.', regex=False)
                                .replace({'None': None, 'nan': None, '': None})
                    )
                    df[col_lc] = pd.to_numeric(df[col_lc], errors='coerce')
                elif sql_type in ('datetime', 'date', 'smalldatetime', 'datetime2'):
                    df[col_lc] = pd.to_datetime(df[col_lc], errors='coerce')
                else:
                    df[col_lc] = df[col_lc].astype(str).fillna('')


            # Detectar registros existentes por fecha_inicial
            if 'fecha_inicial' in df.columns:
                df['fecha_inicial']  = pd.to_datetime(df['fecha_inicial'],errors='coerce')

                fechas_min = df['fecha_inicial'].min()
                fechas_max = df['fecha_inicial'].max()

                if pd.notna(fechas_min):
                    fechas_min = fechas_min.strftime('%Y-%m-%d')
                if pd.notna(fechas_max):
                    fechas_max = fechas_max.strftime('%Y-%m-%d')
            else:
                fechas_min = fechas_max = None

            if fechas_min and fechas_max:
                query_exist = text("""
                    SELECT * FROM inventar_SpcHidr.datos_filtrados
                    WHERE fecha_inicial BETWEEN :fecha_min AND :fecha_max
                """)
                df_existente = pd.read_sql(query_exist, con=engine, params={"fecha_min": fechas_min, "fecha_max": fechas_max})
                df_existente.columns = [str(c).strip().replace(" ", "_").replace(".", "_").lower() for c in df_existente.columns]
                # Convertir fechas existentes
                if 'fecha_inicial' in df_existente.columns:
                    df_existente['fecha_inicial'] = pd.to_datetime(df_existente['fecha_inicial'], errors='coerce')
            else:
                df_existente = pd.DataFrame()

            cols_candidato = ['fecha_inicial'] + [
                c for c in df.columns
                if c not in ['fecha_inicial', 'fecha_final', 'fecha_turno']
            ]

            # 2) Usar solo columnas que existan en AMBOS dataframes (intersección)
            if not df_existente.empty:
                key_cols_common = [c for c in cols_candidato if c in df.columns and c in df_existente.columns]
            else:
                key_cols_common = [c for c in cols_candidato if c in df.columns]

            # 3) Diagnóstico opcional (te ayuda a ver por qué fallaba antes)
            if not df_existente.empty:
                faltantes = [c for c in cols_candidato if c in df.columns and c not in df_existente.columns]
                if faltantes:
                    print("[DEBUG] Columnas del archivo que no existen en SQL y se excluyen de la clave:", faltantes)

            def clave_compuesta(df_, cols):
                # Convertir a str, rellenar NaN con '', luego concatenar con '||'
                return df_[cols].astype(str).fillna('').agg('||'.join, axis=1)

            # 4) Construir claves y filtrar solo lo nuevo
            if not df_existente.empty and key_cols_common:
                df['__key__'] = clave_compuesta(df, key_cols_common)
                df_existente['__key__'] = clave_compuesta(df_existente, key_cols_common)
                set_existentes = set(df_existente['__key__'].unique())
                df_nuevos = df[~df['__key__'].isin(set_existentes)].drop(columns='__key__')
            else:
                # Si no hay existentes para el rango o no hay intersección válida, insertar todo
                df_nuevos = df.copy()
            total_archivo = len(df)
            nuevos = len(df_nuevos)




            # Insertar por chunks ignorando columnas IDENTITY
            def insert_chunks(df_src, table_name, schema_name, rows_per_chunk=20, skip_id_lc=[]):
                cols_to_insert = [c for c in df_src.columns if c in tipos_lc.keys() and c not in skip_id_lc]
                if not cols_to_insert:
                    return
                df_to_insert = df_src[cols_to_insert].copy()
                for i in range(0, len(df_to_insert), rows_per_chunk):
                    chunk = df_to_insert.iloc[i:i+rows_per_chunk]
                    chunk.to_sql(
                        name=table_name,
                        con=engine,
                        schema=schema_name,
                        if_exists='append',
                        index=False
                    )


            if nuevos > 0:
                insert_chunks(
                    df_nuevos,
                    table_name="datos_filtrados",
                    schema_name="inventar_SpcHidr",
                    rows_per_chunk=20,
                    skip_id_lc=identity_cols_lc
                )


            return f"Archivo '{nombre_archivo}' procesado correctamente. Registros en archivo: {total_archivo}. Nuevos insertados: {nuevos}."


        except Exception as e:
            traceback.print_exc()
            return f"Error procesando el archivo: {str(e)}"





