

from dash.dependencies import Input, Output, State
from dash import callback, ctx
from itertools import product
import base64
import io
import os 
from flask import app
import plotly.graph_objs as go
import plotly_express as px
#from app import app
from tabs.utilsHidro.utils_dash import get_fig_bal_casos_hidro, get_data_save_tags_hidro,  get_agua_his_casos_hidro,get_data_publica_casos_hidro, get_data_agua_casos_hidro,get_data_save_casos_hidro,  carta_control_hidro, parse_contents_hidro, local_img_to_html_hidro
from tabs.utilsHidro.utils_recon import balance_core_hidro
#from db import get_tags_min
import datetime
import numpy as np
import pandas as pd
from pandasql import sqldf
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dash import Dash
from dash import dcc


#from utils import 

project_folder = os.path.dirname(os.path.realpath(__file__))  # path de este archivo
assets_folder = os.path.join(project_folder, 'assets')

def register_apphidro_callbacks(app):
    @app.callback(
        Output('imagen_balance', 'src'),
        Input('agg-tab2', 'value'),           # RadioButton que cambia la imagen
        Input('id_caso_activo', 'value'),     # Cambio de caso    
        prevent_initial_call=True
    )
    def actualizar_imagen_hidro(agg_tab2, maxid):
        
        # Usa solo el ID del caso actual
        imagen = get_fig_bal_casos_hidro(maxid, agg_tab2)
        return imagen

    @app.callback(
        Output('data_casos2', 'rowData'),
        Output('data_hcas2', 'rowData'),
        Output("id_caso_activo", "value"),
        Input('btn-get-casos', 'n_clicks'),
        Input('fecha_inicio_caso','value'),
        Input('fecha_final_caso','value'),
        Input('crea-caso','value'),
        prevent_initial_call=True,
    )
    def get_data_casos_hidro(n_clicks, inicio, final,  crea_caso):
    
        if not n_clicks:
            return [], [],None
        if ctx.triggered_id == 'btn-get-casos':
            
            
            inicio_tag = inicio + ' 08:00' #'2024-11-20 08:00'
            final_tag  = final  + ' 07:00' #'2024-11-20 07:00'
            #print(crea_caso)
            if crea_caso==['Si']:
                valor_crea='Si'
            else:
                valor_crea='No'

            print('inicio:', inicio_tag)
            print('final:', final_tag)
            print(valor_crea)
            df_mina = df = get_data_agua_casos_hidro(inicio, final, valor_crea)
            maxid=df_mina["caso_id"].max()


            #df_mina.rename(columns={'0':'Id_caso', '1':'fecha', '2':'observaciones', '3':'modelo', '4':'fecha_ini', '5':'nombre_caso' }, inplace=True)
            #print(df_mina )
            df_hcasos =  get_agua_his_casos_hidro(final)
            #print(df_hcasos)

            #fig_bal = get_fig_bal_casos(final)

            return  df_mina.to_dict('records'), df_hcasos.to_dict('records'),maxid
            #return  df_mina.round(4).to_dict('records'),  fig_bal,  df_hcasos.round(4).to_dict('records')
        #return  df_mina.round(4).to_dict('records'),  fig_bal,  df_hcasos.round(4).to_dict('records')
        
    @app.callback(
        Input('btn-save-casos', 'n_clicks'),
        Input('data_casos2','rowData'),
        Input('fecha_final_caso','value'),
        Input('id_caso_activo','value'),

    )
    def get_data_casos_hidro(n_clicks,  dat_casos, final, maxcas):

        if ctx.triggered_id == 'btn-save-casos':
            print('Actualizando datos')
            
            #print(dat_casos)
            get_data_save_casos(dat_casos, final,maxcas)
            
            #print(df_mina )
            return    


    @app.callback(
        Input('btn-publica-casos', 'n_clicks'),
        Input('recon-resultados','rowData'),
        Input('data_casos2','rowData'),
        Input('id_caso_activo','value'),

    )
    def get_publica_casos_hidro(n_clicks,  rec_caso, data_casos2, maxcas):

        if ctx.triggered_id == 'btn-publica-casos':
            print('Publicando datos')
            
            print(data_casos2)
            get_data_publica_casos(data_casos2, rec_caso, maxcas)
            
            #print(df_mina )
            return    


    # grabar tag

    @app.callback(
        Input('btn-save-tag', 'n_clicks'),
        Input('data-base-tag','rowData'),
        Input('fecha_inicio_tag','value'),
        Input('fecha_final_tag','value'),
    )
    def get_publica_tags_hidro(n_clicks,  rec_tags, inicio ,final):

        inicio_tag = inicio + ' 08:00:00' #'2024-11-20 08:00:00'
        final_tag  = final  + ' 07:00:01' #'2024-11-20 07:00:01'
        if ctx.triggered_id == 'btn-save-tag':
            print('Publicando tags')
            
            get_data_save_tags_hidro(inicio_tag, final_tag, rec_tags)
            
            #print(df_mina )
            return   

    # Calbacks reconciliador

    @app.callback(
        Output('recon-data-base', 'rowData'),
        Input('data-base-upload','contents'),
        Input('data-base-upload','filename'),
        prevent_initial_call=True,
    )
    def recon_get_data_base_hidro(contents, filename):
        if contents is not None:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df_data_base   = pd.read_excel( io.BytesIO(decoded), sheet_name='Datos bases' )
        

            return df_data_base.round(4).to_dict('records')


    @app.callback(
        Output('recon-resultados', 'rowData'),
        Output('recon-desbalances','rowData'),
        Input('btn-recon', 'n_clicks'),
        Input('recon-data-base','rowData'),
        #Input('recon-tolerancias', 'rowData'),
        #Input('recon-elementos','value'), 
        #prevent_initial_call=True,
    )
    def get_recon_hidro(n_clicks, data_base):

        #print(componentes)

        if data_base is not None  and ctx.triggered_id == 'btn-recon':
            # print('#####################')
            # print(type(componentes))
            #print(data_base)

            #componentes = ['Cu', 'Mo'] #Lista obtenida por pantalla de selección de items en Dash
            lista_rows = []
            lista_columns = []
            lista_data = []

            #mediciones = pd.read_excel(path, sheet_name="Datos bases", skiprows=0).iloc[0:39,:]
            df_mediciones_all = pd.DataFrame(data_base).sort_values('id_flujo').iloc[0:68,:] 
            #print(df_mediciones_all)
            error = pd.DataFrame(df_mediciones_all['Tolerancia']).astype(float)/100 
            #print(error)
            df_mediciones_all['id_flujo'] = pd.to_numeric( df_mediciones_all['id_flujo'], errors='coerce' )
            df_mediciones_all.sort_values('id_flujo', inplace=True)
            #print(df_mediciones_all)
            #columnas_componentes = ['FLujo']
            #print(columnas_componentes)
            mediciones= pd.DataFrame(data_base).sort_values('id_flujo').iloc[:,3].to_numpy()
            #print(mediciones)


            #Ejecutar Reconciliador
            resultados, des_recon,des_ini = balance_core(mediciones,error)

            des_ini.rename(columns={0:'Area', 'Desbalance masa':'Desbalance masa_Ini'}, inplace=True)
            des_recon.rename(columns={0:'Area'}, inplace=True)
            df_des = des_ini.merge(des_recon, how='left', on='Area') 
            

            #Consolidar resultado con datos iniciales para comparar
            df_mediciones_all.rename(columns={'Flujo':'Masa Medida','nombre_flujo':'Flujo', 'codigo_flujo':'Codigo'  }, inplace=True)
            
            #out_cols_1 = [f'Ley {elemento} Medida' for elemento in componentes]
            #out_cols_2 = [f'Ley {elemento} recon'  for elemento in componentes]

            df_out = resultados.merge(df_mediciones_all, how='left', on='Flujo')
            print(df_out)
            df_out = df_out[['Codigo','Flujo', 'Masa Medida', 'Masa recon','Tolerancia']]

            df_out['Diferencia'] = df_out['Masa Medida']-df_out['Masa recon']
            df_out['Porcentaje Ajuste'] = df_out['Diferencia']/df_out['Masa Medida']*100



            print(resultados.head())

            return df_out.round(4).to_dict('records'), df_des.round(4).to_dict('records')
        
        else:
            return [] , []


    @callback(
        Output("descargar-excel", "data"),
        Input("btn-recon-csv", "n_clicks"),
        State("recon-resultados", "rowData"),
        prevent_initial_call=True
    )
    def generar_excel_hidro(n_clicks, rec_caso):
        if not rec_caso:
            print("⚠️ No hay datos en rowData")
            return False

        df_rec = pd.DataFrame(rec_caso)
        print("📥 Generando Excel...")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_rec.to_excel(writer, index=False, sheet_name="Datos")
        buffer.seek(0)

        return dcc.send_bytes(buffer.read(), filename="reconciliacion.xlsx")


    @callback(
        Output("input_mina2", "exportDataAsCsv"),
        Input("btn-recon-csv2", "n_clicks"),
    )
    def export_data_as_csv_hidro(n_clicks):
        if n_clicks:
            print('Presione boton y retorne True')
            return True
        return False

    @app.callback(
        Output('data-base-tag', 'rowData'),
        Output('fig_tag_box', 'figure'),
        Output('input_tag', 'rowData'),
        Input('data-tag-upload','contents'),
        Input('data-tag-upload','filename'),
        Input('fecha_inicio_tag','value'),
        Input('fecha_final_tag','value'),
        prevent_initial_call=True,
    )
    def recon_get_tag_base_hidro(contents, filename, inicio, final):
        if contents is not None:
            inicio_tag = inicio + ' 08:00:00' #'2024-11-20 08:00:00'
            final_tag  = final  + ' 07:00:00' #'2024-11-20 07:00:00'
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            df_tag = pd.read_excel( io.BytesIO(decoded), sheet_name='Tags' )
            print(df_tag)

            sql5="""
            SELECT 
            count(Fend) as 'N_hor',
            sum(FIT_61209) as 'FIT_61209s',
            sum(FIT_61209)/count(Fend) as 'FIT_61209av1',
            avg(FIT_61209) as 'FIT_61209savg',
            sum(FIT_61206) as 'FIT_61206s',
            sum(FIT25104) as 'FIT25104s',
            sum(WI_01769) as 'WI_01769s',
            sum(WI_01769_DACA) as 'WI_01769_DACAs',
            sum(LI_12655A) as 'LI_12655As',
            sum(LI_12655B) as 'LI_12655Bs',
            sum(LI_06730A) as 'LI_06730As',
            sum(LI_06730B) as 'LI_06730Bs',
            sum(FIT_00101) as 'FIT_00101s',
            sum(FIT_06441) as 'FIT_06441s',
            sum(FIT_06451) as 'FIT_06451s',
            sum(FIT_06511) as 'FIT_06511s',
            sum(FIT_06521) as 'FIT_06521s',
            sum(DIT_06440) as 'DIT_06440s',
            sum(DIT_06450) as 'DIT_06450s',
            sum(DIT_06510) as 'DIT_06510s',
            sum(DIT_06520) as 'DIT_06520s',
            sum(DIC_06440) as 'DIC_06440s',
            sum(DIC_06450) as 'DIC_06450s',
            sum(DIC_06510) as 'DIC_06510s', 
            sum(DIC_06520) as 'DIC_06520s', 
            sum(FI_19705) as 'FI_19705s',
            sum(FI_19509) as 'FI_19509s',
            sum(FI_19750) as 'FI_19750s',
            sum(FIC_03802) as 'FIC_03802s',
            sum(FIC_03812) as 'FIC_03812s', 
            sum(FIC_03822) as 'FIC_03822s', 
            sum(FIC_03832) as 'FIC_03832s', 
            sum(FIC_03842) as 'FIC_03842s', 
            sum(FIC_04050) as 'FIC_04050s', 
            sum(FIT251041) as 'FIT251041s', 
            sum(FIT_001011) as 'FIT_001011s',   
            sum(FI_195091) as 'FI_195091s', 
            sum(PI_06761) as 'PI_06761s',   
            sum(PI_06771) as 'PI_06771s',   
            sum(PI_06781) as 'PI_06781s',   
            sum(PI_06791) as 'PI_06791s',   
            sum(PI_06801) as 'PI_06801s',       
            sum(FFIC_01820) as 'FFIC_01820s',   
            sum(FI_12734) as 'FI_12734s'
            FROM
            df_tag
            WHERE
            Fini >=  ' """+ inicio_tag +"""'  AND  Fini <='"""+ final_tag +"""' 
            """
            print(sql5)

            df_input_tag5= sqldf(sql5)
            print(df_input_tag5)
            #Flujo 37 F000/F100 ingreso a modelo

            #df__input_mina11 = df_input_mina1 + df_input_mina2 + df_input_mina3 + df_input_mina5 

            #df__input_mina11["Hum"]=((df__input_mina11["TMH"]-df__input_mina11["TMS"])/df__input_mina11["TMH"])*100
            #df__input_mina11["CuT"]=(df__input_mina11["TMFCuT"]/df__input_mina11["TMS"])*100
            #df__input_mina11["Mo"]=(df__input_mina11["TMFMo"]/df__input_mina11["TMS"])*100
            #para FE
            #df__input_mina11[6]=(df__input_mina11[8]/df__input_mina11[2]*100)

            #df_input_mina= pd.concat([df__input_mina11, df_input_mina1, df_input_mina2, df_input_mina3, df_input_mina4, df_input_mina5], ignore_index=True)
            #print(df_input_mina)
                #print(box_x)
            #box_x = 'MATERIAL_BLOQUE' 
            #box_y = 'TMH_ORIGINALES'

            #fig_minestar_box1 = px.box(df_minestar , x=box_x, y=box_y)
            #print(fig_minestar_box1)
            #return  df_tag.round(4).to_dict('records'), fig_minestar_box1, df_input_mina.round(4).to_dict('records')
            return  df_tag.round(4).to_dict('records'), None, df_input_tag5.round(4).to_dict('records')
        return None, go.Figure(), None

        
    """ @app.callback(
        #Output('data-minestar','rowData'),
        Output('fig-minestar', 'figure'),
        Output('fig-minestar-box', 'figure'),
        Input('data-base-minestar', 'data'),
        Input('box-x-minestar','value')
    )
    def plot_data(data, box_x):

        if data is not None:

            df_mina = pd.DataFrame( data )

            df_mina_turno = df_mina.groupby(['Fecha'])['Payload', 'Camiones_TMS','Camiones_Cu fino_Ley Mina', 'Camiones_Mo fino_Ley Mina','Camiones_Fe fino_Ley Mina'].sum().reset_index()

            df_mina_turno['Camiones_Cu%_MinaP11'] = 100*  df_mina_turno['Camiones_Cu fino_Ley Mina'] / df_mina_turno['Camiones_TMS']
            df_mina_turno['Camiones_Mo%_MinaP11'] = 100*  df_mina_turno['Camiones_Mo fino_Ley Mina'] / df_mina_turno['Camiones_TMS']
            df_mina_turno['Camiones_Fe%_MinaP11'] = 100*  df_mina_turno['Camiones_Fe fino_Ley Mina'] / df_mina_turno['Camiones_TMS']

                #print( df_mina_turno.head() )

                #Esto realizarlo de la data final, pues son variables que se deben ingresar 
                # camiones_masa_total = df_mina_turno['Payload'].sum()
                # camiones_masa_tms = df_mina_turno['Camiones_TMS'].sum()
                # camiones_masa_cu  = df_mina_turno['Camiones_Cu fino_Ley Mina'].sum()
                # camiones_ley_cu   = 100*camiones_masa_cu/camiones_masa_tms

            fig_control = carta_control(df_mina, x_col="Fin Descarga", y_col="Payload", N=3, metodo='STD', titulo="Payload Camiones a Chancado", destacar_outliers=True)

            #print(box_x)
            if box_x is None:
                box_x = 'Equipo de Transporte' 
                
            box_y = 'Payload'

            fig_box = px.box( df_mina , x=box_x, y=box_y)

            return  df_mina_turno.round(4).to_dict('records'), fig_control, fig_box
        
        return None, go.Figure(), go.Figure() """

    """ @callback(
        Output("recon-resultados", "exportDataAsCsv"),
        Input("btn-minestar-csv", "n_clicks"),
    )
    def export_data_as_csv(n_clicks):
        if n_clicks:
            print('Presione boton y retorne True')
            return True
        return False """

    #data-mina

    #Fecha	Payload	Camiones_TMS	Camiones_Cu fino_Ley Mina	Camiones_Mo fino_Ley Mina	Camiones_Fe fino_Ley Mina	
    #Camiones_Cu%_MinaP11	Camiones_Mo%_MinaP11	Camiones_Fe%_MinaP11

    # @app.callback(
    #     Output('btn-save-msg', 'children'),
    #     Input('btn-save-data-mina', 'n_clicks'),
    #     Input('store-data-mina', 'data'),
    #     State('data-mina','rowData'),
    # )
    # def guardar_plan(n_clicks, data):

    #     if ctx.triggered_id == 'btn-save-plan':

    #         df_plan = pd.DataFrame( data )
    #         df_plan.to_excel( os.path.join( assets_folder, "data-plan.xlsx" ) , index=False )

    #         return  "Datos Guardados"

    #     return ""

