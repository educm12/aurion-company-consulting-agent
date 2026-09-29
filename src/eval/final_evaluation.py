"""
eval/final_evaluation.py
Script principal de evaluación: python -m src.eval.final_evaluation
(o python final_evaluation.py si lo ejecutas dentro de eval/).

1. Carga el dataset.
2. Ejecuta cada pregunta contra el chatbot (runner.py).
3. Obtiene respuesta y contexto RAG realmente usado.
4. Ejecuta el LLM-as-judge (evaluators.py) sobre cada resultado.
5. Calcula métricas agregadas (globales y por categoría).
6. Guarda un CSV con el detalle fila a fila.
7. Identifica las peores respuestas.
8. Genera gráficas resumen (PNG).
"""

import asyncio
import csv
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt

from src.eval.dataset import load_dataset
from src.eval.evaluators import classify_failure, judge_answer
from src.eval.runner import run_question

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Empleado verificado usado como "usuario" de las evaluaciones, para que
# las preguntas híbridas/SQL tengan acceso completo. Sirve cualquier empleado
# que exista en resources/aurion.db.
EVAL_LOGIN_MESSAGE = "Hola, soy Beatriz Salas Núñez."

PROVIDER = "groq"  # proveedor del agente evaluado; el juez usa el suyo propio


@dataclass
class EvalRow:
    id: str
    category: str
    question: str
    expected_answer: str | None
    model_answer: str
    correctness: int
    relevance: int
    faithfulness: int
    completeness: int
    overall_score: int
    context_sufficient: bool
    rag_tool_called: bool
    tools_called: str
    failure_type: str | None
    reasoning: str


async def evaluate_item(item: dict) -> EvalRow:
    run_result = await run_question(
        item["question"],
        provider=PROVIDER,
        initial_message=EVAL_LOGIN_MESSAGE,
    )

    scores = await judge_answer(
        question=item["question"],
        answer=run_result.answer,
        expected_answer=item.get("expected_answer"),
        reference_context=item.get("context"),
        context_used=run_result.context_used,
        tools_called=run_result.tools_called,
    )

    failure_type = classify_failure(scores, run_result.rag_tool_called, item["category"])

    return EvalRow(
        id=item["id"],
        category=item["category"],
        question=item["question"],
        expected_answer=item.get("expected_answer"),
        model_answer=run_result.answer,
        correctness=scores.correctness,
        relevance=scores.relevance,
        faithfulness=scores.faithfulness,
        completeness=scores.completeness,
        overall_score=scores.overall,
        context_sufficient=scores.context_sufficient,
        rag_tool_called=run_result.rag_tool_called,
        tools_called=", ".join(run_result.tools_called),
        failure_type=failure_type,
        reasoning=scores.reasoning,
    )


async def run_evaluation() -> list[EvalRow]:
    dataset = load_dataset()
    rows = []
    for i, item in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] Evaluando: {item['question'][:70]}...")
        try:
            row = await evaluate_item(item)
        except Exception as e:
            print(f"  ERROR en '{item['id']}': {e}")
            continue
        rows.append(row)
        print(f"  overall={row.overall_score}  failure={row.failure_type}")
    return rows


