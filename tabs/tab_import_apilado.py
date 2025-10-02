import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd
from sqlalchemy import create_engine
from db_connection import get_connection  # Debe retornar un string SQLAlchemy
from db_connection import get_engine
import os

dash.register_page(__name__, path="/importar_apilado", name="Importar Apilado")

layout = html.Div([
    html.H5("Importar datos desde plantilla Apilado y Rotopalas"),
    dcc.Upload(
        id='upload-excel-apilado',
        children=html.Div([
            'Arrastra o selecciona archivo Excel (.xlsx)'
        ]),
        style={
            'width': '100%',
            'height': '80px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
        },
        multiple=False
    ),
    html.Div(id='resultado-carga-apilado', style={"marginTop": "20px"})
])

def procesar_y_cargar_apilado(contents, filename):
    import traceback


    try:
        if not filename.endswith('.xlsx'):
            return "❌ Formato no válido. Debe ser .xlsx"


        # Decodificar Excel
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        xls = pd.ExcelFile(io.BytesIO(decoded))


        # Conexión a BD
        engine = get_engine()


        # Leer claves de módulos y campañas
        df_mod_ext = pd.read_sql("SELECT id_pad, numero_modulo, id_modulo FROM inventar_SpcHidr.name_pad_modulo_ext", engine)
        df_campañas = pd.read_sql("SELECT id_campaña, numero_campaña FROM inventar_SpcHidr.campaña", engine)


        # Función para procesar bloques de hojas
        def proc_bloque(sheet, cols, skip, pad_id, colnames):
            try:
                df = pd.read_excel(xls, sheet_name=sheet, usecols=cols, skiprows=skip)
                if df.shape[1] != len(colnames): 
                    return pd.DataFrame()
                df.columns = colnames
                df["pad_id"] = pad_id
                return df
            except:
                return pd.DataFrame()


        col_ap = ["campaña", "modulo", "volumen_total_estimado_m3", "volumen_diario_m3",
                  "volumen_acumulado_final_apilado_m3", "avance_porcentaje", "altura_promedio_m", "promedio_grado", "fecha"]
        col_rec = ["campaña", "modulo", "volumen_total_estimado_m3", "volumen_diario_m3",
                   "volumen_final_reclamado", "avance_porcentaje", "alerta", "fecha"]
        col_rut = ["modulo", "volumen_total_estimado_m3", "fecha","campaña"]


        # Procesar cada hoja
        df_af = pd.concat([
            proc_bloque("Apilado Final", "A:I", 1, 2, col_ap),
            proc_bloque("Apilado Final", "K:S", 1, 1, col_ap)
        ])


        df_ad_raw = pd.read_excel(xls, sheet_name="Apilado Diario", skiprows=1)
        df_ad = pd.DataFrame()
        if df_ad_raw.shape[1] >= 9:
            df1 = df_ad_raw.iloc[:, 0:9].copy()
            df1.columns = col_ap
            df1["pad_id"] = 2
            df_ad = pd.concat([df_ad, df1], ignore_index=True)
        if df_ad_raw.shape[1] >= 19:
            df2 = df_ad_raw.iloc[:, 10:19].copy()
            df2.columns = col_ap
            df2["pad_id"] = 1
            df_ad = pd.concat([df_ad, df2], ignore_index=True)
        df_ad = df_ad.dropna(how="all")


        df_rf = pd.concat([
            proc_bloque("Rotopala Final", "A:H", 1, 2, col_rec),
            proc_bloque("Rotopala Final", "J:Q", 1, 1, col_rec)
        ])
        df_rd = pd.concat([
            proc_bloque("Rotopalas diario", "A:H", 1, 2, col_rec),
            proc_bloque("Rotopalas diario", "J:Q", 1, 1, col_rec)
        ])
        df_rt = pd.concat([
            proc_bloque("Modulos Ruteados", "A:D", 1, 2, col_rut),
            proc_bloque("Modulos Ruteados", "F:I", 1, 1, col_rut)
        ])


        # Normalizar columnas
        def normalizar_columnas(df, campo_validacion):
            if df.empty: return df
            df = df.copy()
            for c in ["campaña", "modulo"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            df = df[df[campo_validacion].notna()]
            # Convertir fechas
            for fecha_col in ["fecha"]:
                if fecha_col in df.columns:
                    df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
            return df


        df_af = normalizar_columnas(df_af, "volumen_acumulado_final_apilado_m3")
        df_ad = normalizar_columnas(df_ad, "volumen_acumulado_final_apilado_m3")
        df_rf = normalizar_columnas(df_rf, "volumen_final_reclamado")
        df_rd = normalizar_columnas(df_rd, "volumen_final_reclamado")
        df_rt = normalizar_columnas(df_rt, "volumen_total_estimado_m3")


        # Asignar claves de módulo y campaña
        def asignar_claves(df, df_mod_ext, df_campañas):
            if df.empty: return df
            df = df.merge(df_mod_ext, left_on=["pad_id","modulo"], right_on=["id_pad","numero_modulo"], how="left")
            df = df.rename(columns={"id_modulo":"modulo_id"})
            df = df.merge(df_campañas, left_on="campaña", right_on="numero_campaña", how="left")
            df = df.rename(columns={"id_campaña":"campaña_id"})
            df = df.drop(columns=["numero_modulo","numero_campaña","id_pad","id_modulo"], errors="ignore")
            return df


        df_af = asignar_claves(df_af, df_mod_ext, df_campañas)
        df_ad = asignar_claves(df_ad, df_mod_ext, df_campañas)
        df_rf = asignar_claves(df_rf, df_mod_ext, df_campañas)
        df_rd = asignar_claves(df_rd, df_mod_ext, df_campañas)
        df_rt = asignar_claves(df_rt, df_mod_ext, df_campañas)


        # --- Insertar por chunks ---
        def insert_chunks(df, table_name, rows_per_chunk=50):
            if df.empty: return
            for i in range(0, len(df), rows_per_chunk):
                chunk = df.iloc[i:i+rows_per_chunk]
                chunk.to_sql(table_name, engine, if_exists="append", index=False)


        insert_chunks(df_af, "control_apilado")
        insert_chunks(df_ad, "control_apilado_diario")
        insert_chunks(df_rf, "control_reclamo")
        insert_chunks(df_rd, "control_reclamo_diario")
        insert_chunks(df_rt, "control_modulo_ruteado")


        return f"✅ Datos importados exitosamente. AF:{len(df_af)}, AD:{len(df_ad)}, RF:{len(df_rf)}, RD:{len(df_rd)}, RT:{len(df_rt)}"


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
