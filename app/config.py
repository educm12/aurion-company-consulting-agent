"""
config.py
Configuración centralizada de rutas y constantes de la aplicación.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "resources" / "aurion.db")

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000

# Local por defecto; en Render se utiliza la variable de entorno.
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    f"http://{BACKEND_HOST}:{BACKEND_PORT}"
).rstrip("/")
