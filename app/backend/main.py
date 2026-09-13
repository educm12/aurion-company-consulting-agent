"""
main.py
Punto de entrada de la API de Aurion Consulting (FastAPI).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.routers import auth, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Los agentes ya no se construyen aquí: cada proveedor (Groq, OpenAI,
    # Anthropic, Gemini) se construye la primera vez que un usuario lo
    # elige en el login, y se cachea en agent_service para reutilizarlo.
    yield


app = FastAPI(title="Aurion Consulting Chatbot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo local; restringir en producción
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}