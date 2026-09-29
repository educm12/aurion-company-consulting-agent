"""
Prueba rápida manual: python -m src.eval.test_evaluators
"""

import asyncio

from src.eval.evaluators import classify_failure, judge_answer
from src.eval.runner import run_question


async def main():
    r = await run_question(
        "¿Cuántos días de vacaciones tiene un empleado con más de diez años de antigüedad?",
        initial_message="Hola, soy Beatriz Salas Núñez."
    )

    print(f"Pregunta: {r.question}")
    print(f"Respuesta: {r.answer}")
    print()

    scores = await judge_answer(
        question=r.question,
        answer=r.answer,
        expected_answer="30 días de vacaciones anuales.",
        reference_context="Manual, sección 6: 10 años o más -> 30 días.",
        context_used=r.context_used,
        tools_called=r.tools_called,
    )

    print(scores.model_dump_json(indent=2))

    failure = classify_failure(
        scores,
        r.rag_tool_called,
        category="simple_rag",
    )
    print(f"Failure type: {failure}")


if __name__ == "__main__":
    asyncio.run(main())