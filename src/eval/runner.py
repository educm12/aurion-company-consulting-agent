"""
eval/runner.py
Ejecuta el chatbot (agente orquestador completo) de forma programática para
una pregunta dada, capturando:
  - la respuesta final
  - el contexto RAG REALMENTE usado en la generación, extraído del
    ToolMessage de "consultar_politica_empresa" (no una consulta al
    retriever en frío) -- esto es lo que permite luego distinguir retrieval
    failure de generation failure.
  - el contexto SQL realmente devuelto por las tools de datos (read_query,
    calculate_risk_leaving*), en una lista APARTE: sirve para que faithfulness
    pueda verificar también la parte de la respuesta que viene de la base de
    datos, sin contaminar la medición de calidad del retrieval del RAG.

El contexto está anidado dentro de las sub-invocaciones de los subagentes, así
que se obtiene mediante la instrumentación opcional `_subagent_capture` de
src/agent/agent.py (no-op en producción).
"""

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from src.agent.agent import build_agent, _subagent_capture

RAG_TOOL_NAME = "consultar_politica_empresa"

# Tools de SQL que devuelven DATOS (sirven de evidencia para faithfulness).
# list_tables y describe_table se excluyen a propósito: devuelven esquema, no
# hechos sobre los que se apoye una respuesta, y solo añadirían ruido.
SQL_DATA_TOOL_NAMES = {"read_query", "calculate_risk_leaving", "calculate_risk_leaving_all"}

_agent_cache: dict[str, object] = {}


async def _get_agent(provider: str = "groq"):
    if provider not in _agent_cache:
        _agent_cache[provider] = await build_agent(provider)
    return _agent_cache[provider]


@dataclass
class RunResult:
    question: str
    answer: str
    context_used: list[str] = field(default_factory=list)  # chunks RAG
    sql_context: list[str] = field(default_factory=list)    # salidas de tools SQL/riesgo
    rag_tool_called: bool = False
    tools_called: list[str] = field(default_factory=list)


def _content_to_str(content) -> str:
    """Los ToolMessage de MCP pueden traer el contenido como lista de bloques."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)


def _extract_nested(nested_calls: list[tuple[str, list]]) -> tuple[list[str], list[str], bool, list[str]]:
    """
    Recorre los mensajes de cada subagente invocado y extrae:
      - chunks de contexto RAG (ToolMessage de consultar_politica_empresa)
      - salidas de tools SQL/riesgo (contexto de datos)
      - si se llamó al RAG
      - nombres de TODAS las tools llamadas dentro de los subagentes
    sin importar en qué subagente hayan terminado.
    """
    rag_chunks: list[str] = []
    sql_chunks: list[str] = []
    rag_called = False
    nested_tools: list[str] = []

    for _, messages in nested_calls:
        for msg in messages:
            for tc in (getattr(msg, "tool_calls", None) or []):
                nested_tools.append(tc.get("name", ""))

            if msg.__class__.__name__ != "ToolMessage":
                continue

            name = getattr(msg, "name", "")
            if name == RAG_TOOL_NAME:
                rag_called = True
                rag_chunks.append(_content_to_str(msg.content))
            elif name in SQL_DATA_TOOL_NAMES:
                sql_chunks.append(_content_to_str(msg.content))

    return rag_chunks, sql_chunks, rag_called, nested_tools


async def run_question(
    question: str,
    provider: str = "groq",
    initial_message: str | None = None,
) -> RunResult:
    agent = await _get_agent(provider)
    config = {"configurable": {"thread_id": f"eval-{provider}-{uuid4()}"}}

    capture: list[tuple[str, list]] = []
    token = _subagent_capture.set(capture)
    try:
        if initial_message:
            await agent.ainvoke(
                {"messages": [{"role": "user", "content": initial_message}]},
                config=config,
            )
            # Descartamos lo capturado durante el login: el contexto y las
            # tools de la pregunta evaluada no deben mezclarse con los del
            # mensaje de identificación.
            capture.clear()

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
        )
    finally:
        _subagent_capture.reset(token)

    messages = result["messages"]
    answer = messages[-1].content

    # Tools del orquestador. Ojo: result["messages"] incluye el historial del
    # thread, así que contaría también las del login. Se limita a los mensajes
    # posteriores al último mensaje humano (la pregunta evaluada).
    last_human_idx = max(
        (i for i, m in enumerate(messages) if m.__class__.__name__ == "HumanMessage"),
        default=0,
    )
    top_level_tools = [
        tc.get("name", "")
        for msg in messages[last_human_idx:]
        for tc in (getattr(msg, "tool_calls", None) or [])
    ]

    rag_chunks, sql_chunks, rag_called, nested_tools = _extract_nested(capture)

    return RunResult(
        question=question,
        answer=answer,
        context_used=rag_chunks,
        sql_context=sql_chunks,
        rag_tool_called=rag_called,
        tools_called=top_level_tools + nested_tools,
    )


async def run_questions(questions: list[str], provider: str = "groq") -> list[RunResult]:
    return [await run_question(q, provider) for q in questions]


if __name__ == "__main__":
    async def main():
        mensaje_inicial = "Hola, soy Beatriz Salas Núñez."
        pregunta = "¿Cuántos días de vacaciones le quedan a Marta Iglesias Roldán?"
        r = await run_question(pregunta, initial_message=mensaje_inicial)
        print(f"Pregunta: {r.question}")
        print(f"Respuesta: {r.answer}")
        print(f"RAG llamado: {r.rag_tool_called}")
        print(f"Tools llamadas: {r.tools_called}")
        print(f"Contexto RAG ({len(r.context_used)} chunks):")
        for i, c in enumerate(r.context_used, 1):
            print(f"  [{i}] {c[:200]}...")
        print(f"Contexto SQL ({len(r.sql_context)} salidas):")
        for i, c in enumerate(r.sql_context, 1):
            print(f"  [{i}] {c[:200]}...")

    asyncio.run(main())