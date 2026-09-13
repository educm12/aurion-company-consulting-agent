"""
tools.py
Define las tools que usará el agente: 
  - Tool RAG (manual de políticas) 
  - Tools MCP (base de datos SQLite de empleados/proyectos)
"""

import asyncio
from dotenv import load_dotenv

from langchain_core.tools.retriever import create_retriever_tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool

from src.rag.retriever import get_retriever

load_dotenv()

# ---------------------------------------------------------------------------
# 1. Tool RAG — consultas sobre política de empresa
# ---------------------------------------------------------------------------
def get_policy_tool():
    """
    Envuelve el retriever de Chroma como una Tool de LangChain para que el
    agente pueda consultar el manual interno de políticas de Aurion Consulting.
    """
    retriever = get_retriever(k=4)

    policy_tool = create_retriever_tool(
        retriever,
        name="consultar_politica_empresa",
        description=(
            "Útil para responder preguntas sobre las políticas internas de Aurion "
            "Consulting: vacaciones según antigüedad, teletrabajo, código de vestimenta, "
            "mascotas en la oficina, conciliación e hijos, permisos, horario laboral, "
            "beneficios, evaluaciones de desempeño, bonus, seguridad informática y "
            "cualquier otra norma o procedimiento interno de la empresa. "
            "No contiene datos concretos de empleados (usa la herramienta de base de "
            "datos para eso)."
        ),
    )
    return policy_tool


# ---------------------------------------------------------------------------
# 2. Tools MCP — consultas sobre empleados, departamentos y proyectos
# ---------------------------------------------------------------------------
# Se asume un servidor MCP de SQLite corriendo sobre resources/aurion.db,
# expuesto vía stdio (por ejemplo, el servidor oficial "mcp-server-sqlite"
# o uno propio en src/mcp_server/server.py).
MCP_SERVERS_CONFIG = {
    "aurion_sqlite": {
        "command": "uvx",
        "args": [
            "--with", "mcp<1.10",
            "mcp-server-sqlite",
            "--db-path",
            "resources/aurion.db",
        ],
        "transport": "stdio",
    }
}

async def get_sqlite_mcp_tools():
    """
    Conecta con el servidor MCP de SQLite y devuelve sus tools ya adaptadas
    al formato de LangChain (consultar tabla empleados, departamentos,
    proyectos, asignaciones_proyectos, etc.).
    """
    client = MultiServerMCPClient(MCP_SERVERS_CONFIG)
    mcp_tools = await client.get_tools()
    return mcp_tools


# ---------------------------------------------------------------------------
# 3. Tools Risk Leaving — calcula el riesgo de abandono de un empleado
# ---------------------------------------------------------------------------
from datetime import date
import sqlite3

from langchain_core.tools import tool

DB_PATH = "resources/aurion.db"


def _calcular_riesgo(employee: sqlite3.Row, project_count: int) -> dict:
    """
    Lógica pura de cálculo de riesgo (sin acceso a BD), reutilizable tanto
    para un empleado individual como para todos los empleados a la vez.
    """
    hire_date = date.fromisoformat(employee["fecha_contratacion"])
    years = (date.today() - hire_date).days / 365.25

    score = 0
    reasons = []

    if years <= 3:
        score += 20
        reasons.append("Poca antigüedad en la empresa")
    if employee["rendimiento_anual"] >= 4:
        score += 20
        reasons.append("Alto rendimiento (empleado atractivo para otras empresas)")
    if employee["bonus_anual"] < 2000:
        score += 10
        reasons.append("Bonus anual reducido")
    if employee["salario"] < 35000:
        score += 20
        reasons.append("Salario relativamente bajo")
    if project_count >= 3:
        score += 15
        reasons.append("Alta carga de proyectos")
    if employee["modalidad_trabajo"] == "Presencial":
        score += 10
        reasons.append("Trabajo totalmente presencial")

    score = min(score, 100)
    level = "BAJO" if score < 30 else "MEDIO" if score < 60 else "ALTO"

    return {
        "id": employee["id"],
        "nombre_completo": f"{employee['nombre']} {employee['apellidos']}",
        "score": score,
        "level": level,
        "reasons": reasons,
    }


