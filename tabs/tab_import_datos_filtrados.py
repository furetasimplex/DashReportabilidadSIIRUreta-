
import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
from sqlalchemy import create_engine
from db_connection import get_engine
from sqlalchemy import text

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
        if contenido is None:
            return "No se ha cargado ningún archivo."

        try:
            content_type, content_string = contenido.split(',')
            decoded = base64.b64decode(content_string)
            excel_data = io.BytesIO(decoded)

            # Leer hoja desde fila 3 (header en fila 1, omite fila 2)
            df = pd.read_excel(excel_data, sheet_name="Datos filtrados", header=0, skiprows=[1], usecols="A:AB")

            df.columns = [str(col).strip().replace(" ", "_").replace(".", "_").lower() for col in df.columns]
            print(f'NOMBRES COLUMNAS {df.columns}')
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
            for fecha_col in ['fecha_inicial', 'fecha_final']:
                if fecha_col in df.columns:
                    df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
             # Calcular campo fecha_turno
            if 'fecha_inicial' in df.columns:
                df['fecha_turno'] = df['fecha_inicial'].apply(
                    lambda x: x.date() if pd.notnull(x) and x.time() >= pd.to_datetime("08:00:00").time()
                    else (x - pd.Timedelta(days=1)).date() if pd.notnull(x) else pd.NaT
                )
            # Eliminar registros existentes por fecha_inicial
            #engine = get_engine()
            #with engine.connect() as conn:
                #fechas_existentes = df['fecha_inicial'].dropna().unique()
                #for f in fechas_existentes:
                #    stmt = text("""
                #        DELETE FROM datos_filtrados
                #        WHERE fecha_inicial = :fecha_inicial 
                #    """)
                #    conn.execute(stmt, {"fecha_inicial": f})
            engine = get_engine()
            with engine.connect() as conn:
                transaction = conn.begin() # Iniciar una transacción
                try:
                    fechas_a_borrar = df['fecha_inicial'].dropna().unique().tolist()
                    
                    # Es más eficiente borrar todo en una sola consulta
                    if fechas_a_borrar:
                        stmt = text("DELETE FROM datos_filtrados WHERE fecha_inicial IN :fechas")
                        conn.execute(stmt, {"fechas": tuple(fechas_a_borrar)})
                        
                    # 2. Añadir los nuevos registros sin borrar el resto de la tabla
                    df.to_sql("datos_filtrados", con=conn, if_exists="append", index=False)
                    
                    transaction.commit() # Confirmar los cambios
                    return f"Archivo '{nombre_archivo}' cargado. Se actualizaron los registros correspondientes."
                except Exception as e:
                    transaction.rollback() # Revertir cambios si hay un error
                    return f"Error en la transacción: {str(e)}"

            #df.to_sql("datos_filtrados", con=engine, if_exists="replace", index=False)
            return f"Archivo '{nombre_archivo}' cargado correctamente en tabla 'datos_filtrados'."
        except Exception as e:
            return f"Error: {str(e)}"
