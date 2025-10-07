import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd
from sqlalchemy import create_engine, text
from db_connection import get_engine
import os
import traceback

dash.register_page(__name__, path="/importar_apilado", name="Importar Apilado")

layout = html.Div([
    html.H5("Importar datos desde plantilla Apilado y Rotopalas"),
    dcc.Upload(
        id='upload-excel-apilado',
        children=html.Div(['Arrastra o selecciona archivo Excel (.xlsx)']),
        style={
            'width': '100%', 'height': '80px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center',
        },
        multiple=False
    ),
    html.Div(id='resultado-carga-apilado', style={"marginTop": "20px"})
])

def procesar_y_cargar_apilado(contents, filename):
    try:
        if not filename.endswith('.xlsx'):
            return "❌ Formato no válido. Debe ser .xlsx"

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        xls = pd.ExcelFile(io.BytesIO(decoded))

        engine = get_engine()

        df_mod_ext = pd.read_sql("SELECT id_pad, numero_modulo, id_modulo FROM inventar_SpcHidr.name_pad_modulo_ext", engine)
        df_campañas = pd.read_sql("SELECT id_campaña, numero_campaña FROM inventar_SpcHidr.campaña", engine)

        def proc_bloque(sheet, cols, skip, pad_id, colnames):
            try:
                df = pd.read_excel(xls, sheet_name=sheet, usecols=cols, skiprows=skip)
                if df.shape[1] != len(colnames): return pd.DataFrame()
                df.columns = colnames
                df["pad_id"] = pad_id
                return df
            except:
                return pd.DataFrame()

        col_ap = ["campaña", "modulo", "volumen_total_estimado_m3", "volumen_diario_m3", "volumen_acumulado_final_apilado_m3", "avance_porcentaje", "altura_promedio_m", "promedio_grado", "fecha"]
        col_rec_sulfuro = ["campaña", "modulo", "volumen_total_estimado_m3", "volumen_diario_m3", "volumen_final_reclamado", "avance_porcentaje", "fecha"]
        col_rec_oxido = ["campaña", "modulo", "volumen_total_estimado_m3", "volumen_diario_m3", "volumen_final_reclamado", "avance_porcentaje", "alerta", "fecha"]
        col_rut = ["modulo", "volumen_total_estimado_m3", "fecha", "campaña"]

        # --- Extracción de Datos ---
        df_af = pd.concat([
            proc_bloque("Apilado Final", "A:I", 1, 2, col_ap), 
            proc_bloque("Apilado Final", "K:S", 1, 1, col_ap)
        ])
        df_ad = pd.concat([
            proc_bloque("Apilado Diario", "A:I", 1, 2, col_ap),
            proc_bloque("Apilado Diario", "K:S", 1, 1, col_ap)
        ])
        
        # --- Extracción Especial para Rotopalas (Estructura Asimétrica) ---
        # Rotopala Final
        df_rf_sulfuro = proc_bloque("Rotopala Final", "A:G", 1, 2, col_rec_sulfuro)
        if not df_rf_sulfuro.empty:
            df_rf_sulfuro['alerta'] = None
        df_rf_oxido = proc_bloque("Rotopala Final", "AA:AH", 1, 1, col_rec_oxido)
        df_rf = pd.concat([df_rf_sulfuro, df_rf_oxido], ignore_index=True)

        # Rotopalas Diario
        df_rd_sulfuro = proc_bloque("Rotopalas diario", "A:G", 1, 2, col_rec_sulfuro)
        if not df_rd_sulfuro.empty:
            df_rd_sulfuro['alerta'] = None
        df_rd_oxido = proc_bloque("Rotopalas diario", "AA:AH", 1, 1, col_rec_oxido)
        df_rd = pd.concat([df_rd_sulfuro, df_rd_oxido], ignore_index=True)

        df_rt = pd.concat([
            proc_bloque("Modulos Ruteados", "A:D", 1, 2, col_rut), 
            proc_bloque("Modulos Ruteados", "F:I", 1, 1, col_rut)
        ])

        # --- Normalización y Limpieza ---
        def normalizar_columnas(df, campo_validacion):
            if df.empty: return df
            df = df.copy()
            if 'promedio_grado' in df.columns:
                df['promedio_grado'] = df['promedio_grado'].astype(str).str.replace('°', '', regex=False)
                df['promedio_grado'] = pd.to_numeric(df['promedio_grado'], errors='coerce')
            for c in ["campaña", "modulo"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            df = df.dropna(subset=[campo_validacion])
            if "fecha" in df.columns:
                df["fecha"] = pd.to_datetime(df["fecha"], errors='coerce')
            return df

        df_af = normalizar_columnas(df_af, "volumen_acumulado_final_apilado_m3")
        df_ad = normalizar_columnas(df_ad, "volumen_diario_m3")
        df_rf = normalizar_columnas(df_rf, "modulo") 
        df_rd = normalizar_columnas(df_rd, "volumen_diario_m3")
        df_rt = normalizar_columnas(df_rt, "volumen_total_estimado_m3")
        
        # --- Asignación de Claves Foráneas ---
        def asignar_claves(df, df_mod_ext, df_campañas):
            if df.empty: return df
            df = df.merge(df_mod_ext, left_on=["pad_id","modulo"], right_on=["id_pad","numero_modulo"], how="left")
            df = df.rename(columns={"id_modulo":"modulo_id"})
            df = df.merge(df_campañas, left_on="campaña", right_on="numero_campaña", how="left")
            df = df.rename(columns={"id_campaña":"campaña_id"})
            df = df.drop(columns=["numero_modulo","numero_campaña","id_pad"], errors="ignore")
            if 'id_modulo' in df.columns and 'modulo_id' in df.columns:
                df = df.drop(columns=['id_modulo'])
            return df

        df_af = asignar_claves(df_af, df_mod_ext, df_campañas)
        df_ad = asignar_claves(df_ad, df_mod_ext, df_campañas)
        df_rf = asignar_claves(df_rf, df_mod_ext, df_campañas)
        df_rd = asignar_claves(df_rd, df_mod_ext, df_campañas)
        df_rt = asignar_claves(df_rt, df_mod_ext, df_campañas)

        # --- Filtrado con Reporte ---
        report_messages = []
        def filter_and_report_unlinked(df, df_name):
            if df.empty: return df
            
            unlinked_rows = df[df['modulo_id'].isnull() | df['campaña_id'].isnull()]
            df.dropna(subset=['modulo_id', 'campaña_id'], inplace=True)
            
            if len(unlinked_rows) > 0:
                msg = f"De '{df_name}', se descartaron {len(unlinked_rows)} fila(s) porque su Módulo o Campaña no se encontraron en la BD."
                report_messages.append(msg)
                print(f"--- Filas descartadas de {df_name} ---")
                print(unlinked_rows[['campaña', 'modulo']])
                print("---------------------------------------")
            return df

        df_af = filter_and_report_unlinked(df_af, "Apilado Final")
        df_ad = filter_and_report_unlinked(df_ad, "Apilado Diario")
        df_rf = filter_and_report_unlinked(df_rf, "Reclamo Final")
        df_rd = filter_and_report_unlinked(df_rd, "Reclamo Diario")
        df_rt = filter_and_report_unlinked(df_rt, "Módulos Ruteados")
        
        # --- Lógica de Carga a Base de Datos (Anti-duplicados) ---
        def eliminar_y_cargar_datos(df, table_name, unique_keys, engine, schema=None):
            if df.empty: return
            full_table_name = f'"{schema}"."{table_name}"' if schema else f'"{table_name}"'
            with engine.connect() as connection:
                transaction = connection.begin()
                try:
                    for _, row in df.iterrows():
                        conditions = []
                        params = {}
                        for key in unique_keys:
                            if key == 'fecha':
                                if pd.notna(row[key]):
                                    conditions.append(f"CAST([{key}] AS DATE) = :val_{key}")
                                    params[f"val_{key}"] = row[key].strftime('%Y-%m-%d')
                            elif pd.notna(row[key]):
                                conditions.append(f'"{key}" = :val_{key}')
                                params[f"val_{key}"] = row[key]
                        if conditions:
                            delete_stmt = f"DELETE FROM {full_table_name} WHERE {' AND '.join(conditions)}"
                            connection.execute(text(delete_stmt), params)
                    
                    df.to_sql(table_name, connection, if_exists="append", index=False, schema=schema)
                    transaction.commit()
                except Exception as e:
                    transaction.rollback()
                    raise e
        
        schema_name = "inventar_SpcHidr"
        eliminar_y_cargar_datos(df_af, "control_apilado", ["modulo_id", "campaña_id"], engine, schema=schema_name)
        eliminar_y_cargar_datos(df_ad, "control_apilado_diario", ["fecha", "modulo_id", "campaña_id"], engine, schema=schema_name)
        eliminar_y_cargar_datos(df_rf, "control_reclamo", ["modulo_id", "campaña_id"], engine, schema=schema_name)
        eliminar_y_cargar_datos(df_rd, "control_reclamo_diario", ["fecha", "modulo_id", "campaña_id"], engine, schema=schema_name)
        eliminar_y_cargar_datos(df_rt, "control_modulo_ruteado", ["fecha", "modulo_id", "campaña_id"], engine, schema=schema_name)

        # --- Mensaje de Resultado con Advertencias ---
        final_message = f"✅ Datos importados y actualizados. AF:{len(df_af)}, AD:{len(df_ad)}, RF:{len(df_rf)}, RD:{len(df_rd)}, RT:{len(df_rt)}"
        if report_messages:
            warnings = "\\n\\n**Advertencias:**\\n- " + "\\n- ".join(report_messages)
            final_message += warnings
        
        return html.Div(dcc.Markdown(final_message.replace('\\n', '\n')))

    except Exception as e:
        traceback.print_exc()
        return f"❌ Error procesando archivo: {str(e)}"

def register_callbacks(app):
    @app.callback(
        Output("resultado-carga-apilado", "children"),
        Input("upload-excel-apilado", "contents"),
        State("upload-excel-apilado", "filename")
    )
    def importar_apilado(contents, filename):
        if contents is None:
            return ""
        return procesar_y_cargar_apilado(contents, filename)
