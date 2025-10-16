import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
from sqlalchemy import create_engine
from db_connection import get_engine
from sqlalchemy import text

layout = html.Div([
    html.H4("Carga de Tonelaje Reclamado por Camiones (Sulfuro)"),
    dcc.Upload(
        id='upload-reclamos-sulfuro',
        children=html.Div([
                html.I(className="bi bi-file-earmark-arrow-up fs-1 text-primary"),  # ícono Bootstrap
                html.H5("Subir archivo Excel", className="mt-2 mb-1 fw-semibold"),
                html.P(
                    "Arrastra o selecciona un archivo .xlsx con hoja ",
                ),
                html.H5("'Reclamo Camiones SULFURO'",className="mt-2 mb-1 fw-semibold")
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
    html.Div(id='status-reclamos-sulfuro', style={'marginTop': 20})
])

def register_callbacks(app):
    @app.callback(
        Output('status-reclamos-sulfuro', 'children'),
        Input('upload-reclamos-sulfuro', 'contents'),
        State('upload-reclamos-sulfuro', 'filename')
    )
    def procesar_reclamos_sulfuro(contenido, nombre_archivo):
        if contenido is None:
            return "Por favor, carga un archivo para comenzar."

        try:
            content_type, content_string = contenido.split(',')
            decoded = base64.b64decode(content_string)

            # --- PASO 1: Leer el Excel de forma flexible ---
            # Quitamos 'usecols' para evitar el error y leemos desde la segunda fila.
            df = pd.read_excel(
                io.BytesIO(decoded),
                sheet_name="Reclamo Camiones SULFURO",
                header=1
            )

        except Exception as e:
            return html.Div([f'Error al leer el archivo. Detalle: {e}'], style={'color': 'red'})
        
        try:
            # --- PASO 2: Arreglar la columna de fecha ---
            # La primera columna no tendrá nombre (se llamará 'Unnamed: 0') debido a la celda combinada.
            # Le asignamos el nombre correcto 'Fecha'.
            df.rename(columns={df.columns[0]: 'Fecha'}, inplace=True)
            
            # Usamos 'ffill' (forward fill) para rellenar los espacios vacíos en la columna de fecha
            # con el último valor válido. Esto "descombina" la celda.
            df['Fecha'].ffill(inplace=True)

            # --- PASO 3: Seleccionar y renombrar las columnas que necesitamos ---
            # Ahora que los datos están limpios, seleccionamos las columnas de interés.
            df_procesado = df[['Fecha', 'total geomensura [tms]', 'Total THM [tms]']]

            # Renombramos las columnas para que coincidan con la base de datos.
            df_procesado.rename(columns={
                'Fecha': 'fecha',
                'total geomensura [tms]': 'ton_reclamo_camiones',
                'Total THM [tms]': 'ton_reclamo_camiones2'
            }, inplace=True)
            
            # --- PASO 4: Limpieza final y conversión de tipos ---
            df = df_procesado # Continuamos trabajando con nuestro DataFrame ya limpio.
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
            df['ton_reclamo_camiones'] = pd.to_numeric(df['ton_reclamo_camiones'], errors='coerce')
            df['ton_reclamo_camiones2'] = pd.to_numeric(df['ton_reclamo_camiones2'], errors='coerce')

            df.dropna(subset=['fecha'], inplace=True)

            if df.empty:
                return html.Div(['No se encontraron datos válidos en el archivo.'], style={'color': 'orange'})

        except KeyError as e:
             return html.Div([f'Error al procesar los datos: No se encontró la columna {e}. Revisa que los nombres de los títulos en la fila 2 del Excel sean correctos.'], style={'color': 'red'})
        except Exception as e:
            return html.Div([f'Error al procesar los datos. Detalle: {e}'], style={'color': 'red'})

        # --- Inserción en la Base de Datos (no necesita cambios) ---
        try:
            engine = get_engine()
            nombre_tabla_destino = "reclamos_tonelaje"
            df.to_sql(nombre_tabla_destino, con=engine, if_exists="append", index=False)
            
            return html.Div([f"✅ ¡Éxito! Se han cargado {len(df)} registros desde '{nombre_archivo}'."], style={'color': 'green', 'fontWeight': 'bold'})
        except Exception as e:
            return html.Div([f"❌ Ocurrió un error al guardar en la base de datos: {e}"], style={'color': 'red', 'fontWeight': 'bold'})