# ---------------------------------------------------------------------------
# Guardado de resultados
# ---------------------------------------------------------------------------
def save_csv(rows: list[EvalRow], path: Path):
    fieldnames = list(asdict(rows[0]).keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    print(f"\nResultados guardados en: {path}")


# ---------------------------------------------------------------------------
# Métricas agregadas
# ---------------------------------------------------------------------------
def print_aggregate_metrics(rows: list[EvalRow]):
    dims = ["correctness", "relevance", "faithfulness", "completeness", "overall_score"]

    print("\n" + "=" * 60)
    print("MÉTRICAS AGREGADAS (global)")
    print("=" * 60)
    for dim in dims:
        values = [getattr(r, dim) for r in rows]
        print(f"  {dim:15s}: media={statistics.mean(values):.2f}  min={min(values)}  max={max(values)}")

    retrieval_failures = sum(1 for r in rows if r.failure_type == "retrieval_failure")
    generation_failures = sum(1 for r in rows if r.failure_type == "generation_failure")
    ok = sum(1 for r in rows if r.failure_type is None)
    print(f"\n  OK (overall>=4):      {ok}/{len(rows)}")
    print(f"  Retrieval failures:   {retrieval_failures}/{len(rows)}")
    print(f"  Generation failures:  {generation_failures}/{len(rows)}")

    print("\n" + "-" * 60)
    print("MÉTRICAS POR CATEGORÍA")
    print("-" * 60)
    categories = sorted(set(r.category for r in rows))
    for cat in categories:
        cat_rows = [r for r in rows if r.category == cat]
        avg_overall = statistics.mean(r.overall_score for r in cat_rows)
        print(f"  {cat:20s}: n={len(cat_rows):2d}  overall medio={avg_overall:.2f}")


def print_worst_answers(rows: list[EvalRow], n: int = 5):
    print("\n" + "=" * 60)
    print(f"PEORES {n} RESPUESTAS (por overall_score)")
    print("=" * 60)
    worst = sorted(rows, key=lambda r: r.overall_score)[:n]
    for r in worst:
        print(f"\n[{r.id}] overall={r.overall_score}  failure={r.failure_type}  categoría={r.category}")
        print(f"  Pregunta:  {r.question}")
        print(f"  Respuesta: {r.model_answer[:200]}...")
        print(f"  Motivo:    {r.reasoning}")


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------
def generate_charts(rows: list[EvalRow], timestamp: str):
    dims = ["correctness", "relevance", "faithfulness", "completeness", "overall_score"]

    # 1. Barras: media por dimensión
    fig, ax = plt.subplots(figsize=(7, 4))
    means = [statistics.mean(getattr(r, d) for r in rows) for d in dims]
    ax.bar(dims, means, color="#4C72B0")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Puntuación media (1-5)")
    ax.set_title("Puntuación media por dimensión")
    plt.xticks(rotation=20)
    plt.tight_layout()
    fig.savefig(RESULTS_DIR / f"dimensiones_{timestamp}.png")
    plt.close(fig)

    # 2. Barras: overall medio por categoría
    categories = sorted(set(r.category for r in rows))
    cat_means = [statistics.mean(r.overall_score for r in rows if r.category == c) for c in categories]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(categories, cat_means, color="#55A868")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Overall medio")
    ax.set_title("Overall medio por categoría de pregunta")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    fig.savefig(RESULTS_DIR / f"categorias_{timestamp}.png")
    plt.close(fig)

    # 3. Tarta: tipos de fallo
    ok = sum(1 for r in rows if r.failure_type is None)
    retrieval = sum(1 for r in rows if r.failure_type == "retrieval_failure")
    generation = sum(1 for r in rows if r.failure_type == "generation_failure")
    fig, ax = plt.subplots(figsize=(5, 5))
    labels_vals = [(l, v) for l, v in [("OK", ok), ("Retrieval failure", retrieval), ("Generation failure", generation)] if v > 0]
    ax.pie(
        [v for _, v in labels_vals],
        labels=[l for l, _ in labels_vals],
        autopct="%1.0f%%",
        colors=["#55A868", "#C44E52", "#DD8452"],
    )
    ax.set_title("Distribución de resultados")
    plt.tight_layout()
    fig.savefig(RESULTS_DIR / f"fallos_{timestamp}.png")
    plt.close(fig)

    print(f"\nGráficas guardadas en: {RESULTS_DIR}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    rows = await run_evaluation()
    if not rows:
        print("No se obtuvo ningún resultado (todas las preguntas fallaron).")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_csv(rows, RESULTS_DIR / f"results_{timestamp}.csv")
    print_aggregate_metrics(rows)
    print_worst_answers(rows, n=5)
    generate_charts(rows, timestamp)


if __name__ == "__main__":
    asyncio.run(main())