"""Carga centralizada de variables de entorno para este clon de la app."""

from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def load_app_env(*, override: bool = False) -> bool:
    """Carga el .env de la raiz, sin depender del directorio de ejecucion."""
    return load_dotenv(dotenv_path=ENV_FILE, override=override)
