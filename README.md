# Aurion Consulting Chatbot

An AI assistant for a fictional company (**Aurion Consulting**) that answers employee questions by combining structured data (SQLite) with unstructured company policy documentation (RAG), orchestrated through a multi-agent LangGraph pipeline.

## Overview

The assistant can answer questions that require combining two sources of information at once, for example:

- *"How many vacation days does Marta have left, based on her seniority?"*
- *"Can María bring her dog to the office, and how many vacation days has she taken this year?"*

It also verifies the identity of the person chatting: employees get full access (company policies + database + attrition risk), while non-employees are limited to general web search.

On top of the core chatbot, the project includes two supporting systems:
- An **automated evaluation pipeline** (LLM-as-judge + LangSmith) to score answer quality and distinguish retrieval failures from generation failures.
- A **semantic cache** (Redis + RedisVL) that reuses answers to paraphrased questions instead of re-running the LLM/RAG/MCP pipeline, scoped per user identity to avoid leaking personal data between employees.

## Architecture

- **Orchestrator agent** — verifies the user's identity and routes to the right subagent(s), with a dynamic system prompt based on verification state.
- **Company subagent** — answers questions using:
  - **RAG** over the internal policy manual (ChromaDB + HuggingFace embeddings)
  - **SQLite database** (employees, departments, projects) via an **MCP** server
  - A custom attrition-risk heuristic tool
- **Web subagent** — general-purpose web search (Tavily) for questions unrelated to the company.
- **Semantic cache** — sits in front of the agent invocation: on a cache hit, the LLM/RAG/MCP pipeline is skipped entirely and the stored answer is returned directly.
- **LangGraph** manages state, checkpointing (conversation memory) and conditional tool access.
- **LLM provider** is configurable per session: Groq, OpenAI, Anthropic or Google Gemini.

## Tech stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangChain + LangGraph |
| Vector store (RAG) | ChromaDB |
| Structured data access | MCP (Model Context Protocol) over SQLite |
| Semantic cache | Redis + RedisVL |
| Web search | Tavily |
| Evaluation | LLM-as-judge (custom) + LangSmith |
| Backend API | FastAPI |
| Frontend | Streamlit |
| LLMs | Groq, OpenAI, Anthropic, Google Gemini |

## Project structure

