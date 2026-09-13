"""
config.py
Configuración centralizada de rutas y constantes de la aplicación.
Las rutas son relativas a la raíz del proyecto (donde también vive src/
y resources/), asumiendo que uvicorn/streamlit se lanzan desde ahí.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "resources" / "aurion.db")

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"