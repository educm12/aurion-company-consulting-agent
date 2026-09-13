"""
auth.py
Endpoint de login: verifica al usuario y crea su sesión de chat.
"""

from fastapi import APIRouter

from app.backend.schemas import LoginRequest, LoginResponse
from app.backend.services.agent_service import login_and_create_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    thread_id, verificado, nombre_completo, mensaje_bienvenida = await login_and_create_session(
        payload.nombre, payload.apellidos, payload.proveedor
    )
    return LoginResponse(
        thread_id=thread_id,
        verificado=verificado,
        nombre_completo=nombre_completo,
        mensaje_bienvenida=mensaje_bienvenida,
    )