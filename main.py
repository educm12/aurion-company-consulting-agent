"""
main.py
Punto de entrada del chatbot de Aurion Consulting (arquitectura multi-agente
con verificación de identidad). El asistente inicia la conversación pidiendo
nombre y apellidos antes de que el usuario escriba nada.
"""

import asyncio
import uuid

from src.agent.agent import build_agent

EXIT_COMMANDS = {"salir", "exit", "quit"}

# Mensaje "disparador" interno: no lo escribe el usuario, solo sirve para
# que el agente tome la iniciativa y salude/pida identificación según su
# system prompt dinámico (estado no verificado al arrancar).
KICKOFF_MESSAGE = "[INICIO_DE_CONVERSACION]"


async def chat_loop():
    print("Inicializando agente (conectando con MCP y cargando el modelo)...")
    agent = await build_agent()

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # Primer turno: el agente habla primero, sin input del usuario.
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": KICKOFF_MESSAGE}]},
        config=config,
    )
    print(f"\nAsistente: {result['messages'][-1].content}\n")

    while True:
        pregunta = input("Tú: ").strip()

        if not pregunta:
            continue
        if pregunta.lower() in EXIT_COMMANDS:
            print("Asistente: ¡Hasta luego!")
            break

        try:
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": pregunta}]},
                config=config,
            )
        except Exception as e:
            print(f"Asistente: Ha ocurrido un error al procesar tu pregunta: {e}\n")
            continue

        respuesta = result["messages"][-1].content
        print(f"Asistente: {respuesta}\n")


def main():
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nAsistente: ¡Hasta luego!")


if __name__ == "__main__":
    main()
    
            