"""
eval/runner.py
Ejecuta el chatbot (subagente de empresa: RAG + SQL) de forma programática
para una pregunta dada, capturando:
  - la respuesta final
  - el contexto RAG REALMENTE usado en la generación, extraído del
    ToolMessage de "consultar_politica_empresa" (no una consulta al
    retriever en frío) -- esto es lo que permite luego distinguir retrieval
    failure de generation failure.

No modifica src/agent/: reutiliza build_company_subagent() tal cual existe.
"""

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from src.agent.agent import build_agent, _subagent_capture

_agent_cache: dict[str, object] = {}


async def _get_agent(provider: str = "groq"):
    if provider not in _agent_cache:
        _agent_cache[provider] = await build_agent(provider)
    return _agent_cache[provider]


@dataclass
class RunResult:
    question: str
    answer: str
    context_used: list[str] = field(default_factory=list)
    rag_tool_called: bool = False
    tools_called: list[str] = field(default_factory=list)


def _extract_nested_context(nested_calls: list[tuple[str, list]]) -> tuple[list[str], bool]:
    """Busca, dentro de los mensajes de cada subagente invocado, los
    ToolMessage de RAG (consultar_politica_empresa) para extraer el
    contexto real usado, sin importar en qué subagente haya terminado."""
    context_chunks = []
    rag_called = False

    for _, messages in nested_calls:
        for msg in messages:
            if msg.__class__.__name__ == "ToolMessage" and getattr(msg, "name", "") == "consultar_politica_empresa":
                rag_called = True
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                context_chunks.append(content)

    return context_chunks, rag_called


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

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
        )
    finally:
        _subagent_capture.reset(token)

    messages = result["messages"]
    answer = messages[-1].content

    tools_called = [
        tc.get("name", "")
        for msg in messages
        for tc in (getattr(msg, "tool_calls", None) or [])
    ]

    context_used, rag_called = _extract_nested_context(capture)

    return RunResult(
        question=question,
        answer=answer,
        context_used=context_used,
        rag_tool_called=rag_called,
        tools_called=tools_called,
    )


async def run_questions(questions: list[str], provider: str = "groq") -> list[RunResult]:
    return [await run_question(q, provider) for q in questions]


if __name__ == "__main__":
    async def main():
        mensaje_inicial = "Hola, soy Beatriz Salas Núñez."
        pregunta = "¿Cuántos días de vacaciones tiene algien con mas de 10 años en la empresa?"
        r = await run_question(pregunta, initial_message=mensaje_inicial)
        print(f"Pregunta: {r.question}")
        print(f"Respuesta: {r.answer}")
        print(f"RAG llamado: {r.rag_tool_called}")
        print(f"Tools llamadas: {r.tools_called}")
        print(f"Contexto ({len(r.context_used)} chunks):")
        for i, c in enumerate(r.context_used, 1):
            print(f"  [{i}] {c[:200]}...")

    asyncio.run(main())