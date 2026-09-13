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
    
            
"""
1. Solo RAG (política, sin datos de empleado)

"¿Cuántos días de permiso retribuido tengo si me caso?"
"¿Puedo traer a mi perro a la oficina todos los días?"
"¿Qué cubre el seguro médico de la empresa?"

2. Solo SQL (dato concreto, sin necesidad de política)

"¿En qué departamento trabaja Lucía Herrero Campos?"
"¿Cuál es el salario de Javier Ortega Beltrán?"
"¿Quién es el manager de Álvaro Cano Molina?"

3. Híbridas — vacaciones según antigüedad (el caso central del proyecto)

"¿Cuántos días de vacaciones le quedan a Marta Iglesias Roldán?"
"¿Cuántos días de vacaciones le quedan a Rubén... perdón, a Nuria Esteban Cid?" (antigüedad corta → 25 días, para comprobar que distingue tramos)
"¿Quién tiene más días de vacaciones pendientes, Cristina Vidal Serrano o Silvia Quintana Osorio?" (fuerza a comparar dos antigüedades distintas)

4. Híbridas — mascotas

"¿Puede Lucía Herrero Campos traer a su gato a la oficina?" (Tecnología → permitido)
"¿Puede Patricia Rincón Lozano traer a su mascota al trabajo?" (Comercial → no permitido, aunque en la BD tiene_mascota=0, así que también prueba que no invente que tiene mascota)

5. Híbridas — teletrabajo

"¿Puede Iván Cortés Aranda teletrabajar en remoto completo?" (Tecnología, antigüedad >1 año, rendimiento 4 → sí)
"¿Puede Adrián Vega Palomo trabajar en remoto?" (Atención al Cliente, junior → debería explicar que no, por política de presencialidad)

6. Híbridas — hijos y conciliación

"¿Ramón Cabrera Duque puede pedir horario flexible por sus hijos?" (tiene 3 hijos → comprobar que consulta numero_hijos y la política de <12 años, aunque la BD no guarda edad de los hijos — buen caso para ver si el agente es honesto sobre esa limitación)

7. Híbridas — código de vestimenta

"¿Qué código de vestimenta debe seguir Hugo Santamaría Vidal y en qué departamento trabaja?"

8. Multi-fuente + cálculo (la más exigente)

"Dame un resumen de la situación de Beatriz Salas Núñez: departamento, antigüedad, días de vacaciones disfrutados y pendientes, y si puede teletrabajar según su puesto."
"""