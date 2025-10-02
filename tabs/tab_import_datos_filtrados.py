# importar_datos_filtrados.py
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
from sqlalchemy import text
from db_connection import get_engine


dash.register_page(__name__, path="/importar_datos_filtrados", name="Importar datos filtrados")


layout = html.Div([
    html.H4("Carga de datos planta (datos_filtrados)"),
    dcc.Upload(
        id='upload-datos-filtrados',
        children=html.Div(['Arrastra o selecciona el archivo Excel con hoja Datos filtrados']),
        style={
            'width': '80%',
            'padding': '20px',
            'border': '1px dashed #aaa',
            'textAlign': 'center',
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
            df = pd.read_excel(excel_data, sheet_name="Datos filtrados", header=0, skiprows=[1], usecols="A:AH")
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
            if 'fecha_inicial' in df.columns:
                def calcular_fecha_turno(x):
                    if pd.isna(x):
                        return pd.NaT
                    if isinstance(x, pd.Timestamp):
                        return x if x.time() >= pd.to_datetime("08:00:00").time() else x - pd.Timedelta(days=1)
                    # por si viene como string
                    try:
                        x_ts = pd.to_datetime(x)
                        return x_ts if x_ts.time() >= pd.to_datetime("08:00:00").time() else x_ts - pd.Timedelta(days=1)
                    except:
                        return pd.NaT
                df['fecha_turno'] = df['fecha_inicial'].apply(calcular_fecha_turno)


            engine = get_engine()


            # Obtener esquema de tabla para convertir tipos y detectar columnas IDENTITY
            schema_query = """
            SELECT COLUMN_NAME, DATA_TYPE, COLUMNPROPERTY(object_id(TABLE_SCHEMA+'.'+TABLE_NAME), COLUMN_NAME, 'IsIdentity') AS IsIdentity
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'inventar_SpcHidr' AND TABLE_NAME = 'datos_filtrados'
            """
            df_schema = pd.read_sql(schema_query, engine)
            tipos = dict(zip(df_schema['COLUMN_NAME'], df_schema['DATA_TYPE']))
            identity_cols = [row['COLUMN_NAME'] for idx, row in df_schema.iterrows() if row['IsIdentity'] == 1]


            # Convertir según tipo SQL
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

            fechas_min = df['fecha_inicial'].min().strftime('%Y-%m-%d') if 'fecha_inicial' in df.columns else None
            fechas_max = df['fecha_inicial'].max().strftime('%Y-%m-%d') if 'fecha_inicial' in df.columns else None


            if fechas_min and fechas_max:
                query_exist = text("""
                    SELECT * FROM inventar_SpcHidr.datos_filtrados
                    WHERE fecha_inicial BETWEEN :fecha_min AND :fecha_max
                """)
                df_existente = pd.read_sql(query_exist, con=engine, params={"fecha_min": fechas_min, "fecha_max": fechas_max})
                # Convertir fechas existentes
                if 'fecha_inicial' in df_existente.columns:
                    df_existente['fecha_inicial'] = pd.to_datetime(df_existente['fecha_inicial'], errors='coerce')
            else:
                df_existente = pd.DataFrame()


            # Crear clave compuesta para detectar nuevos registros
            key_cols = ['fecha_inicial'] + [c for c in df.columns if c not in ['fecha_inicial', 'fecha_final', 'fecha_turno']]
            def clave_compuesta(df_):
                return df_[key_cols].astype(str).agg('||'.join, axis=1)
            if not df_existente.empty:
                df['__key__'] = clave_compuesta(df)
                df_existente['__key__'] = clave_compuesta(df_existente)
                set_existentes = set(df_existente['__key__'].unique())
                df_nuevos = df[~df['__key__'].isin(set_existentes)].drop(columns='__key__')
            else:
                df_nuevos = df.copy()


            total_archivo = len(df)
            nuevos = len(df_nuevos)


            # Insertar por chunks ignorando columnas IDENTITY
            def insert_chunks(df, table_name, schema_name, rows_per_chunk=20, skip_id=[]):
                cols_to_insert = [c for c in df.columns if c in tipos.keys() and c not in skip_id]
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


            if nuevos > 0:
                insert_chunks(df_nuevos, table_name="datos_filtrados", schema_name="inventar_SpcHidr", rows_per_chunk=20, skip_id=identity_cols)


            return f"Archivo '{nombre_archivo}' procesado correctamente. Registros en archivo: {total_archivo}. Nuevos insertados: {nuevos}."


        except Exception as e:
            traceback.print_exc()
            return f"Error procesando el archivo: {str(e)}"





