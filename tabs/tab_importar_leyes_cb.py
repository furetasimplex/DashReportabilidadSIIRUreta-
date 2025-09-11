# callbacks/tab_importar_leyes_cb.py
from dash.dependencies import Input, Output, State
from dash import callback_context
from dash import dcc, html
import base64
import io
import pandas as pd
from procesar_excel_leyes import procesar_excel_leyes

def register_tab_importar_leyes_callbacks(app):
    @app.callback(
        Output('import-feedback', 'children'),
        Input('upload-leyes-excel', 'contents'),
        State('upload-leyes-excel', 'filename')
    )
    def importar_leyes(contents, filename):
        if contents is None:
            return ""
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            archivo_excel = io.BytesIO(decoded)
            mensaje = procesar_excel_leyes(archivo_excel, filename)
            return html.Div([html.P(mensaje, style={'color': 'green'})])
        except Exception as e:
            return html.Div([html.P(f"Error: {str(e)}", style={'color': 'red'})])
