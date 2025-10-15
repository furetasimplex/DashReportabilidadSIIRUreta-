from dash.dependencies import Input, Output, State
from dash import callback, ctx, dcc
import base64
import io
import os
import plotly.graph_objs as go
import plotly.express as px
import datetime
import numpy as np
import pandas as pd
from pandasql import sqldf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from tabs.aguaApp.utils.utils_dash import (
    get_fig_bal_casos_agua,
    get_data_save_tags_agua,
    get_agua_his_casos_agua,
    get_data_publica_casos_agua,
    get_data_agua_casos_agua,
    get_data_save_casos_agua,
    carta_control_agua,
    parse_contents_agua,
    local_img_to_html_agua,
)
from tabs.aguaApp.utils.utils_recon import balance_core_agua


project_folder = os.path.dirname(os.path.realpath(__file__))
assets_folder = os.path.join(project_folder, 'assets')


def register_appagua_callbacks(app):
    # === IMAGEN BALANCE ===
    @app.callback(
        Output('imagen_balance_agua', 'src'),
        Input('agg_tab2_agua', 'value'),
        Input('id_caso_activo_agua', 'value'),
        prevent_initial_call=True
    )
    def actualizar_imagen_agua(agg_tab2_agua, maxid_agua):
        imagen = get_fig_bal_casos_agua(maxid_agua, agg_tab2_agua)
        return imagen

    # === GET CASOS ===
    @app.callback(
        Output('data_casos2_agua', 'rowData'),
        Output('data_hcas2_agua', 'rowData'),
        Output('id_caso_activo_agua', 'value'),
        Input('btn_get_casos_agua', 'n_clicks'),
        Input('fecha_inicio_caso_agua', 'value'),
        Input('fecha_final_caso_agua', 'value'),
        Input('crea_caso_agua', 'value'),
        prevent_initial_call=True,
    )
    def get_data_casos_agua(n_clicks, inicio, final, crea_caso):
        if not n_clicks:
            return [], [], None

        if ctx.triggered_id == 'btn_get_casos_agua':
            inicio_tag = inicio + ' 08:00'
            final_tag = final + ' 07:00'

            valor_crea = 'Si' if crea_caso == ['Si'] else 'No'
            print('inicio:', inicio_tag)
            print('final:', final_tag)
            print(valor_crea)

            df_mina = get_data_agua_casos_agua(inicio, final, valor_crea)
            print(f"df_mina: {df_mina}")
            maxid = df_mina["caso_id"].max()
            df_hcasos = get_agua_his_casos_agua(final)

            return df_mina.to_dict('records'), df_hcasos.to_dict('records'), maxid

    # === SAVE CASOS ===
    @app.callback(
        Input('btn_save_casos_agua', 'n_clicks'),
        Input('data_casos2_agua', 'rowData'),
        Input('fecha_final_caso_agua', 'value'),
        Input('id_caso_activo_agua', 'value'),
    )
    def save_data_casos_agua(n_clicks, dat_casos, final, maxcas):
        if ctx.triggered_id == 'btn_save_casos_agua':
            print('Actualizando datos de casos...')
            get_data_save_casos_agua(dat_casos, final, maxcas)
            return

    # === PUBLICAR CASOS ===
    @app.callback(
        Input('btn_publica_casos_agua', 'n_clicks'),
        Input('recon_resultados_agua', 'rowData'),
        Input('data_casos2_agua', 'rowData'),
        Input('id_caso_activo_agua', 'value'),
    )
    def publicar_casos_agua(n_clicks, rec_caso, data_casos, maxcas):
        if ctx.triggered_id == 'btn_publica_casos_agua':
            print('Publicando datos...')
            get_data_publica_casos_agua(data_casos, rec_caso, maxcas)
            return

    # === SAVE TAGS ===
    @app.callback(
        Input('btn_save_tag_agua', 'n_clicks'),
        Input('data_base_tag_agua', 'rowData'),
        Input('fecha_inicio_tag_agua', 'value'),
        Input('fecha_final_tag_agua', 'value'),
    )
    def guardar_tags_agua(n_clicks, rec_tags, inicio, final):
        inicio_tag = inicio + ' 08:00:00'
        final_tag = final + ' 07:00:01'
        if ctx.triggered_id == 'btn_save_tag_agua':
            print('Guardando tags...')
            get_data_save_tags_agua(inicio_tag, final_tag, rec_tags)
            return

    # === LOAD DATOS BASE ===
    @app.callback(
        Output('recon_data_base_agua', 'rowData'),
        Input('data_base_upload_agua', 'contents'),
        Input('data_base_upload_agua', 'filename'),
        prevent_initial_call=True,
    )
    def recon_get_data_base_agua(contents, filename):
        if contents is not None:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df_data_base = pd.read_excel(io.BytesIO(decoded), sheet_name='Datos bases')
            return df_data_base.round(4).to_dict('records')

    # === RECONCILIADOR ===
    @app.callback(
        Output('recon_resultados_agua', 'rowData'),
        Output('recon_desbalances_agua', 'rowData'),
        Input('btn_recon_agua', 'n_clicks'),
        Input('recon_data_base_agua', 'rowData'),
    )
    def get_recon_agua(n_clicks, data_base):
        if data_base is not None and ctx.triggered_id == 'btn_recon_agua':
            df_mediciones_all = pd.DataFrame(data_base).sort_values('id_flujo').iloc[0:68, :]
            error = pd.DataFrame(df_mediciones_all['Tolerancia']).astype(float) / 100
            df_mediciones_all['id_flujo'] = pd.to_numeric(df_mediciones_all['id_flujo'], errors='coerce')
            df_mediciones_all.sort_values('id_flujo', inplace=True)
            mediciones = pd.DataFrame(data_base).sort_values('id_flujo').iloc[:, 3].to_numpy()

            resultados, des_recon, des_ini = balance_core_agua(mediciones, error)
            des_ini.rename(columns={0: 'Area', 'Desbalance masa': 'Desbalance masa_Ini'}, inplace=True)
            des_recon.rename(columns={0: 'Area'}, inplace=True)
            df_des = des_ini.merge(des_recon, how='left', on='Area')

            df_mediciones_all.rename(columns={'Flujo': 'Masa Medida', 'nombre_flujo': 'Flujo', 'codigo_flujo': 'Codigo'}, inplace=True)
            df_out = resultados.merge(df_mediciones_all, how='left', on='Flujo')
            df_out = df_out[['Codigo', 'Flujo', 'Masa Medida', 'Masa recon', 'Tolerancia']]
            df_out['Diferencia'] = df_out['Masa Medida'] - df_out['Masa recon']
            df_out['Porcentaje Ajuste'] = df_out['Diferencia'] / df_out['Masa Medida'] * 100

            return df_out.round(4).to_dict('records'), df_des.round(4).to_dict('records')
        else:
            return [], []

    # === DESCARGAR EXCEL ===
    @callback(
        Output("descargar_excel_agua", "data"),
        Input("btn_recon_csv_agua", "n_clicks"),
        State("recon_resultados_agua", "rowData"),
        prevent_initial_call=True
    )
    def generar_excel_agua(n_clicks, rec_caso):
        if not rec_caso:
            print("⚠️ No hay datos en rowData")
            return False

        df_rec = pd.DataFrame(rec_caso)
        print("📥 Generando Excel...")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_rec.to_excel(writer, index=False, sheet_name="Datos")
        buffer.seek(0)

        return dcc.send_bytes(buffer.read(), filename="reconciliacion_agua.xlsx")

    # === EXPORT CSV ===
    @callback(
        Output("input_mina2_agua", "exportDataAsCsv"),
        Input("btn_recon_csv2_agua", "n_clicks"),
    )
    def export_data_as_csv_agua(n_clicks):
        if n_clicks:
            print('Presione boton y retorne True')
            return True
        return False

    # === TAGS UPLOAD ===
    @app.callback(
        Output('data_base_tag_agua', 'rowData'),
        Output('fig_tag_box_agua', 'figure'),
        Output('input_tag_agua', 'rowData'),
        Input('data_tag_upload_agua', 'contents'),
        Input('data_tag_upload_agua', 'filename'),
        Input('fecha_inicio_tag_agua', 'value'),
        Input('fecha_final_tag_agua', 'value'),
        prevent_initial_call=True,
    )
    def recon_get_tag_base_agua(contents, filename, inicio, final):
        if contents is not None:
            inicio_tag = inicio + ' 08:00:00'
            final_tag = final + ' 07:00:00'
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df_tag = pd.read_excel(io.BytesIO(decoded), sheet_name='Tags')

            sql5 = f"""
            SELECT 
                count(Fend) as 'N_hor',
                sum(FIT_61209) as 'FIT_61209s',
                avg(FIT_61209) as 'FIT_61209_avg'
            FROM df_tag
            WHERE Fini >= '{inicio_tag}' AND Fini <= '{final_tag}'
            """
            df_input_tag5 = sqldf(sql5)
            return df_tag.round(4).to_dict('records'), go.Figure(), df_input_tag5.round(4).to_dict('records')
        return None, go.Figure(), None
