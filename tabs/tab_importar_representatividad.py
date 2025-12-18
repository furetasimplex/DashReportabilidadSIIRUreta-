import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
from sqlalchemy import text
from db_connection import get_engine

# --- LAYOUT DEL TAB ---
layout = html.Div([
    html.H4("Carga de Representatividad de Torres (Hoja: Reporte Diario)"),
    dcc.Upload(
        id='upload-representatividad',
        children=html.Div([
            html.I(className="bi bi-file-earmark-bar-graph fs-1 text-success"),
            html.H5("Subir Excel 'BD Torres...'", className="mt-2 mb-1 fw-semibold"),
            html.P("El sistema buscará automáticamente la hoja 'Reporte Diario' y filtrará fechas inválidas."),
        ]),
        className=(
            "border-dashed border-success text-center "
            "py-4 rounded-3 bg-light-subtle"
        ),
        style={
            "cursor": "pointer",
            "transition": "all 0.25s ease-in-out",
            "border": "1px dashed #aaa"
        },
        multiple=False
    ),
    html.Div(id='status-representatividad', style={'marginTop': 20})
])

# --- LÓGICA DE PROCESAMIENTO ---
def register_callbacks(app):
    @app.callback(
        Output('status-representatividad', 'children'),
        Input('upload-representatividad', 'contents'),
        State('upload-representatividad', 'filename')
    )
    def procesar_representatividad(contenido, nombre_archivo):
        if contenido is None:
            return "Esperando archivo..."

        print(f"\n--- PROCESANDO ARCHIVO: {nombre_archivo} ---")
        mensajes = []

        try:
            # 1. Decodificar archivo
            content_type, content_string = contenido.split(',')
            decoded = base64.b64decode(content_string)
            excel_file = io.BytesIO(decoded)
            
            # 2. Leer Excel (Configuración Específica)
            # Hoja: "Reporte Diario"
            # Filas a saltar: 9
            # Indices: AT(45) hasta AX(49) y BH(59) hasta BK(62)
            indices_columnas = [45, 46, 47, 48, 49, 59, 60, 61, 62]
            
            df = pd.read_excel(
                excel_file, 
                sheet_name="Reporte Diario", 
                header=None, 
                skiprows=9, 
                usecols=indices_columnas
            )
            
            # Renombramos manualmente
            df.columns = [
                'Dia', 
                'TM1_TurnoA_Quimico', 'TM1_TurnoA_Fisico', 
                'TM1_TurnoB_Quimico', 'TM1_TurnoB_Fisico',
                'TM2_TurnoA_Quimico', 'TM2_TurnoA_Fisico', 
                'TM2_TurnoB_Quimico', 'TM2_TurnoB_Fisico'
            ]

            # --- LIMPIEZA Y FILTRADO DE FECHAS ---
            # Borrar filas donde 'Dia' sea totalmente vacío
            df.dropna(subset=['Dia'], inplace=True) 

            # Convertir a datetime (errores se vuelven NaT)
            df['Dia'] = pd.to_datetime(df['Dia'], errors='coerce')
            
            # FILTRO CLAVE: Mantener solo fechas mayores a 2020-01-01
            # Esto elimina el 1970-01-01 y cualquier basura histórica
            df = df[df['Dia'] > '2020-01-01']
            
            # Convertir finalmente a objeto date (sin hora) para SQL
            df['Dia'] = df['Dia'].dt.date

            print(f"Filas VÁLIDAS encontradas (post-filtro fecha): {len(df)}")
            
            if df.empty:
                return html.Div("❌ No se encontraron datos con fechas válidas (posteriores a 2020).", style={'color': 'red'})

            # 3. Insertar en Base de Datos
            engine = get_engine()
            registros_exitosos = 0
            
            with engine.begin() as conn:
                for index, row in df.iterrows():
                    # Preparar parámetros
                    params = {
                        'p_Dia': row['Dia'],
                        'p_TM1_AQ': str(row['TM1_TurnoA_Quimico']) if pd.notna(row['TM1_TurnoA_Quimico']) else None,
                        'p_TM1_AF': str(row['TM1_TurnoA_Fisico']) if pd.notna(row['TM1_TurnoA_Fisico']) else None,
                        'p_TM1_BQ': str(row['TM1_TurnoB_Quimico']) if pd.notna(row['TM1_TurnoB_Quimico']) else None,
                        'p_TM1_BF': str(row['TM1_TurnoB_Fisico']) if pd.notna(row['TM1_TurnoB_Fisico']) else None,
                        'p_TM2_AQ': str(row['TM2_TurnoA_Quimico']) if pd.notna(row['TM2_TurnoA_Quimico']) else None,
                        'p_TM2_AF': str(row['TM2_TurnoA_Fisico']) if pd.notna(row['TM2_TurnoA_Fisico']) else None,
                        'p_TM2_BQ': str(row['TM2_TurnoB_Quimico']) if pd.notna(row['TM2_TurnoB_Quimico']) else None,
                        'p_TM2_BF': str(row['TM2_TurnoB_Fisico']) if pd.notna(row['TM2_TurnoB_Fisico']) else None,
                    }

                    sql_query = text("""
                        EXEC inventar_SpcHidr.sp_Importar_Representatividad 
                        :p_Dia, 
                        :p_TM1_AQ, :p_TM1_AF, :p_TM1_BQ, :p_TM1_BF,
                        :p_TM2_AQ, :p_TM2_AF, :p_TM2_BQ, :p_TM2_BF
                    """)
                    
                    conn.execute(sql_query, params)
                    registros_exitosos += 1

            mensajes.append(html.Div(f"✅ Éxito: Se procesaron {registros_exitosos} días válidos.", style={'color': 'green'}))
            mensajes.append(html.Div(f"ℹ️ Se filtraron automáticamente fechas inválidas (1970, vacíos, etc).", style={'fontSize': '0.9em', 'color': 'gray'}))

        except Exception as e:
            print(f"ERROR CRITICO: {e}")
            return html.Div([
                html.H5("❌ Error en la carga"),
                html.P(f"Detalle: {str(e)}")
            ], style={'color': 'red'})

        return html.Div(mensajes)