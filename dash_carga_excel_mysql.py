
import dash
from dash import dcc, html, Input, Output, State, ctx
import pandas as pd
from sqlalchemy import create_engine
import base64
import io
import os
from dotenv import load_dotenv
from db_connection import get_engine
load_dotenv()
engine = get_engine()

# Conexión a base de datos MySQL

#puerto = '3306'

#engine = create_engine(f"mysql+pymysql://{usuario}:{contraseña}@{host}:{puerto}/{base_datos}")

# Función para limpiar y preparar los datos de la hoja "Datos filtrados"
def limpiar_datos_filtrados(df_raw):
    df = df_raw.copy()
    df.columns = [str(col).strip().replace(" ", "_").replace(".", "_").lower() for col in df.columns]
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        except:
            pass
    for fecha_col in ['fecha_inicial', 'fecha_final']:
        if fecha_col in df.columns:
            df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
    return df

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H3("Cargar Template Excel"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Arrastra o selecciona un archivo .xlsx']),
        style={'width': '50%', 'padding': '20px', 'border': '1px dashed #aaa'},
        multiple=False
    ),
    html.Div(id='output-status', style={'marginTop': 20})
])

@app.callback(
    Output('output-status', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def procesar_excel(contenido, nombre_archivo):
    if contenido is None:
        return "No se ha cargado ningún archivo."

    content_type, content_string = contenido.split(',')
    decoded = base64.b64decode(content_string)
    excel_data = io.BytesIO(decoded)

    try:
        # Leer hoja "Datos filtrados" desde fila 3 (header en fila 1), hasta columna AH
        df_raw = pd.read_excel(excel_data, sheet_name="Datos filtrados", header=0, skiprows=[1], usecols="A:AH")
        df_limpio = limpiar_datos_filtrados(df_raw)

        # Subir a MySQL
        df_limpio.to_sql(name="datos_filtrados", con=engine, if_exists="replace", index=False)
        return f"Archivo '{nombre_archivo}' procesado y cargado exitosamente en la tabla 'datos_filtrados'."
    except Exception as e:
        return f"Error procesando el archivo: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
