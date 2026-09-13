"""
agent_service.py
Gestiona un agente por proveedor de LLM (construido de forma perezosa
y cacheado), y recuerda qué proveedor eligió cada sesión de chat.
"""

import uuid

from src.agent.agent import build_agent

_agents: dict[str, object] = {}          # provider -> agente compilado
_thread_provider: dict[str, str] = {}     # thread_id -> provider usado


async def get_or_build_agent(provider: str):
    if provider not in _agents:
        _agents[provider] = await build_agent(provider)
    return _agents[provider]


async def login_and_create_session(nombre: str, apellidos: str, provider: str):
    agent = await get_or_build_agent(provider)

    thread_id = str(uuid.uuid4())
    _thread_provider[thread_id] = provider
    config = {"configurable": {"thread_id": thread_id}}

    mensaje_inicial = f"Hola, soy {nombre} {apellidos}."
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": mensaje_inicial}]},
        config=config,
    )
    mensaje_bienvenida = result["messages"][-1].content

    state = await agent.aget_state(config)
    verificado = state.values.get("verificado", False)
    nombre_completo = state.values.get("nombre_completo")

    return thread_id, verificado, nombre_completo, mensaje_bienvenida


async def send_message(thread_id: str, mensaje: str) -> str:
    provider = _thread_provider.get(thread_id, "groq")
    agent = await get_or_build_agent(provider)
    config = {"configurable": {"thread_id": thread_id}}

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": mensaje}]},
        config=config,
    )
    return result["messages"][-1].content