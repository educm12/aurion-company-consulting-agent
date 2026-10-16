"""
agent.py
Arquitectura multi-agente de Aurion Consulting:

  - subagente_empresa: SQL + riesgo de abandono + política de empresa (RAG).
    Solo accesible si el usuario está verificado como empleado.
  - subagente_web: búsqueda en internet.
    Accesible siempre (empleados y usuarios externos).
  - agente orquestador: pide nombre y apellidos, verifica al usuario y
    decide, mediante middleware, a qué subagentes puede recurrir.
"""

import os
from typing import Callable

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    dynamic_prompt,
    wrap_model_call,
)
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from src.agent.tools import (
    EmployeeState,
    calculate_risk_leaving,
    calculate_risk_leaving_all,
    get_policy_tool,
    get_sqlite_mcp_tools,
    verificar_empleado,
    web_search,
)

import contextvars

load_dotenv()


# Modelo por defecto para cada proveedor. Puedes ajustar estos nombres
# cuando quieras probar otro modelo concreto de cada proveedor.
PROVIDER_DEFAULTS = {
    "groq": "openai/gpt-oss-120b",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "google_genai": "gemini-3.0-flash",
}


def get_llm(provider: str = "groq"):
    if provider not in PROVIDER_DEFAULTS:
        raise ValueError(f"Proveedor no soportado: {provider}")
    model_name = PROVIDER_DEFAULTS[provider]
    return init_chat_model(model_name, model_provider=provider, temperature=0)


# Permite capturar, de forma opcional, los mensajes internos de los
# subagentes cuando algo externo (p.ej. el runner de evaluación) lo
# solicita. Si nadie lo activa (valor por defecto None), no cambia nada
# del comportamiento normal del chatbot.
_subagent_capture: contextvars.ContextVar[list | None] = contextvars.ContextVar(
    "_subagent_capture", default=None
)


# ---------------------------------------------------------------------------
# 1. Subagente de empresa (SQL + riesgo de abandono + política)
# ---------------------------------------------------------------------------
SUBAGENTE_EMPRESA_PROMPT = """\
Eres un especialista en información interna de Aurion Consulting. Respondes \
preguntas sobre datos de empleados/proyectos y política de empresa Para preguntas \
sobre la política de empresa (dias de vacaciones, teletrabajo, vestimenta, etc), utiliza la tool \
"consultar_politica_empresa". Para preguntas sobre datos de empleados/proyectos usa \
"read_query", "list_tables" o "describe_table". Y para preguntas sobre el riesgo de abandono \
de empleados usa "calculate_risk_leaving" y "calculate_risk_leaving_all". Combina las fuentes \
cuando la pregunta lo requiera. Nunca inventes datos que no vengan de estas tools. \
Responde en español, de forma clara y concisa.
Cuando el usuario te pregunte por un empleado, proyecto, manager, etc., primero verifica que exista en la base de datos \
antes de dar cualquier dato sobre él. Si no existe, informa al usuario de que no hay ningún \
empleado o proyecto con ese nombre y no inventes datos.
Si el usuario pregunta sobre una política de empresa, primero verifica que la política exista en la base de datos vectorial \
antes de dar cualquier dato sobre ella. Si no existe, informa al usuario de que no hay ninguna política con ese \
nombre y no inventes datos.
Si te preguntan por un empleado en concreto y una política de empresa, da la resupesta para ese empleado, \
no des una respuesta genérica sobre la política de empresa. Por ejemplo, si te preguntan \
"¿Puede Lucía Herrero Campos traer a su gato a la oficina?", no respondas con la política de empresa \
sobre mascotas, sino con la respuesta concreta para Lucía Herrero Campos.
"""


async def build_company_subagent(provider: str = "groq"):
    llm = get_llm(provider)

    sqlite_tools_all = await get_sqlite_mcp_tools()
    sqlite_tools = [
        t for t in sqlite_tools_all
        if t.name in {"read_query", "list_tables", "describe_table"}
    ]

    tools = [
        calculate_risk_leaving,
        calculate_risk_leaving_all,
        get_policy_tool(),
        *sqlite_tools,
    ]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=SUBAGENTE_EMPRESA_PROMPT,
    )


# ---------------------------------------------------------------------------
# 2. Subagente de búsqueda web + RAG
# ---------------------------------------------------------------------------
SUBAGENTE_WEB_PROMPT = """\
Eres un especialista en búsqueda de información general en internet. \
Respondes preguntas sobre información laboral en general \
(legislación laboral, normas sociales, datos públicos, etc.), ajena a \
la información interna de Aurion Consulting (datos de empleados, proyectos, \
riesgo de abandono y política interna de empresa). Usa la tool \
"web_search" y cita siempre la fuente (dominio/URL). Responde en español, \
de forma clara y concisa.
"""


async def build_web_subagent(provider: str = "groq"):
    llm = get_llm(provider)
    tools = [web_search]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=SUBAGENTE_WEB_PROMPT,
    )


