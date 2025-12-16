import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import base64
import io
from db_connection import get_engine  # Debe retornar un SQLAlchemy Engine

dash.register_page(__name__, path="/importar_rec", name="Importar rec")

layout = html.Div([
    # ------------------ PARÁMETROS ÓXIDOS ------------------
    dbc.Row([dbc.Col([html.H5('Parámetros Óxidos')], width={"size": 4})]),
    dbc.Row([
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_camp_oxido', type='number'),
                                   dbc.Label("Número Campaña")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_oxi_ini', type='number'),
                                   dbc.Label("Parcela Inicio")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_oxi_fin', type='number'),
                                   dbc.Label("Parcela Fin")])], width=1),
    ]),
    dbc.Row([
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_camp_oxido2', type='number'),
                                   dbc.Label("Número Campaña")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_oxi_ini2', type='number'),
                                   dbc.Label("Parcela Inicio")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_oxi_fin2', type='number'),
                                   dbc.Label("Parcela Fin")])], width=1),
    ]),
    # ------------------ PARÁMETROS SULFUROS ------------------
    dbc.Row([dbc.Col([html.H5('Parámetros Sulfuros')], width={"size": 4})]),
    dbc.Row([
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_camp_sulf', type='number'),
                                   dbc.Label("Número Campaña")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_sulf_ini', type='number'),
                                   dbc.Label("Parcela Inicio")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_sulf_fin', type='number'),
                                   dbc.Label("Parcela Fin")])], width=1),
    ]),
    dbc.Row([
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_camp_sulf2', type='number'),
                                   dbc.Label("Número Campaña")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_sulf_ini2', type='number'),
                                   dbc.Label("Parcela Inicio")])], width=1),
        dbc.Col([dbc.FormFloating([dbc.Input(id='id_sulf_fin2', type='number'),
                                   dbc.Label("Parcela Fin")])], width=1),
    ]),
    html.H4("Carga de datos Recuperaciones (rec)"),
    dcc.Upload(
        id='upload-rec',
        #children=html.Div(['Arrastra o selecciona el archivo Excel con hoja Base_Datos']),
        children=html.Div([
                html.I(className="bi bi-file-earmark-arrow-up fs-1 text-primary"),  # ícono Bootstrap
                html.H5("Subir archivo Excel", className="mt-2 mb-1 fw-semibold"),
                html.P(
                    "Arrastra o selecciona un archivo Excel (.xlsx) ",
                ),
                html.H5("'Base_Datos'",className="mt-2 mb-1 fw-semibold")
            ]),
            className=(
                "border-dashed border-primary text-center "
                "py-4 rounded-3 bg-light-subtle"
            ),
            style={
                "cursor": "pointer",
                "transition": "all 0.25s ease-in-out",
                "border":"1px dashed #aaa"
            },
        multiple=False
    ),
    html.Div(id='status-rec', style={'marginTop': 20})
])

