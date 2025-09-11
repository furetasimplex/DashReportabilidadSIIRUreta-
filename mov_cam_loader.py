
import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
from sqlalchemy import create_engine
import base64
import io

# Configuración de conexión MySQL
usuario = 'tu_usuario'
contraseña = 'tu_contraseña'
host = 'localhost'
puerto = '3306'
base_datos = 'nombre_base'
engine = create_engine(f"mysql+pymysql://{usuario}:{contraseña}@{host}:{puerto}/{base_datos}")

# App Dash
app = dash.Dash(__name__)
app.title = "Carga mov_cam"

app.layout = html.Div([
    html.H4("Cargar archivo de movimientos de mina (mov_cam)"),
    dcc.Upload(
        id='upload-excel',
        children=html.Div(['Arrastra o selecciona el archivo Excel']),
        style={
            'width': '50%',
            'padding': '20px',
            'border': '1px dashed #aaa',
            'textAlign': 'center',
        },
        multiple=False
    ),
    html.Div(id='upload-status', style={'marginTop': 20})
])

@app.callback(
    Output('upload-status', 'children'),
    Input('upload-excel', 'contents'),
    State('upload-excel', 'filename')
)
def procesar_mov_cam(contenido, nombre_archivo):
    if contenido is None:
        return "No se ha cargado ningún archivo."

    try:
        content_type, content_string = contenido.split(',')
        decoded = base64.b64decode(content_string)
        excel_data = io.BytesIO(decoded)

        # Leer hoja "Base_Datos", encabezado en fila 2 (index 1)
        df = pd.read_excel(excel_data, sheet_name="Base_Datos", header=1)

        # Crear columna Fecha
        df["Fecha"] = pd.to_datetime(df[["Año", "Mes", "Dia"]], errors="coerce")

        # Filtrar año < 2030
        df = df[df["Fecha"].dt.year < 2030]

        # Reordenar columnas: Fecha primero
        columnas = ["Fecha"] + [col for col in df.columns if col not in ["Año", "Mes", "Dia", "Fecha"]]
        df = df[columnas]

        # Subir a tabla ya existente: mov_cam
        df.to_sql(name="mov_cam", con=engine, if_exists="append", index=False)
        return f"Archivo '{nombre_archivo}' cargado exitosamente en la tabla 'mov_cam'. Registros cargados: {len(df)}"

    except Exception as e:
        return f"Error procesando el archivo: {str(e)}"

if __name__ == '__main__':
    app.run_server(debug=True)
