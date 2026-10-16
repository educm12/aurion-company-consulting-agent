"""
eval/evaluators.py
Evaluación con DeepEval: se sustituye el evaluador personalizado basado en
LangChain por métricas nativas de DeepEval:

  - correctness          -> GEval (respuesta correcta vs expected_answer)
  - relevance            -> AnswerRelevancyMetric (¿aborda lo que se preguntó?)
  - faithfulness         -> FaithfulnessMetric (¿respaldada por el contexto
                            realmente recuperado? no alucina)
  - completeness         -> GEval (cubre la información de expected_answer)
  - appropriate_behavior -> GEval (para preguntas ambiguas, fuera de dominio o
                            sin información: ¿pide aclaración / declina /
                            admite que no sabe, en vez de inventar?)
  - contextual_relevancy -> ContextualRelevancyMetric (SOLO diagnóstico del
                            retrieval; no entra en el overall)

Las métricas aplicadas dependen de la categoría de la pregunta:
  - Categorías de comportamiento (ambiguous, out_of_context,
    insufficient_info): appropriate_behavior + correctness.
  - Resto: correctness, relevance, faithfulness, completeness.

El juez usa el proveedor/modelo configurado en el entorno
(EVAL_JUDGE_PROVIDER / EVAL_JUDGE_MODEL, por defecto groq +
llama-3.3-70b-versatile) mediante un adaptador DeepEvalBaseLLM sobre
langchain (sin añadir dependencias como litellm).

Además de las métricas, se aplican comprobaciones deterministas en Python
y se clasifica el fallo como retrieval_failure / generation_failure.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, SingleTurnParams

load_dotenv()

JUDGE_PROVIDER = os.getenv("EVAL_JUDGE_PROVIDER", "groq")
JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "llama-3.3-70b-versatile")

# Umbral por métrica (0-1) y umbral de "respuesta satisfactoria" (overall).
METRIC_THRESHOLD = float(os.getenv("EVAL_METRIC_THRESHOLD", "0.5"))
OK_THRESHOLD = float(os.getenv("EVAL_OK_THRESHOLD", "0.7"))

# Categorías donde lo correcto es un COMPORTAMIENTO (pedir aclaración,
# declinar, admitir falta de información), no un dato factual.
BEHAVIOR_CATEGORIES = {"ambiguous", "out_of_context", "insufficient_info"}

# Categorías donde se espera que el RAG recupere contexto del manual.
RAG_EXPECTED_CATEGORIES = {"simple_rag", "hybrid", "hybrid_complex"}

CORRECTNESS_CRITERIA = (
    "Determine whether the actual output is factually correct with respect "
    "to the expected output (the human ground-truth reference)."
)
COMPLETENESS_CRITERIA = (
    "Determine whether the actual output contains all the key information "
    "present in the expected output (the human ground-truth reference)."
)
BEHAVIOR_CRITERIA = (
    "The expected output describes the CORRECT BEHAVIOR for this question "
    "(asking for clarification, declining to answer, or admitting there is no "
    "information). Determine whether the actual output shows that behavior and "
    "does NOT invent facts or answer as if the information existed."
)


# ---------------------------------------------------------------------------
# Adaptador del juez: DeepEval <-> LangChain (init_chat_model)
# ---------------------------------------------------------------------------
class GroqJudgeLLM(DeepEvalBaseLLM):
    """Modelo evaluador de DeepEval respaldado por init_chat_model."""

    def __init__(self, model_name: str, provider: str = "groq"):
        # Se guardan antes de super().__init__ porque load_model() se llama dentro.
        self.model_name = model_name
        self.provider = provider
        super().__init__(model=model_name)

    def load_model(self):
        return init_chat_model(self.model_name, model_provider=self.provider, temperature=0)

    def generate(self, prompt, schema=None, **kwargs):
        if schema is not None:
            return self.model.with_structured_output(schema).invoke(prompt)
        return self.model.invoke(prompt).content

    async def a_generate(self, prompt, schema=None, **kwargs):
        if schema is not None:
            return await self.model.with_structured_output(schema).ainvoke(prompt)
        return (await self.model.ainvoke(prompt)).content

    def get_model_name(self):
        return self.model_name


_judge = None
_metrics = None


def _get_judge():
    global _judge
    if _judge is None:
        _judge = GroqJudgeLLM(JUDGE_MODEL, JUDGE_PROVIDER)
    return _judge


def _get_metrics():
    """Las métricas se construyen una sola vez: GEval genera sus evaluation_steps
    con una llamada al LLM al construirse, así que cachearlas evita repetir ese coste."""
    global _metrics
    if _metrics is None:
        judge = _get_judge()
        g_eval_params = [
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ]
        _metrics = {
            "correctness": GEval(
                name="Correctness",
                criteria=CORRECTNESS_CRITERIA,
                evaluation_params=g_eval_params,
                threshold=METRIC_THRESHOLD,
                model=judge,
                strict_mode=False,
            ),
            "relevance": AnswerRelevancyMetric(
                threshold=METRIC_THRESHOLD, model=judge, strict_mode=False
            ),
            "faithfulness": FaithfulnessMetric(
                threshold=METRIC_THRESHOLD, model=judge, strict_mode=False
            ),
            "completeness": GEval(
                name="Completeness",
                criteria=COMPLETENESS_CRITERIA,
                evaluation_params=g_eval_params,
                threshold=METRIC_THRESHOLD,
                model=judge,
                strict_mode=False,
            ),
            "appropriate_behavior": GEval(
                name="AppropriateBehavior",
                criteria=BEHAVIOR_CRITERIA,
                evaluation_params=g_eval_params,
                threshold=METRIC_THRESHOLD,
                model=judge,
                strict_mode=False,
            ),
            "contextual_relevancy": ContextualRelevancyMetric(
                threshold=METRIC_THRESHOLD, model=judge, strict_mode=False
            ),
        }
    return _metrics


# ---------------------------------------------------------------------------
# Resultado de la evaluación
# ---------------------------------------------------------------------------
@dataclass
class EvalScores:
    correctness: float | None
    relevance: float | None
    faithfulness: float | None
    completeness: float | None
    appropriate_behavior: float | None
    contextual_relevancy: float | None  # diagnóstico de retrieval, NO entra en overall
    overall: float
    context_sufficient: bool
    reasoning: str


async def judge_answer(
    question: str,
    answer: str,
    expected_answer: str | None,
    reference_context: str | None,
    context_used: list[str],
    tools_called: list[str],
    category: str,
    sql_context: list[str] | None = None,
) -> EvalScores:
    cleaned = (answer or "").strip()

    # Comprobación determinista: respuesta vacía -> fallo total sin llamar al juez.
    if not cleaned:
        return EvalScores(
            correctness=0.0,
            relevance=None,
            faithfulness=None,
            completeness=None,
            appropriate_behavior=None,
            contextual_relevancy=None,
            overall=0.0,
            context_sufficient=False,
            reasoning="Respuesta vacía: fallo determinista, no se invocó al modelo juez.",
        )

    ctx = [c for c in (context_used or []) if c and c.strip()]  # chunks del RAG
    sql = [c for c in (sql_context or []) if c and c.strip()]    # salidas de SQL/riesgo

    # Caso base: solo contexto RAG. Lo usan correctness/relevance/completeness
    # y, sobre todo, contextual_relevancy (diagnóstico del retrieval).
    test_case = LLMTestCase(
        input=question,
        actual_output=cleaned,
        expected_output=expected_answer,  # None si no hay: _run omite esas métricas
        retrieval_context=ctx or None,
        context=[reference_context] if reference_context else None,
    )

    # Caso para faithfulness: RAG + SQL, para que también se verifique la
    # parte de la respuesta que proviene de la base de datos.
    faith_case = LLMTestCase(
        input=question,
        actual_output=cleaned,
        expected_output=expected_answer,
        retrieval_context=(ctx + sql) or None,
        context=[reference_context] if reference_context else None,
    )

    metrics = _get_metrics()
    scores: dict[str, float | None] = {}
    reasons: list[str] = []

    async def _run(key: str, required_tc_params: list[str], case: LLMTestCase | None = None):
        case = case or test_case
        if any(getattr(case, p, None) is None for p in required_tc_params):
            scores[key] = None
            return
        metric = metrics[key]
        try:
            await metric.a_measure(case)
            scores[key] = metric.score
            if metric.reason:
                reasons.append(f"{key}: {metric.reason}")
        except Exception as e:  # métrica no aplicable / error del juez
            scores[key] = None
            reasons.append(f"{key}: no evaluado ({e})")

    # Métricas que entran en el overall, según el tipo de pregunta.
    if category in BEHAVIOR_CATEGORIES:
        plan = {
            "appropriate_behavior": ["expected_output"],
            "correctness": ["expected_output"],
        }
    else:
        plan = {
            "correctness": ["expected_output"],
            "relevance": [],
            "faithfulness": ["retrieval_context"],
            "completeness": ["expected_output"],
        }

    for key, required in plan.items():
        await _run(key, required, faith_case if key == "faithfulness" else None)

    # Diagnóstico de retrieval: se mide aparte y no entra en el overall.
    if category in RAG_EXPECTED_CATEGORIES:
        await _run("contextual_relevancy", ["retrieval_context"])

    values = [scores[k] for k in plan if scores.get(k) is not None]
    if not values:
        raise RuntimeError(
            "Ninguna métrica pudo evaluarse; revisa el modelo juez. Detalle: "
            + " | ".join(reasons)[:500]
        )
    overall = sum(values) / len(values)
    
    return EvalScores(
        correctness=scores.get("correctness"),
        relevance=scores.get("relevance"),
        faithfulness=scores.get("faithfulness"),
        completeness=scores.get("completeness"),
        appropriate_behavior=scores.get("appropriate_behavior"),
        contextual_relevancy=scores.get("contextual_relevancy"),
        overall=overall,
        context_sufficient=bool(ctx),
        reasoning=" ".join(reasons).strip()[:800],
    )


def classify_failure(scores: EvalScores, rag_tool_called: bool, category: str) -> str | None:
    """
    Devuelve "retrieval_failure", "generation_failure", o None si la
    respuesta fue satisfactoria (overall >= OK_THRESHOLD).
    """
    if scores.overall >= OK_THRESHOLD:
        return None

    # Preguntas donde no se espera RAG (ambiguas, fuera de dominio, SQL puro):
    # un fallo aquí es de generación, no de retrieval.
    if category not in RAG_EXPECTED_CATEGORIES:
        return "generation_failure"

    # Se esperaba RAG y no se llamó a la tool -> retrieval.
    if not rag_tool_called:
        return "retrieval_failure"

    # Se recuperó contexto, pero poco relevante para la pregunta -> retrieval.
    if scores.contextual_relevancy is not None and scores.contextual_relevancy < METRIC_THRESHOLD:
        return "retrieval_failure"

    # Contexto razonable pero la respuesta sigue siendo mala -> generación.
    return "generation_failure"