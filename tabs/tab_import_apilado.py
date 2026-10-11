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
    if not filename.endswith('.xlsx'):
        return "❌ Formato no válido. Debe ser .xlsx"

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    xls = pd.ExcelFile(io.BytesIO(decoded))

    # Conexión a BD
    engine = get_engine()

    # Leer claves
    df_mod_ext = pd.read_sql("SELECT id_pad, numero_modulo, id_modulo FROM name_pad_modulo_ext", engine)
    df_campañas = pd.read_sql("SELECT id_campaña, numero_campaña, id_modulo FROM campaña", engine)
    #print(df_mod_ext)

    def proc_bloque(sheet, cols, skip, pad_id, colnames):
        try:
            df = pd.read_excel(xls, sheet_name=sheet, usecols=cols, skiprows=skip)
            if df.shape[1] != len(colnames): return pd.DataFrame()
            df.columns = colnames
            df["pad_id"] = pad_id
            return df
        except: return pd.DataFrame()

    col_ap = ["campaña", "modulo", "volumen_total_estimado_m3", "volumen_diario_m3",
              "volumen_acumulado_final_apilado_m3", "avance_porcentaje", "altura_promedio_m", "promedio_grado", "fecha"]
    col_rec = ["campaña", "modulo", "volumen_total_estimado_m3", "volumen_diario_m3",
               "volumen_final_reclamado", "avance_porcentaje", "alerta", "fecha"]
    
    col_rut = ["modulo", "volumen_total_estimado_m3", "fecha","campaña"]


    df_af = pd.concat([
        proc_bloque("Apilado Final", "A:I", 1, 2, col_ap),
        proc_bloque("Apilado Final", "K:S", 1, 1, col_ap)
    ])
    print(df_af)
    try:
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

        df_ad = df_ad.dropna(how="all")  # elimina filas completamente vacías

    except Exception as e:
        print(f"❌ Error leyendo hoja 'Apilado Diario': {e}")
        df_ad = pd.DataFrame()

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
    print(df_rt)
    def normalizar_columnas(df, campo_validacion):
        print(df)    
        """
        Convierte 'campaña' y 'módulo' a enteros, y filtra filas donde el campo de validación no sea nulo.
        """
        if df.empty:
            return df
        df = df.copy()
        print(df.columns.tolist())
        df["campaña"] = pd.to_numeric(df["campaña"], errors='coerce').astype('float')
        df["modulo"] = pd.to_numeric(df["modulo"], errors='coerce').astype('float')
        df = df[df[campo_validacion].notna()]
        return df

    df_af = normalizar_columnas(df_af, "volumen_acumulado_final_apilado_m3")
    df_ad = normalizar_columnas(df_ad, "volumen_acumulado_final_apilado_m3")
    df_rf = normalizar_columnas(df_rf, "volumen_final_reclamado")
    df_rd = normalizar_columnas(df_rd, "volumen_final_reclamado")
    df_rt = normalizar_columnas(df_rt, "volumen_total_estimado_m3")
    def asignar_claves(df, df_mod_ext, df_campañas):
        if df.empty:
            return df

        # Asignar módulo_id desde vista extendida (pad_id + número_modulo)
        df = df.merge(
            df_mod_ext,
            left_on=["pad_id", "modulo"],
            right_on=["id_pad", "numero_modulo"],
            how="left"
        )
        df = df.rename(columns={"id_modulo": "modulo_id"})

        # Asignar campaña_id desde tabla campaña (número_campaña + modulo_id)
        df = df.merge(
        df_campañas[["id_campaña", "numero_campaña"]],
            left_on="campaña",
            right_on="numero_campaña",
            how="left"
        )
        df = df.rename(columns={"id_campaña": "campaña_id"})
       

        # Eliminar columnas auxiliares
        df = df.drop(columns=["numero_modulo", "numero_campaña", "id_pad", "id_modulo"], errors="ignore")
        return df

    df_af = asignar_claves(df_af, df_mod_ext, df_campañas)
    df_ad = asignar_claves(df_ad, df_mod_ext, df_campañas)
    df_rf = asignar_claves(df_rf, df_mod_ext, df_campañas)
    df_rd = asignar_claves(df_rd, df_mod_ext, df_campañas)
    df_rt = asignar_claves(df_rt, df_mod_ext, df_campañas)
    print(df_rt)
    if not df_af.empty:
        df_af.to_sql("control_apilado", engine, if_exists="append", index=False)
    if not df_ad.empty:
        df_ad.to_sql("control_apilado_diario", engine, if_exists="append", index=False)
    if not df_rf.empty:
        df_rf.to_sql("control_reclamo", engine, if_exists="append", index=False)
    if not df_rd.empty:
        df_rd.to_sql("control_reclamo_diario", engine, if_exists="append", index=False)
    if not df_rt.empty:
        df_rt.to_sql("control_modulo_ruteado", engine, if_exists="append", index=False)

    return "✅ Datos importados exitosamente."

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
