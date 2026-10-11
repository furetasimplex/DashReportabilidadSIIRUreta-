# tabs/tab_import_leyes_granulo.py
from dash import html, dcc, Input, Output, State
import base64, io, pandas as pd
from tabs.procesar_excel_leyes import procesar_excel_leyes

layout = html.Div([
    html.H5("Importar Leyes y Granulometría desde archivo Excel"),
    dcc.Upload(
        id='upload-leyes-granulo',
        children=html.Div(['Arrastra o haz clic para subir el archivo Excel (.xlsx)']),
        style={
            'width': '100%', 'height': '80px', 'lineHeight': '80px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='import-feedback-leyes-granulo')
])

def register_callbacks(app):
    @app.callback(
        Output('import-feedback-leyes-granulo', 'children'),
        Input('upload-leyes-granulo', 'contents'),
        State('upload-leyes-granulo', 'filename')
    )
    def importar_excel(contents, filename):
        if contents is None:
            return ""
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            file_like = io.BytesIO(decoded)
            mensaje = procesar_excel_leyes(file_like, filename)
            return html.Div(f"✅ {mensaje}", style={"color": "green"})
        except Exception as e:
            return html.Div(f"❌ Error: {str(e)}", style={"color": "red"})
