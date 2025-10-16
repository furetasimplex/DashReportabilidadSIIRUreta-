import dash
from dash import html, dcc, Input, Output, State
import pandas as pd
import base64
import io
import re
from sqlalchemy import create_engine
from db_connection import get_engine
from sqlalchemy import text

def _purge_tables(engine):
    """Elimina todos los registros de ambas tablas en una transacción.
    Intenta TRUNCATE y, si hay FKs o permisos, cae a DELETE."""
    tablas = [
        "[inventar_SpcHidr].[reclamo_camiones_por_modulo]",
        "[inventar_SpcHidr].[reclamos_tonelaje]",
    ]
    with engine.begin() as conn:
        for fqtn in tablas:
            try:
                conn.execute(text(f"TRUNCATE TABLE {fqtn};"))
                print(f"Purga: TRUNCATE aplicado a {fqtn}")
            except Exception as e:
                print(f"Purga: TRUNCATE falló en {fqtn} → usando DELETE. Detalle: {e}")
                conn.execute(text(f"DELETE FROM {fqtn};"))

layout = html.Div([
    html.H4("Carga de Reclamos de Tonelaje (Sulfuro)"),
    dcc.Upload(
        id='upload-reclamos-sulfuro',
        children=html.Div(['Arrastra o selecciona el archivo Excel de Reclamos']),
        style={
            'width': '80%',
            'padding': '20px',
            'border': '1px dashed #aaa',
            'textAlign': 'center',
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
    def procesar_ambas_tareas(contenido, nombre_archivo):
        if contenido is None:
            return "Por favor, carga un archivo para comenzar."

        print("\n--- INICIANDO PROCESO DE CARGA DE ARCHIVO ---") # DEBUG
        try:
            content_type, content_string = contenido.split(',')
            decoded = base64.b64decode(content_string)
            excel_file = io.BytesIO(decoded)
            print("Archivo decodificado exitosamente.") # DEBUG
            engine = get_engine()
            print("Purga: borrando datos previos de ambas tablas...")  # DEBUG
            _purge_tables(engine)
        except Exception as e:
            print(f"ERROR: Fallo en la decodificación del archivo: {e}") # DEBUG
            return html.Div([f'Error al decodificar el archivo. Detalle: {e}'], style={'color': 'red'})

        mensajes = []
        
        # --- TAREA 1: CARGA DE TOTALES DIARIOS ---
        print("\n--- INICIANDO TAREA 1: TOTALES DIARIOS ---") # DEBUG
        try:
            excel_file.seek(0)
            df_task1 = pd.read_excel(excel_file, sheet_name="Reclamo Camiones SULFURO", header=1)
            print(f"Tarea 1: Archivo Excel leído. {df_task1.shape[0]} filas encontradas inicialmente.") # DEBUG
            
            df_task1.rename(columns={df_task1.columns[0]: 'Fecha'}, inplace=True)
            # Corrección del FutureWarning
            df_task1['Fecha'] = df_task1['Fecha'].ffill()

            df_procesado = df_task1[['Fecha', 'total geomensura [tms]', 'Total THM [tms]']]
            df_procesado.rename(columns={'Fecha': 'fecha', 'total geomensura [tms]': 'ton_reclamo_camiones', 'Total THM [tms]': 'ton_reclamo_camiones2'}, inplace=True)
            
            df_task1 = df_procesado
            df_task1['fecha'] = pd.to_datetime(df_task1['fecha'], errors='coerce').dt.date
            df_task1['ton_reclamo_camiones'] = pd.to_numeric(df_task1['ton_reclamo_camiones'], errors='coerce')
            df_task1['ton_reclamo_camiones2'] = pd.to_numeric(df_task1['ton_reclamo_camiones2'], errors='coerce')
            df_task1.dropna(subset=['fecha'], inplace=True)
            print(f"Tarea 1: Datos procesados. {len(df_task1)} filas válidas para insertar.") # DEBUG

            if not df_task1.empty:
                engine = get_engine()
                print("Tarea 1: Conectando a la base de datos para insertar...") # DEBUG
                df_task1.to_sql("reclamos_tonelaje", con=engine, if_exists="append", index=False, schema="inventar_SpcHidr")
                print(f"Tarea 1: Inserción exitosa de {len(df_task1)} registros.") # DEBUG
                mensajes.append(html.Div(f"✅ Tarea 1 (Totales Diarios): Se cargaron {len(df_task1)} registros en 'inventar_SpcHidr'.", style={'color': 'green'}))
            else:
                print("Tarea 1: No se encontraron datos válidos para insertar.") # DEBUG
                mensajes.append(html.Div("🔸 Tarea 1 (Totales Diarios): No se encontraron datos válidos.", style={'color': 'orange'}))

        except Exception as e:
            print(f"--- ERROR EN TAREA 1 ---: {e}") # DEBUG
            mensajes.append(html.Div(f"❌ Tarea 1 (Totales Diarios): Error al procesar. Detalle: {e}", style={'color': 'red'}))

        print("\n--- INICIANDO TAREA 2: MÓDULOS Y CAMPAÑAS ---")  # DEBUG
        try:
            engine = get_engine()
            print("Tarea 2: Conectando a la BD para obtener mapeos...")  # DEBUG

            # Tablas diccionario reales (alias a id/numero para no tocar más lógica)
            modulos_df = pd.read_sql(
                "SELECT id_modulo AS id, numero AS numero FROM inventar_SpcHidr.modulo",
                engine
            )
            campanas_df = pd.read_sql(
                "SELECT [id_campaña] AS id, [numero_campaña] AS numero FROM inventar_SpcHidr.[campaña]",
                engine
            )
            print(f"Tarea 2: Mapeos obtenidos. {len(modulos_df)} módulos y {len(campanas_df)} campañas.")  # DEBUG

            modulo_map  = pd.Series(modulos_df['id'].values, index=modulos_df['numero']).to_dict()
            campana_map = pd.Series(campanas_df['id'].values, index=campanas_df['numero']).to_dict()

            excel_file.seek(0)
            df_task2 = pd.read_excel(excel_file, sheet_name="Reclamo Camiones SULFURO", header=None)
            print("Tarea 2: Archivo Excel leído para análisis por columnas.")  # DEBUG

            start_col_index = 249  # IP
            end_col_index   = 264  # JE
            print(f"Tarea 2: Analizando columnas desde {start_col_index} (IP) hasta {end_col_index} (JE).")  # DEBUG

            all_results = []

            for col in range(start_col_index, end_col_index + 1):
                campaign_cell_value = df_task2.iloc[0, :col+1].ffill().iloc[col]
                if pd.notna(campaign_cell_value) and isinstance(campaign_cell_value, str) and campaign_cell_value.startswith('C'):
                    current_campaign_num = int(''.join(filter(str.isdigit, campaign_cell_value)))
                else:
                    continue

                module_raw  = df_task2.iloc[1, col]
                tonnage_raw = df_task2.iloc[2, col]

                if pd.notna(module_raw) and pd.notna(tonnage_raw):
                    module_num_match = re.search(r'\d+', str(module_raw))
                    if module_num_match:
                        module_num = int(module_num_match.group(0))
                        tonelaje   = pd.to_numeric(tonnage_raw, errors='coerce')

                        id_modulo  = modulo_map.get(module_num)
                        campana_id = campana_map.get(current_campaign_num)

                        if pd.notna(tonelaje) and tonelaje > 0 and id_modulo is not None and campana_id is not None:
                            print(f"  > OK: Campaña {current_campaign_num}→ID {campana_id}, "
                                f"Módulo {module_num}→ID {id_modulo}, TMS {tonelaje}")  # DEBUG
                            all_results.append({
                                'tonelaje_reclamado': float(tonelaje),
                                'id_modulo': int(id_modulo),          # FK
                                'campana_id': int(campana_id),         # FK
                                'campana': int(current_campaign_num),  # número requerido por la tabla
                                'numero_modulo': int(module_num)       # número requerido por la tabla
                            })

            if all_results:
                final_df = pd.DataFrame(all_results)
                print(f"Tarea 2: {len(final_df)} registros válidos para insertar.")  # DEBUG
                print("Tarea 2: Insertando en BD...")  # DEBUG
                final_df.to_sql(
                    "reclamo_camiones_por_modulo",
                    con=engine,
                    if_exists="append",
                    index=False,
                    schema="inventar_SpcHidr"
                )
                print(f"Tarea 2: Inserción exitosa de {len(final_df)} registros.")  # DEBUG
                mensajes.append(html.Div(
                    f"✅ Tarea 2 (Módulos y Campañas): {len(final_df)} registros relacionados cargados.",
                    style={'color': 'green'}
                ))
            else:
                print("Tarea 2: No se encontraron registros válidos.")  # DEBUG
                mensajes.append(html.Div(
                    "🔸 Tarea 2 (Módulos y Campañas): No se encontraron datos válidos o correspondencias de ID.",
                    style={'color': 'orange'}
                ))

        except Exception as e:
            print(f"--- ERROR EN TAREA 2 ---: {e}")  # DEBUG
            mensajes.append(html.Div(
                f"❌ Tarea 2 (Módulos y Campañas): Error al procesar. Detalle: {e}",
                style={'color': 'red'}
            ))
        print("\n--- PROCESO DE CARGA FINALIZADO ---") # DEBUG
        return html.Div([
            html.H5(f"Resultados de la carga para '{nombre_archivo}':"),
            html.Br()
        ] + mensajes)