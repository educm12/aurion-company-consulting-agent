# Aurion Consulting Chatbot

An AI assistant for a fictional company (**Aurion Consulting**) that answers employee questions by combining structured data (SQLite) with unstructured company policy documentation (RAG), orchestrated through a multi-agent LangGraph pipeline.

## Overview

The assistant can answer questions that require combining two sources of information at once, for example:

- *"How many vacation days does Marta have left, based on her seniority?"*
- *"Can María bring her dog to the office, and how many vacation days has she taken this year?"*

It also verifies the identity of the person chatting: employees get full access (company policies + database + attrition risk), while non-employees are limited to general web search and company policies.

## Architecture

- **Orchestrator agent** — verifies the user's identity and routes to the right subagent(s), with a dynamic system prompt based on verification state.
- **Company subagent** — answers questions using:
  - **RAG** over the internal policy manual (ChromaDB + HuggingFace embeddings)
  - **SQLite database** (employees, departments, projects) via an **MCP** server
  - A custom attrition-risk heuristic tool
- **Web subagent** — general-purpose web search (Tavily) for questions unrelated to the company.
- **LangGraph** manages state, checkpointing (conversation memory) and conditional tool access.
- **LLM provider** is configurable per session: Groq, OpenAI, Anthropic or Google Gemini.

## Tech stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangChain + LangGraph |
| Vector store | ChromaDB |
| Structured data access | MCP (Model Context Protocol) over SQLite |
| Web search | Tavily |
| Backend API | FastAPI |
| Frontend | Streamlit |
| LLMs | Groq, OpenAI, Anthropic, Google Gemini |

## Project structure

```
my-chatbot-project/
├── app/                    # Web application (FastAPI + Streamlit)
│   ├── backend/
│   │   ├── main.py         # FastAPI entrypoint
│   │   ├── routers/        # /auth, /chat endpoints
│   │   └── services/       # agent lifecycle & business logic
│   └── frontend/
│       └── streamlit_app.py
├── src/
│   ├── agent/               # agent, tools, MCP wiring
│   └── rag/                 # embeddings + retriever
├── resources/
│   ├── aurion.db             # SQLite database
│   ├── aurion_schema.sql
│   ├── chroma_db/            # persisted vector store
│   └── manual_politicas_aurion.pdf
├── main.py                   # terminal chat entrypoint
├── langgraph.json             # LangGraph Studio config
└── requirements.txt
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables** — create a `.env` file:
   ```
   GROQ_API_KEY=...
   OPENAI_API_KEY=...
   ANTHROPIC_API_KEY=...
   GOOGLE_API_KEY=...
   TAVILY_API_KEY=...
   LANGSMITH_API_KEY=...      # optional, for tracing
   ```

3. **Build the vector store** (run once, or after updating the policy manual)
   ```bash
   python -m src.rag.embeddings
   ```

## Running the app

**Option A — Web app** (run both from the project root, in separate terminals)
```bash
uvicorn app.backend.main:app --reload --port 8000
streamlit run app/frontend/streamlit_app.py
```
**Option B — Terminal chat**
```bash
python main.py
```
**Option C — LangGraph Studio** (visual graph debugger)
```bash
langgraph dev
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

## Notes

- Conversation state is kept in memory (`MemorySaver`); it resets when the server restarts.
- MCP tools are restricted to read-only queries (`read_query`, `list_tables`, `describe_table`) — the agent cannot modify the database.
- Non-employee users only get access to the company policy and web search subagent, enforced at the middleware/tool-access level, not just via prompting.