"""
schemas.py
Modelos Pydantic para validar peticiones y respuestas de la API.
"""

from pydantic import BaseModel, Field
from typing import Literal


class LoginRequest(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre de pila")
    apellidos: str = Field(..., min_length=1, description="Apellidos")
    proveedor: Literal["groq", "openai", "anthropic", "google_genai"] = "groq"


class LoginResponse(BaseModel):
    thread_id: str
    verificado: bool
    nombre_completo: str | None = None
    mensaje_bienvenida: str


class ChatRequest(BaseModel):
    thread_id: str
    mensaje: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    respuesta: str