# ---------------------------------------------------------------------------
# 3. Envoltura de los subagentes como tools del orquestador
# ---------------------------------------------------------------------------
async def build_subagent_tools(provider: str = "groq"):
    company_subagent = await build_company_subagent(provider=provider)
    web_subagent = await build_web_subagent(provider=provider)

    @tool
    async def consultar_informacion_empresa(pregunta: str) -> str:
        """
        Consulta al especialista en información INTERNA de Aurion
        Consulting: Datos de empleados, proyectos, política de empresa
        y riesgo de abandono. Úsala solo si el usuario ha sido verificado
        como empleado.

        Args:
            pregunta: la pregunta del usuario, tal cual, para que el
                especialista decida qué tools internas usar.
        """
        result = await company_subagent.ainvoke(
            {"messages": [{"role": "user", "content": pregunta}]}
        )

        capture = _subagent_capture.get()
        if capture is not None:
            capture.append(("consultar_informacion_empresa", result["messages"]))

        return result["messages"][-1].content

    @tool
    async def buscar_informacion_internet(pregunta: str) -> str:
        """
        Consulta al especialista en búsqueda de información GENERAL en
        internet (legislación, normas del mercado laboral, datos públicos,
        etc.).

        Args:
            pregunta: la pregunta del usuario, tal cual.
        """
        result = await web_subagent.ainvoke(
            {"messages": [{"role": "user", "content": pregunta}]}
        )

        capture = _subagent_capture.get()
        if capture is not None:
            capture.append(("buscar_informacion_internet", result["messages"]))

        return result["messages"][-1].content

    return consultar_informacion_empresa, buscar_informacion_internet


# ---------------------------------------------------------------------------
# 4. Middleware: acceso condicional a subagentes según verificación
# ---------------------------------------------------------------------------
def build_middleware(consultar_informacion_empresa, buscar_informacion_internet):

    @wrap_model_call
    async def dynamic_tool_access(
        request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        """Da acceso al subagente de empresa solo si el usuario está verificado
        como empleado; el subagente web siempre está disponible."""
        verificado = request.state.get("verificado")

        if verificado:
            tools = [
                verificar_empleado,
                consultar_informacion_empresa,
                buscar_informacion_internet,
            ]
        else:
            tools = [
                verificar_empleado,
                buscar_informacion_internet,
            ]

        request = request.override(tools=tools)
        return await handler(request)

    @dynamic_prompt
    def dynamic_orchestrator_prompt(request: ModelRequest) -> str:
        verificado = request.state.get("verificado")
        nombre_completo = request.state.get("nombre_completo")

        if verificado:
            return f"""\
            Eres el asistente virtual de Aurion Consulting, atendiendo a {nombre_completo}, \
            un empleado verificado de la empresa.

            Tienes acceso a:
            - "consultar_informacion_empresa": datos de empleados, proyectos, \
            riesgo de abandono y política de empresa (información interna sensible).
            - "buscar_informacion_internet": información general externa \
            (legislación, normas del mercado laboral, etc.).

            Elige la fuente adecuada según la pregunta, y combina ambas si la pregunta \
            lo requiere. Responde en español, de forma clara y concisa.
            """
        else:
            return """\
            Eres el asistente virtual de Aurion Consulting. Todavía no has verificado \
            la identidad de la persona con la que hablas.

            Si este es el primer mensaje de la conversación (por ejemplo, si el \
            mensaje del usuario es "[INICIO_DE_CONVERSACION]" o algo similar sin \
            contenido real), saluda brevemente y pide su nombre y apellidos para \
            poder identificarle. No trates ese mensaje como una pregunta real.

            En cuanto el usuario te dé su nombre y apellidos, llama a la tool \
            "verificar_empleado" con esos datos.

            Mientras no esté verificado, puedes ayudarle con la tool \
            "buscar_informacion_internet" para preguntas generales \
            (legislación laboral, normas del mercado laboral, datos públicos, etc.).

            Si la persona resulta NO ser empleada de Aurion Consulting, informa de \
            que puedes ayudarle con búsquedas de información general en internet, \
            pero no con información interna de la empresa (política de empresa, \
            datos de empleados, proyectos, riesgo de abandono, etc.). \
            No inventes ni reveles ningún dato interno.

            Responde en español, de forma clara y concisa.
            """

    return [dynamic_tool_access, dynamic_orchestrator_prompt]


# ---------------------------------------------------------------------------
# 5. Construcción del agente orquestador
# ---------------------------------------------------------------------------
async def build_agent(provider: str = "groq"):
    llm = get_llm(provider)

    consultar_informacion_empresa, buscar_informacion_internet = (
        await build_subagent_tools(provider)
    )

    middleware = build_middleware(
        consultar_informacion_empresa,
        buscar_informacion_internet,
    )

    checkpointer = MemorySaver()

    agent = create_agent(
        model=llm,
        tools=[
            verificar_empleado,
            consultar_informacion_empresa,
            buscar_informacion_internet,
        ],
        state_schema=EmployeeState,
        middleware=middleware,
        checkpointer=checkpointer,
    )

    return agent


# ---------------------------------------------------------------------------
# Prueba rápida manual: python -m src.agent.agent
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    async def main():
        agent = await build_agent()
        config = {"configurable": {"thread_id": "test-1"}}

        preguntas = [
            "Hola, soy Marta Iglesias Roldán",
            "¿Cuántos días de vacaciones me quedan?",
        ]

        for p in preguntas:
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": p}]},
                config=config,
            )

            print(f"Tú: {p}")
            print(f"Asistente: {result['messages'][-1].content}\n")

    asyncio.run(main())