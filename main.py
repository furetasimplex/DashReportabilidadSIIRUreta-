# main.py
from dash import Dash
import dash_bootstrap_components as dbc
from layout import create_layout, register_callbacks
from dotenv import load_dotenv

load_dotenv()

external_stylesheets = [
    dbc.themes.FLATLY,  # o SANDSTONE, LUX, QUARTZ, CERULEAN, etc.
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
]

app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard Hidro"

app.layout = create_layout(app)
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8065)