```
my-chatbot-project/
├── app/                    # Web application (FastAPI + Streamlit)
│   ├── backend/
│   │   ├── main.py         # FastAPI entrypoint
│   │   ├── routers/        # /auth, /chat, /cache endpoints
│   │   └── services/       # agent lifecycle, cache integration & business logic
│   └── frontend/
│       └── streamlit_app.py
├── src/
│   ├── agent/               # agent, tools, MCP wiring
│   ├── rag/                 # embeddings + retriever
│   ├── cache/               # semantic cache (Redis + RedisVL)
│   │   ├── config.py            # thresholds, TTLs, Redis URL — all env-configurable
│   │   ├── semantic_cache.py    # lookup()/store() wrapper over RedisVL SemanticCache
│   │   └── metrics.py           # hit rate / latency tracking
│   └── eval/                # evaluation pipeline (separate from production code)
│       ├── dataset.py           # ~16 representative questions (simple, hybrid, ambiguous, out-of-context...)
│       ├── runner.py            # runs the chatbot programmatically, captures answer + retrieved context
│       ├── evaluators.py        # LLM-as-judge: correctness, relevance, faithfulness, completeness, overall
│       ├── final_evaluation.py  # main script: python -m src.eval.evaluate
│       └── results/             # generated CSVs and charts (gitignored)
├── resources/
│   ├── aurion.db             # SQLite database
│   ├── aurion_schema.sql
│   ├── chroma_db/            # persisted vector store
│   └── manual_politicas_aurion.pdf
├── main.py                   # terminal chat entrypoint
├── langgraph.json            # LangGraph Studio config
└── requirements.txt
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis** (required for the semantic cache — needs the vector search module, plain `redis:latest` won't work)
   ```bash
   docker run -d --name redis-aurion -p 6379:6379 redis/redis-stack-server:latest
   ```

3. **Environment variables** — create a `.env` file:
   ```
   GROQ_API_KEY=...
   OPENAI_API_KEY=...
   ANTHROPIC_API_KEY=...
   GOOGLE_API_KEY=...
   TAVILY_API_KEY=...
   LANGSMITH_API_KEY=...      # optional, for tracing

   # Semantic cache
   REDIS_URL=redis://localhost:6379
   CACHE_ENABLED=true
   CACHE_SIMILARITY_THRESHOLD=0.90   # tune based on your embedding model's behavior
   CACHE_TTL_POLICY_SECONDS=86400     # policy-only answers (shared across users)
   CACHE_TTL_PERSONAL_SECONDS=1800     # answers involving personal/SQL data (per-user scope)

   # Evaluation (LLM-as-judge, ideally a different provider than the agent's)
   EVAL_JUDGE_PROVIDER=groq
   EVAL_JUDGE_MODEL=qwen/qwen3.8-27b
   ```

4. **Build the vector store** (run once, or after updating the policy manual)
   ```bash
   python -m src.rag.embeddings
   ```

## Running the app

**Web app (option 1)** 
```bash
python main.py
```

**Web app (option 2)** (run both from the project root, in separate terminals)
```bash
uvicorn app.backend.main:app --reload --port 8000
streamlit run app/frontend/streamlit_app.py
```
**LangGraph Studio** (visual graph debugger)
```bash
langgraph dev
```

## Evaluation

Run the full evaluation suite against the current dataset:
```bash
python -m src.eval.final_evaluation
```

This will:
1. Run every question in `src/eval/dataset.py` against the chatbot.
2. Score each answer on correctness, relevance, faithfulness, completeness and overall quality via an LLM-as-judge.
3. Classify low-scoring answers as **retrieval failure** (bad/insufficient context) or **generation failure** (good context, bad answer).
4. Save a detailed CSV and summary charts to `src/eval/results/`.
5. Print aggregate metrics, per-category breakdown, and the worst-scoring answers.

## Semantic cache

Before invoking the agent, incoming questions are embedded locally (`all-MiniLM-L6-v2`) and checked against Redis for a semantically similar prior question (cosine similarity ≥ `CACHE_SIMILARITY_THRESHOLD`). On a hit, the stored answer is returned immediately — no LLM, RAG or MCP call is made.

Cache entries are scoped to avoid leaking personal data between users:
- Answers that required querying the SQLite database (personal data) are cached **per employee** and expire quickly (`CACHE_TTL_PERSONAL_SECONDS`).
- Answers that only used the policy RAG tool are cached as **shared/public** entries with a longer TTL (`CACHE_TTL_POLICY_SECONDS`), since they don't depend on who's asking.

Check live cache performance (hit rate, average latency saved) while the backend is running:
```
GET http://127.0.0.1:8000/cache/stats
```

## Examples
Here are some prompt examples to ask the chatbot:

**1. Solo RAG (política, sin datos de empleado)**

"¿Cuántos días de permiso retribuido tengo si me caso?"
"¿Puedo traer a mi perro a la oficina todos los días?"
"¿Qué cubre el seguro médico de la empresa?"

**2. Solo SQL (dato concreto, sin necesidad de política)**

"¿En qué departamento trabaja Lucía Herrero Campos?"
"¿Cuál es el salario de Javier Ortega Beltrán?"
"¿Quién es el manager de Álvaro Cano Molina?"

**3. Híbridas — vacaciones según antigüedad (el caso central del proyecto)**

"¿Cuántos días de vacaciones le quedan a Marta Iglesias Roldán?"
"¿Cuántos días de vacaciones le quedan a Rubén... perdón, a Nuria Esteban Cid?" (antigüedad corta → 25 días, para comprobar que distingue tramos)
"¿Quién tiene más días de vacaciones pendientes, Cristina Vidal Serrano o Silvia Quintana Osorio?" (fuerza a comparar dos antigüedades distintas)

**4. Híbridas — mascotas**

"¿Puede Lucía Herrero Campos traer a su gato a la oficina?" (Tecnología → permitido)
"¿Puede Patricia Rincón Lozano traer a su mascota al trabajo?" (Comercial → no permitido, aunque en la BD tiene_mascota=0, así que también prueba que no invente que tiene mascota)

**5. Híbridas — teletrabajo**

"¿Puede Iván Cortés Aranda teletrabajar en remoto completo?" (Tecnología, antigüedad >1 año, rendimiento 4 → sí)
"¿Puede Adrián Vega Palomo trabajar en remoto?" (Atención al Cliente, junior → debería explicar que no, por política de presencialidad)

**6. Híbridas — hijos y conciliación**

"¿Ramón Cabrera Duque puede pedir horario flexible por sus hijos?" (tiene 3 hijos → comprobar que consulta numero_hijos y la política de <12 años, aunque la BD no guarda edad de los hijos — buen caso para ver si el agente es honesto sobre esa limitación)

**7. Híbridas — código de vestimenta**

"¿Qué código de vestimenta debe seguir Hugo Santamaría Vidal y en qué departamento trabaja?"

**8. Multi-fuente + cálculo (la más exigente)**

"Dame un resumen de la situación de Beatriz Salas Núñez: departamento, antigüedad, días de vacaciones disfrutados y pendientes, y si puede teletrabajar según su puesto."

**9. Búsqueda web (información general, ajena a Aurion Consulting)**

"¿Cuántos días de permiso por paternidad establece la ley en España actualmente?"
"¿Cuál es el salario mínimo interprofesional este año?"
"¿Qué dice el Estatuto de los Trabajadores sobre el periodo de prueba?"

**10. Riesgo de abandono (calculate_risk_leaving)**

"¿Cuál es el riesgo de abandono de Javier Ortega Beltrán?"
"¿Beatriz Salas Núñez tiene riesgo de irse de la empresa? ¿Por qué?"

**11. Riesgo de abandono agregado (calculate_risk_leaving_all)**

"¿Qué empleados tienen mayor riesgo de abandono en este momento?"
"Dame un listado de los empleados con riesgo de abandono alto, ordenados de mayor a menor."

**12. Caché semántica (misma intención, distinta redacción)**

Pregunta primero: "¿Cómo hay que ir vestido a la oficina?" → luego, en la misma sesión: "¿Qué ropa tengo que llevar a la oficina?" — la segunda debería resolverse como *cache hit*, sin invocar al LLM.

## Notes

- Conversation state is kept in memory (`MemorySaver`); it resets when the server restarts.
- MCP tools are restricted to read-only queries (`read_query`, `list_tables`, `describe_table`) — the agent cannot modify the database.
- Non-employee users only get access to the web search subagent, enforced at the middleware/tool-access level, not just via prompting.
- The semantic cache has no active invalidation mechanism, since there is no write tool in the current setup that could make a cached answer stale. If a write tool is added in the future, invalidation should hook into that write path.
- Both the evaluation pipeline and the semantic cache reuse the existing agent/subagent code directly (via a small `contextvars`-based instrumentation hook in `src/agent/agent.py`) rather than duplicating any chatbot logic.