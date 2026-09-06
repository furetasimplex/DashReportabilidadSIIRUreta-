import os

from env_loader import load_app_env

load_app_env()

from main import server

application = server

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8065"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    server.run(host="0.0.0.0", port=port, debug=debug)
