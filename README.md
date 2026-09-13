# Aurion Consulting Chatbot

An AI assistant for a fictional company (**Aurion Consulting**) that answers employee questions by combining structured data (SQLite) with unstructured company policy documentation (RAG), orchestrated through a multi-agent LangGraph pipeline.

## Overview

The assistant can answer questions that require combining two sources of information at once, for example:

- *"How many vacation days does Marta have left, based on her seniority?"*
- *"Can María bring her dog to the office, and how many vacation days has she taken this year?"*

It also verifies the identity of the person chatting: employees get full access (company policies + database + attrition risk), while non-employees are limited to general web search.

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

## Notes

- Conversation state is kept in memory (`MemorySaver`); it resets when the server restarts.
- MCP tools are restricted to read-only queries (`read_query`, `list_tables`, `describe_table`) — the agent cannot modify the database.
- Non-employee users only get access to the web search subagent, enforced at the middleware/tool-access level, not just via prompting.