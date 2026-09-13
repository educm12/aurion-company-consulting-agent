"""
chat.py
Endpoint de chat: envía un mensaje al agente y devuelve su respuesta.
"""

from fastapi import APIRouter, HTTPException

from app.backend.schemas import ChatRequest, ChatResponse
from app.backend.services.agent_service import send_message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    try:
        respuesta = await send_message(payload.thread_id, payload.mensaje)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el mensaje: {e}")
    return ChatResponse(respuesta=respuesta)