def register_callbacks(app):
    @app.callback(
        Output('status-rec', 'children'),
        Input('upload-rec', 'contents'),
        State('upload-rec', 'filename'),
        State('id_camp_oxido', 'value'),
        State('id_oxi_ini', 'value'),
        State('id_oxi_fin', 'value'),
        State('id_camp_oxido2', 'value'),
        State('id_oxi_ini2', 'value'),
        State('id_oxi_fin2', 'value'),
        State('id_camp_sulf', 'value'),
        State('id_sulf_ini', 'value'),
        State('id_sulf_fin', 'value'),
        State('id_camp_sulf2', 'value'),
        State('id_sulf_ini2', 'value'),
        State('id_sulf_fin2', 'value'),
    )
    def tab_recuperacion(contenido, nombre_archivo,
                         camp_ox, ox_ini, ox_fin,
                         camp_ox2, ox_ini2, ox_fin2,
                         camp_su, su_ini, su_fin,
                         camp_su2, su_ini2, su_fin2):
        if contenido is None:
            return dbc.Alert("No se ha cargado ningún archivo.", color="warning")

        try:
            # --- Decodificación del archivo ---
            _, content_string = contenido.split(',')
            decoded = base64.b64decode(content_string)
            excel_data = io.BytesIO(decoded)

            # --- Utilidades ---
            def _build_conditions(df, col, ranges):
                conds, choices = [], []
                for camp, ini, fin in ranges:
                    if camp is None or ini is None or fin is None:
                        continue
                    try:
                        c = int(str(camp).strip())
                        a = int(str(ini).strip())
                        b = int(str(fin).strip())
                    except Exception:
                        continue
                    conds.append((df[col] >= a) & (df[col] <= b))
                    choices.append(c)
                return conds, choices

            # --- Lectura Óxidos ---
            def read_ox(path):
                re = pd.read_excel(path, sheet_name="Recuperaciones Oxidos")
                raw = re.iloc[3:, 1:34]
                headers = raw.iloc[0, :]
                df = raw.iloc[1:, :].copy()
                df.columns = headers
                df = df.melt(id_vars="Parcela")
                df.columns = ["Fecha_drenaje", "Parcela", "Recuperacion_parcela"]

                df["PAD"] = "OXIDO"
                df["pad_id"] = 1
                df["Parcela"] = pd.to_numeric(df["Parcela"], errors="coerce").astype("Int64")
                df = df.dropna(subset=["Parcela"]).copy()
                df["Parcela"] = df["Parcela"].astype(int)
                df["parcela_id"] = df["Parcela"]
                df["Fecha_drenaje"] = pd.to_datetime(df["Fecha_drenaje"], errors="coerce")

                conds, choices = _build_conditions(df, "Parcela",
                                                   [(camp_ox, ox_ini, ox_fin), (camp_ox2, ox_ini2, ox_fin2)])
                df["Campana"] = np.select(conds, choices, default=np.nan)
                df["campaña_id"] = pd.to_numeric(df["Campana"], errors="coerce").astype("Int64")
                return df

            # --- Lectura Sulfuros ---
            def read_sulf(path):
                re = pd.read_excel(path, sheet_name="Recuperaciones Sulfuros")
                raw = re.iloc[2:, 1:31]
                headers = raw.iloc[0, :]
                df = raw.iloc[1:, :].copy()
                df.columns = headers
                df = df.melt(id_vars="Parcela")
                df.columns = ["Fecha_drenaje", "Parcela", "Recuperacion_parcela"]

                df["PAD"] = "SULFUROS"
                df["pad_id"] = 2
                df["Parcela"] = pd.to_numeric(df["Parcela"], errors="coerce").astype("Int64")
                df = df.dropna(subset=["Parcela"]).copy()
                df["Parcela"] = df["Parcela"].astype(int)
                df["parcela_id"] = df["Parcela"] + 32  # ID global
                df["Fecha_drenaje"] = pd.to_datetime(df["Fecha_drenaje"], errors="coerce")

                conds, choices = _build_conditions(df, "Parcela",
                                                   [(camp_su, su_ini, su_fin), (camp_su2, su_ini2, su_fin2)])
                df["Campana"] = np.select(conds, choices, default=np.nan)
                df["campaña_id"] = pd.to_numeric(df["Campana"], errors="coerce").astype("Int64")
                return df

            # --- Procesamiento ---
            df_s = read_sulf(excel_data)
            df_o = read_ox(excel_data)
            df = pd.concat([df_s, df_o], ignore_index=True)

            cols = ["Fecha_drenaje", "PAD", "pad_id", "Parcela", "parcela_id",
                    "Campana", "campaña_id", "Recuperacion_parcela"]
            df = df[[c for c in cols if c in df.columns]]

            # --- Persistencia en BD ---
            engine = get_engine()
            with engine.begin() as conn:
                df.to_sql("Recuperaciones_pad", con=conn,schema="inventar_SpcHidr", if_exists="append", index=False,
                          method="multi", chunksize=20)

            return dbc.Alert(
                f"Archivo '{nombre_archivo}' cargado correctamente. Registros cargados: {len(df)}",
                color="success"
            )

        except Exception as e:
            return dbc.Alert(f"Error: {e}", color="danger")
