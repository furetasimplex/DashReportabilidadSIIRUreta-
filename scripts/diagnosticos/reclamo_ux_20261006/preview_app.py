"""Local visual preview of the Reclamo panel without the site auth shell."""
from pathlib import Path
import sys
from dash import Dash

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import panel

app = Dash(__name__, suppress_callback_exceptions=True)
app.layout = panel.layout()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8099, debug=False)