def _project_counts(conn) -> dict:
    """id_empleado -> nº de proyectos asignados, en una sola query."""
    rows = conn.execute(
        """
        SELECT empleado_id, COUNT(*) AS total
        FROM asignaciones_proyectos
        GROUP BY empleado_id
        """
    ).fetchall()
    return {r["empleado_id"]: r["total"] for r in rows}


@tool
def calculate_risk_leaving(employee_id: int) -> str:
    """
    Estima el riesgo de abandono de UN empleado concreto, dado su ID,
    usando una heurística basada en antigüedad, rendimiento, salario,
    bonus, carga de proyectos y modalidad de trabajo.

    Usa esta tool solo cuando la pregunta se refiera a un empleado
    específico. Si la pregunta pide comparar, listar o rankear el riesgo
    de VARIOS o TODOS los empleados, usa en su lugar
    "calculate_risk_leaving_all".
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    employee = conn.execute(
        "SELECT * FROM empleados WHERE id = ?", (employee_id,)
    ).fetchone()

    if employee is None:
        conn.close()
        return f"No existe ningún empleado con ID {employee_id}."

    counts = _project_counts(conn)
    conn.close()

    r = _calcular_riesgo(employee, counts.get(employee_id, 0))

    return (
        f"Empleado: {r['nombre_completo']}\n"
        f"Riesgo estimado de abandono: {r['score']}% ({r['level']})\n\n"
        f"Factores detectados:\n" + "\n".join(f"- {x}" for x in r["reasons"])
    )


@tool
def calculate_risk_leaving_all(top_n: int = 5) -> str:
    """
    Calcula el riesgo de abandono de TODOS los empleados de la empresa y
    devuelve los `top_n` con mayor riesgo, ordenados de mayor a menor.

    Usa esta tool cuando la pregunta pida un ranking, comparación entre
    varios empleados, o los empleados con mayor/menor riesgo en general
    (por ejemplo: "¿quiénes son los 3 empleados con mayor riesgo de
    abandono?"). No la uses para consultar a un único empleado conocido:
    en ese caso usa "calculate_risk_leaving".

    Args:
        top_n: número de empleados a devolver (por defecto 5).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    employees = conn.execute("SELECT * FROM empleados").fetchall()
    counts = _project_counts(conn)
    conn.close()

    resultados = [
        _calcular_riesgo(e, counts.get(e["id"], 0)) for e in employees
    ]
    resultados.sort(key=lambda r: r["score"], reverse=True)

    top = resultados[:top_n]
    least = resultados[-top_n:]

    lineas_top = [
        f"{i+1}. {r['nombre_completo']} — {r['score']}% ({r['level']})"
        for i, r in enumerate(top)
    ]
    
    lineas_least = [
        f"{i+1}. {r['nombre_completo']} — {r['score']}% ({r['level']})"
        for i, r in enumerate(least)
    ]
    
    return f"Top {top_n} empleados con mayor riesgo de abandono:\n" + "\n".join(lineas_top) + \
            f"\n\nLos {top_n} empleados con menor riesgo de abandono:\n" + "\n".join(lineas_least)
            
            
# ---------------------------------------------------------------------------
# 4. Tools Search Web — busca información en la web
# ---------------------------------------------------------------------------
from typing import Dict, Any
from tavily import TavilyClient

tavily_client = TavilyClient()

@tool
def web_search(query: str) -> Dict[str, Any]:
    """
    Busca en internet información general sobre el mundo laboral, legislación
    o normativa que NO sea específica de Aurion Consulting.

    Úsala solo para preguntas de carácter general/externo, por ejemplo:
    - "¿Cuál es el salario mínimo interprofesional en España?"
    - "¿Es legal que una empresa contrate a un menor de edad?"
    - "¿Qué dice la ley sobre el teletrabajo en España?"
    - "¿Es habitual ir en chándal a una oficina?"

    NO uses esta tool si la pregunta es sobre las políticas, normas o
    procedimientos INTERNOS de Aurion Consulting (vacaciones, teletrabajo,
    código de vestimenta, mascotas, permisos, etc.) — para eso usa siempre
    "consultar_politica_empresa", nunca esta. Tampoco la uses para datos de
    empleados concretos (para eso usa las tools SQL).

    Si la pregunta mezcla ambas cosas (por ejemplo: "¿el código de
    vestimenta de mi empresa es más estricto que la media del sector?"),
    usa primero "consultar_politica_empresa" para el dato interno y esta
    tool solo para el contexto externo, y combina ambas respuestas.

    Args:
        query: consulta de búsqueda en lenguaje natural.

    Returns:
        Resultados de búsqueda web (títulos, snippets y URLs).
    """
    try:
        return tavily_client.search(query, max_results=5)
    except Exception as e:
        return {"error": f"No se pudo completar la búsqueda web: {e}"}


# ---------------------------------------------------------------------------
# 5. Tool de verificación de identidad — comprueba si el usuario es empleado
# ---------------------------------------------------------------------------
import sqlite3

from langchain.agents import AgentState
from langchain.messages import ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command

DB_PATH = "resources/aurion.db"


class EmployeeState(AgentState):
    """Estado propio del agente: si el usuario ha sido identificado como
    empleado, y con qué ID/nombre, para poder dar acceso condicional a
    las tools/subagentes."""
    verificado: bool
    empleado_id: int | None
    nombre_completo: str | None


@tool
def verificar_empleado(nombre: str, apellidos: str, runtime: ToolRuntime) -> Command:
    """
    Comprueba si la persona que escribe es un empleado de Aurion Consulting,
    buscando su nombre y apellidos en la base de datos.

    Debes llamar a esta tool en cuanto el usuario te dé su nombre y
    apellidos, antes de responder a cualquier otra consulta, si todavía
    no se ha verificado su identidad en esta conversación.

    Args:
        nombre: nombre de pila tal como lo ha dado el usuario.
        apellidos: apellidos tal como los ha dado el usuario.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    empleado = conn.execute(
        """
        SELECT id, nombre, apellidos
        FROM empleados
        WHERE LOWER(nombre) = LOWER(?) AND LOWER(apellidos) = LOWER(?)
        """,
        (nombre.strip(), apellidos.strip()),
    ).fetchone()
    conn.close()

    if empleado is None:
        return Command(
            update={
                "verificado": False,
                "empleado_id": None,
                "nombre_completo": None,
                "messages": [
                    ToolMessage(
                        f"No se ha encontrado a '{nombre} {apellidos}' en la "
                        "base de datos de empleados. Se le tratará como "
                        "usuario externo, con acceso solo a búsqueda web.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
            }
        )

    return Command(
        update={
            "verificado": True,
            "empleado_id": empleado["id"],
            "nombre_completo": f"{empleado['nombre']} {empleado['apellidos']}",
            "messages": [
                ToolMessage(
                    f"Identidad verificada: {empleado['nombre']} "
                    f"{empleado['apellidos']} (ID {empleado['id']}). "
                    "Acceso completo concedido.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
    
    
# ---------------------------------------------------------------------------
# 6. Punto único de entrada: todas las tools del agente
# ---------------------------------------------------------------------------
async def get_all_tools():
    """
    Devuelve la lista completa de tools que se pasarán al agente:
    la tool RAG + las tools MCP de la base de datos SQLite.
    """
    tools = [get_policy_tool(), calculate_risk_leaving, calculate_risk_leaving_all,
             web_search, verificar_empleado]
    
    sqlite_tools = await get_sqlite_mcp_tools()
    tools.extend(sqlite_tools)

    return tools


# ---------------------------------------------------------------------------
# Prueba rápida manual: python -m src.agent.tools
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    async def main():
        tools = await get_all_tools()
        print(f"Tools cargadas: {len(tools)}\n")
        for t in tools:
            print(f"- {t.name}: {t.description[:100]}")

    asyncio.run(main())
    