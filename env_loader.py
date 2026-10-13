"""Carga centralizada de variables de entorno para este clon de la app."""

from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def load_app_env(*, override: bool = False) -> bool:
    """Carga el .env de la raiz, sin depender del directorio de ejecucion."""
    return load_dotenv(dotenv_path=ENV_FILE, override=override)


def require_app_env(*names: str) -> dict[str, str]:
    """Validate required settings without exposing values in error messages."""
    missing = [name for name in names if not os.getenv(name, "").strip()]
    if missing:
        raise RuntimeError(
            "Faltan variables de configuración requeridas: " + ", ".join(missing)
            + ". Completa el .env de la raíz del proyecto antes de iniciar la app."
        )
    return {name: os.environ[name] for name in names}
