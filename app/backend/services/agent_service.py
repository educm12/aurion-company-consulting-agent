"""
agent_service.py
Gestiona un agente por proveedor de LLM y expone login/chat, ahora con
caché semántica delante de send_message(). El login no se cachea (la
verificación de identidad debe ejecutarse siempre); solo se cachea la
respuesta a mensajes de chat posteriores, con scope por identidad para
no filtrar respuestas entre usuarios.
"""

import time
import uuid

from src.agent.agent import build_agent
from src.cache.config import CACHE_ENABLED
from src.cache.metrics import get_metrics
from src.cache.semantic_cache import build_scope, lookup, store
from src.agent.agent import _subagent_capture
from src.cache.config import CACHE_TTL_PERSONAL_SECONDS, CACHE_TTL_POLICY_SECONDS


_agents: dict[str, object] = {}
_thread_provider: dict[str, str] = {}
_thread_identity: dict[str, tuple[bool, int | None]] = {}  # thread_id -> (verificado, empleado_id)

SQL_TOOL_NAMES = {"read_query", "list_tables", "describe_table", "calculate_risk_leaving", "calculate_risk_leaving_all"}


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
    empleado_id = state.values.get("empleado_id")

    _thread_identity[thread_id] = (verificado, empleado_id)

    return thread_id, verificado, nombre_completo, mensaje_bienvenida


def _classify_and_scope(nested_calls, verificado, empleado_id) -> tuple[str, str, int]:
    """Decide con qué scope, categoría y TTL guardar esta respuesta,
    según si se usaron tools SQL (personal) o no (política, compartible)."""
    used_sql = any(
        tc.get("name") in SQL_TOOL_NAMES
        for _, messages in nested_calls
        for msg in messages
        for tc in (getattr(msg, "tool_calls", None) or [])
    )

    if used_sql:
        scope = build_scope(empleado_id, verificado)
        return scope, "personal", CACHE_TTL_PERSONAL_SECONDS
    else:
        return "public", "policy", CACHE_TTL_POLICY_SECONDS


async def send_message(thread_id: str, mensaje: str) -> str:
    provider = _thread_provider.get(thread_id, "groq")
    verificado, empleado_id = _thread_identity.get(thread_id, (False, None))
    metrics = get_metrics()

    # Para el LOOKUP probamos primero el scope individual (si aplica) y,
    # si no hay hit ahí, probamos también "public" -- una pregunta de
    # política pudo haber sido cacheada como "public" por otro usuario.
    scopes_to_check = [build_scope(empleado_id, verificado), "public"]

    if CACHE_ENABLED:
        for scope in scopes_to_check:
            cache_result = lookup(mensaje, scope=scope)
            if cache_result.hit:
                metrics.record_hit(cache_result.latency_ms)
                print(f"[CACHE HIT] scope={scope} similarity={cache_result.similarity_score}")
                return cache_result.answer

    start = time.perf_counter()
    agent = await get_or_build_agent(provider)
    config = {"configurable": {"thread_id": thread_id}}

    capture: list = []
    token = _subagent_capture.set(capture)
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": mensaje}]},
            config=config,
        )
    finally:
        _subagent_capture.reset(token)

    answer = result["messages"][-1].content
    latency_ms = (time.perf_counter() - start) * 1000

    if CACHE_ENABLED:
        metrics.record_miss(latency_ms)
        scope, category, ttl = _classify_and_scope(capture, verificado, empleado_id)
        store(mensaje, answer, scope=scope, category=category, ttl=ttl)
        print(f"[CACHE MISS] scope={scope} category={category} ttl={ttl}s latency={latency_ms:.1f}ms")

    return answer