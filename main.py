
"""
main.py
Ejecuta backend (FastAPI/Uvicorn) y frontend (Streamlit)
simultáneamente, esperando a que el backend esté disponible.
"""

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)

BACKEND_URL = "http://127.0.0.1:8000/docs"
BACKEND_TIMEOUT = 120  # Tiempo máximo de espera en segundos
CHECK_INTERVAL = 1     # Intervalo entre comprobaciones

processes = []


def start_backend():
    """Inicia el servidor FastAPI con Uvicorn."""
    print("🚀 Iniciando backend FastAPI en http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.backend.main:app",
            "--reload",
            "--port",
            "8000",
        ],
        cwd=str(PROJECT_ROOT),
    )

    processes.append(proc)
    return proc


def wait_for_backend(proc):
    """Espera hasta que FastAPI responda o se agote el tiempo."""
    print("⏳ Esperando a que el backend esté disponible...")

    deadline = time.monotonic() + BACKEND_TIMEOUT

    while time.monotonic() < deadline:
        # Comprobar si el proceso principal de Uvicorn ha terminado.
        if proc.poll() is not None:
            raise RuntimeError(
                f"El proceso de Uvicorn terminó con código {proc.returncode}. "
                "Revisa los errores del backend."
            )

        try:
            with urllib.request.urlopen(
                BACKEND_URL,
                timeout=2,
            ) as response:
                if response.status == 200:
                    print("✅ Backend disponible.")
                    return

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ):
            pass

        print("   Backend todavía iniciándose...", flush=True)
        time.sleep(CHECK_INTERVAL)

    raise TimeoutError(
        f"El backend no respondió en {BACKEND_TIMEOUT} segundos. "
        "No se iniciará Streamlit."
    )


def start_frontend():
    """Inicia la aplicación Streamlit."""
    print("🎨 Iniciando frontend Streamlit en http://localhost:8501")

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/frontend/streamlit_app.py",
            "--server.headless",
            "false",
        ],
        cwd=str(PROJECT_ROOT),
    )

    processes.append(proc)
    return proc


def cleanup(signum=None, frame=None):
    """Detiene todos los procesos al salir."""
    print("\n🛑 Deteniendo servicios...")

    for p in processes:
        if p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
            except Exception as exc:
                print(f"Error al detener un proceso: {exc}")

    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, cleanup)

    try:
        # 1. Iniciar backend.
        backend = start_backend()

        # 2. Esperar a que FastAPI responda.
        wait_for_backend(backend)

        # 3. Iniciar frontend únicamente cuando esté disponible.
        frontend = start_frontend()

        print(
            "\n✅ Backend y frontend iniciados. "
            "Presiona Ctrl+C para detenerlos.\n"
        )

        # 4. Mantener ambos procesos activos.
        while True:
            time.sleep(1)

            if backend.poll() is not None:
                print("\n⚠️ El backend se ha detenido.")
                break

            if frontend.poll() is not None:
                print("\n⚠️ El frontend se ha detenido.")
                break

    except (KeyboardInterrupt, RuntimeError, TimeoutError) as exc:
        if not isinstance(exc, KeyboardInterrupt):
            print(f"\n❌ {exc}")

    finally:
        cleanup()


if __name__ == "__main__":
    main()
