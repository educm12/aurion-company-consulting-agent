"""
streamlit_app.py
Interfaz web del chatbot: pantalla de login + chat.
"""

import sys
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import BACKEND_URL

st.set_page_config(page_title="Asistente Aurion Consulting", page_icon="💬")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
    st.session_state.verificado = False
    st.session_state.nombre_completo = None
    st.session_state.messages = []
    

PROVEEDORES = {
    "Groq (gpt-oss-120b)": "groq",
    "OpenAI (gpt-4o-mini)": "openai",
    "Anthropic (Claude Haiku)": "anthropic",
    "Google (Gemini 3.0 Flash)": "google_genai",
}

def hacer_login(nombre: str, apellidos: str, proveedor: str):
    resp = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"nombre": nombre, "apellidos": apellidos, "proveedor": proveedor},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    st.session_state.thread_id = data["thread_id"]
    st.session_state.verificado = data["verificado"]
    st.session_state.nombre_completo = data["nombre_completo"]
    st.session_state.messages = [{"role": "assistant", "content": data["mensaje_bienvenida"]}]
    

def enviar_mensaje(mensaje: str) -> str:
    resp = requests.post(
        f"{BACKEND_URL}/chat",
        json={"thread_id": st.session_state.thread_id, "mensaje": mensaje},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["respuesta"]

def cerrar_sesion():
    """Resetea el estado local de Streamlit. La sesión del agente en el
    backend (thread_id) simplemente deja de usarse -- no hace falta
    borrarla explícitamente, el checkpointer la conserva por si se
    quisiera retomar, pero el frontend ya no la referencia."""
    st.session_state.thread_id = None
    st.session_state.verificado = False
    st.session_state.nombre_completo = None
    st.session_state.messages = []


if st.session_state.thread_id is None:
    st.title("Asistente Aurion Consulting")
    st.write("Introduce tu nombre y apellidos para empezar.")

    with st.form("login_form"):
        nombre = st.text_input("Nombre")
        apellidos = st.text_input("Apellidos")
        proveedor_label = st.selectbox("Modelo a utilizar", list(PROVEEDORES.keys()))
        enviado = st.form_submit_button("Entrar")

    if enviado:
        if not nombre.strip() or not apellidos.strip():
            st.error("Por favor, rellena ambos campos.")
        else:
            with st.spinner("Verificando..."):
                hacer_login(nombre, apellidos, PROVEEDORES[proveedor_label])
            st.rerun()
            
else:
    col_titulo, col_salir = st.columns([5, 1])

    with col_titulo:
        estado = "Empleado verificado ✅" if st.session_state.verificado else "Usuario externo 🌐"
        st.caption(f"{estado} — {st.session_state.nombre_completo or 'Invitado'}")
        st.title("Asistente Aurion Consulting")

    with col_salir:
        st.write("")  # pequeño espaciador para alinear verticalmente el botón
        if st.button("Cerrar sesión"):
            cerrar_sesion()
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pregunta = st.chat_input("Escribe tu pregunta...")
    if pregunta:
        st.session_state.messages.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                respuesta = enviar_mensaje(pregunta)
            st.markdown(respuesta)

        st.session_state.messages.append({"role": "assistant", "content": respuesta})