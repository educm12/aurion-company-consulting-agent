"""
eval/evaluators.py
LLM-as-judge: evalúa cada respuesta del chatbot en 5 dimensiones y
clasifica el fallo (si lo hay) como retrieval failure o generation
failure. Usa un modelo distinto al del agente, para evitar sesgo de
auto-evaluación.
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

load_dotenv()

JUDGE_PROVIDER = os.getenv("EVAL_JUDGE_PROVIDER", "groq")
JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "llama-3.3-70b-versatile")

_judge_llm = None


def _get_judge_llm():
    global _judge_llm
    if _judge_llm is None:
        _judge_llm = init_chat_model(JUDGE_MODEL, model_provider=JUDGE_PROVIDER, temperature=0)
    return _judge_llm


class JudgeScores(BaseModel):
    correctness: int = Field(..., ge=1, le=5, description="¿La respuesta es factualmente correcta respecto a expected_answer?")
    relevance: int = Field(..., ge=1, le=5, description="¿La respuesta aborda realmente lo que se preguntó?")
    faithfulness: int = Field(..., ge=1, le=5, description="¿Cada afirmación está respaldada por el contexto recuperado (no alucina)?")
    completeness: int = Field(..., ge=1, le=5, description="¿Incluye toda la información relevante presente en expected_answer/context?")
    overall: int = Field(..., ge=1, le=5, description="Calidad global considerando las 4 dimensiones anteriores.")
    context_sufficient: bool = Field(
        ..., description="¿El contexto recuperado contenía la información necesaria para responder bien, "
                          "asumiendo que la pregunta SÍ requería contexto? Si la pregunta no requería "
                          "contexto (p.ej. fuera de dominio), responde true."
    )
    reasoning: str = Field(..., description="Justificación breve (2-3 frases) de las puntuaciones.")


JUDGE_SYSTEM_PROMPT = """\
Eres un evaluador experto de un chatbot empresarial de RRHH (Aurion \
Consulting) que combina políticas internas (RAG) y datos de empleados \
(SQL). Tu trabajo es puntuar UNA respuesta del chatbot, siendo estricto \
y objetivo.

Reglas especiales importantes:
- Si la pregunta es ambigua (falta información como el nombre de un \
  empleado) o está fuera del dominio de la empresa, la respuesta \
  CORRECTA es que el chatbot lo reconozca y pida aclaración o decline \
  responder — en ese caso, si lo hace bien, todas las puntuaciones \
  deben ser altas (4-5), no bajas.
- Si la pregunta pide un dato que no existe (p.ej. un empleado \
  inventado, una política no cubierta en el manual), la respuesta \
  CORRECTA es decir explícitamente que no tiene esa información — \
  inventar una respuesta plausible pero falsa debe puntuarse muy bajo \
  en correctness y faithfulness (1-2), aunque "suene" razonable.
- "context_sufficient" se refiere únicamente a si el contexto \
  recuperado (context_used) contenía lo necesario para responder bien. \
  Si no se recuperó contexto porque la pregunta no lo requería \
  (fuera de dominio, ambigua), pon context_sufficient=true.

Responde ÚNICAMENTE en el formato estructurado solicitado.
"""

JUDGE_USER_TEMPLATE = """\
PREGUNTA:
{question}

RESPUESTA DEL CHATBOT:
{answer}

RESPUESTA ESPERADA (referencia humana):
{expected_answer}

CONTEXTO DE REFERENCIA (lo que debería haberse usado, según un humano):
{reference_context}

CONTEXTO REALMENTE RECUPERADO POR EL RAG (lo que el chatbot vio de verdad):
{context_used}

TOOLS QUE LLAMÓ EL CHATBOT:
{tools_called}
"""


async def judge_answer(
    question: str,
    answer: str,
    expected_answer: str | None,
    reference_context: str | None,
    context_used: list[str],
    tools_called: list[str],
) -> JudgeScores:
    llm = _get_judge_llm().with_structured_output(JudgeScores)

    user_prompt = JUDGE_USER_TEMPLATE.format(
        question=question,
        answer=answer,
        expected_answer=expected_answer or "(no aplica / no hay respuesta esperada fija)",
        reference_context=reference_context or "(no aplica)",
        context_used="\n---\n".join(context_used) if context_used else "(no se recuperó ningún contexto)",
        tools_called=", ".join(tools_called) if tools_called else "(ninguna)",
    )

    result = await llm.ainvoke(
        [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return result


def classify_failure(scores: JudgeScores, rag_tool_called: bool, category: str) -> str | None:
    """
    Devuelve "retrieval_failure", "generation_failure", o None si la
    respuesta fue satisfactoria (overall >= 4).
    """
    if scores.overall >= 4:
        return None

    # Categorías donde no aplica RAG/SQL de forma relevante (ambigüedad,
    # fuera de dominio): un fallo aquí es de generación (no supo manejar
    # el caso), no de retrieval.
    if category in {"ambiguous", "out_of_context"}:
        return "generation_failure"

    # Si se esperaba recuperar contexto pero no se llamó a la tool RAG
    # en absoluto, o el contexto recuperado no era suficiente -> retrieval.
    if not rag_tool_called or not scores.context_sufficient:
        return "retrieval_failure"

    # Contexto suficiente pero la respuesta sigue siendo mala -> generación.
    return "generation_failure"