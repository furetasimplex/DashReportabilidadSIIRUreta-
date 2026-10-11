import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
from sqlalchemy import create_engine
from db_connection import get_engine
from sqlalchemy.sql import text

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
            content_type, content_string = contenido.split(',')
            decoded = base64.b64decode(content_string)
            excel_data = io.BytesIO(decoded)

            # Leer Excel
            df = pd.read_excel(excel_data, sheet_name="Base_Datos", header=0)
            
            df = df[df["Año"].notna()]
            df = df[df["Año"] < 2030]
            
            # Crear campo Fecha
            # Convertir a string y rellenar con ceros a la izquierda si es necesario
            df["Año"] = df["Año"].fillna(0).astype(int).astype(str).str.zfill(4)
            df["Mes"] = df["Mes"].fillna(0).astype(int).astype(str).str.zfill(2)
            df["Dia"] = df["Dia"].fillna(0).astype(int).astype(str).str.zfill(2)

            # Concatenar en formato YYYY-MM-DD
            df["Fecha_str"] = df["Año"] + "-" + df["Mes"] + "-" + df["Dia"]

            # Convertir a datetime, forzando error a NaT si es inválido (por ejemplo, "0000-00-00")
            df["Fecha"] = pd.to_datetime(df["Fecha_str"], errors="coerce")

            


            
            df = df[df["Fecha"].dt.year < 2030]

            # Reordenar columnas
            columnas = ["Fecha"] + [col for col in df.columns if col not in ["Año", "Mes", "Dia", "Fecha","Fecha_str"]]
            df = df[columnas]
            # Definir columnas clave para detección de duplicados
            columnas_clave = ["Fecha", "Turno", "Origen", "Solido", "Ton", "Poligono_CIO"]

            # Filtrar solo las filas con Fecha válida
            df = df[df["Fecha"].notna()]

            # Obtener fechas mínima y máxima del archivo cargado
            fecha_min = df["Fecha"].min().strftime('%Y-%m-%d')
            fecha_max = df["Fecha"].max().strftime('%Y-%m-%d')
            engine = get_engine()

            # Cargar desde la base solo registros dentro del rango de fechas
            query = text("""
                SELECT Fecha, Turno, Origen, Solido, Ton, Poligono_CIO
                FROM mov_cam
                WHERE Fecha BETWEEN :fecha_min AND :fecha_max
            """)

            df_existente = pd.read_sql(query, con=engine, params={"fecha_min": fecha_min, "fecha_max": fecha_max})

            # Paso 6: Verificar si existen duplicados
            if df_existente.empty:
                # No hay duplicados, insertar todo
                print(f"Insertando todos los registros: {len(df)}")
                df.to_sql("mov_cam", con=engine, if_exists="append", index=False)
            else:
                # Comparar registros nuevos contra existentes
                df_existente["Fecha"] = pd.to_datetime(df_existente["Fecha"], errors="coerce")
                df_total = pd.concat([df_existente, df], ignore_index=True)
                df_filtrado = df_total.drop_duplicates(subset=columnas_clave, keep=False)

                # Extraer solo las filas nuevas desde df original
                df_nuevos = df.merge(df_filtrado, on=columnas_clave, how="inner")

                print(f"Registros nuevos a insertar: {len(df_nuevos)}")

                if not df_nuevos.empty:
                    df_nuevos.to_sql("mov_cam", con=engine, if_exists="append", index=False)

            return f"Archivo '{nombre_archivo}' cargado correctamente. Registros cargados: {len(df)}"
        except Exception as e:
            return f"Error: {str(e)}"