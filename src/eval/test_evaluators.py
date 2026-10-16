"""
Prueba rápida manual: python -m src.eval.test_evaluators

Ejecuta unos pocos casos representativos (RAG puro, híbrido y un caso de
comportamiento esperado) para validar runner + evaluators antes de lanzar la
evaluación completa. Son ~3 preguntas, así que consume poca cuota del juez.
"""

import asyncio
import json
from dataclasses import asdict

from src.eval.evaluators import classify_failure, judge_answer
from src.eval.runner import run_question

LOGIN_MESSAGE = "Hola, soy Beatriz Salas Núñez."

CASES = [
    {
        "category": "simple_rag",
        "question": "¿Cuántos días de vacaciones tiene un empleado con más de diez años de antigüedad?",
        "expected_answer": "30 días de vacaciones anuales.",
        "reference_context": "Manual, sección 6: 10 años o más -> 30 días.",
    },
    {
        "category": "hybrid",
        "question": "¿Puede Claudia Gallego Moreno traer a su perro a la oficina?",
        "expected_answer": (
            "No: aunque Claudia Gallego Moreno trabaja en la sede de Madrid, que cuenta con zona"
            "pet-friendly, trabaja en el departamento de Comercial, que no permite mascotas."
        ),
        "reference_context": "Manual sección 10 + tabla empleados (departamento y mascota de Claudia Gallego Moreno).",
    },
    {
        "category": "insufficient_info",
        "question": "¿Cuántos días de vacaciones tiene Pedro García?",
        "expected_answer": (
            "No existe ningún empleado llamado Pedro García en la base de datos; el "
            "chatbot debería decirlo explícitamente, no inventar un dato."
        ),
        "reference_context": "Tabla empleados no contiene ningún 'Pedro García'.",
    },
]


async def run_case(case: dict):
    print("=" * 70)
    print(f"[{case['category']}] {case['question']}")

    r = await run_question(case["question"], initial_message=LOGIN_MESSAGE)

    print(f"\nRespuesta: {r.answer}")
    print(f"RAG llamado: {r.rag_tool_called}  |  chunks RAG: {len(r.context_used)}  |  salidas SQL: {len(r.sql_context)}")
    print(f"Tools llamadas: {r.tools_called}\n")

    scores = await judge_answer(
        question=r.question,
        answer=r.answer,
        expected_answer=case["expected_answer"],
        reference_context=case["reference_context"],
        context_used=r.context_used,
        tools_called=r.tools_called,
        category=case["category"],
        sql_context=r.sql_context,
    )

    print(json.dumps(asdict(scores), ensure_ascii=False, indent=2))

    failure = classify_failure(scores, r.rag_tool_called, category=case["category"])
    print(f"Failure type: {failure}\n")


async def main():
    for case in CASES:
        try:
            await run_case(case)
        except Exception as e:
            print(f"  ERROR en este caso: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())