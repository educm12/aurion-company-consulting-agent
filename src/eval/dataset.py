"""
eval/dataset.py
Dataset de evaluación: preguntas representativas del chatbot de Aurion
Consulting, cubriendo casos simples, híbridos (RAG+SQL), ambiguos, fuera
de contexto y de información insuficiente.

Cada entrada tiene:
  - question: la pregunta a enviar al chatbot
  - expected_answer: respuesta de referencia (para correctness/completeness)
  - context: sección(es) del manual o dato de BD relevante, como referencia
    humana de qué debería haberse recuperado/usado (no es literalmente el
    contexto que devolverá el retriever, sirve de "ground truth" para juzgar
    si el retrieval fue bueno)
  - category: para poder desglosar resultados por tipo de caso
"""

DATASET = [
    {
        "id": "q01",
        "category": "simple_rag",
        "question": "¿Cuántos días de vacaciones tiene un empleado con más de diez años de antigüedad?",
        "expected_answer": "30 días de vacaciones anuales.",
        "context": "Manual, sección 6 (Vacaciones según antigüedad): 10 años o más -> 30 días.",
    },
    {
        "id": "q02",
        "category": "simple_rag",
        "question": "¿Qué código de vestimenta debe seguir el departamento Comercial?",
        "expected_answer": "Vestimenta business casual en todo momento, por el contacto frecuente con clientes.",
        "context": "Manual, sección 9 (Código de vestimenta): Comercial y Atención al Cliente -> business casual.",
    },
    {
        "id": "q03",
        "category": "simple_sql",
        "question": "¿Cuál es el salario de Javier Ortega Beltrán?",
        "expected_answer": "74000 euros brutos anuales.",
        "context": "Tabla empleados, fila de Javier Ortega Beltrán, columna salario.",
    },
    {
        "id": "q04",
        "category": "simple_sql",
        "question": "¿Quién es el manager directo de Álvaro Cano Molina?",
        "expected_answer": "Marta Iglesias Roldán.",
        "context": "Tabla empleados, fila de Álvaro Cano Molina, columna manager.",
    },
    {
        "id": "q05",
        "category": "hybrid",
        "question": "¿Cuántos días de vacaciones le quedan a Marta Iglesias Roldán?",
        "expected_answer": (
            "Marta tiene más de 10 años de antigüedad (contratada en 2015), por lo que "
            "le corresponden 30 días anuales; hay que restarle los días que ya ha "
            "disfrutado según la base de datos para saber cuántos le quedan."
        ),
        "context": (
            "Manual sección 6 (30 días si >=10 años de antigüedad) + tabla empleados "
            "(fecha_contratacion y dias_vacaciones_disfrutados de Marta Iglesias Roldán)."
        ),
    },
    {
        "id": "q06",
        "category": "hybrid",
        "question": "¿Puede Lucía Herrero Campos traer a su gato a la oficina?",
        "expected_answer": (
            "Sí: Lucía trabaja en Tecnología, uno de los departamentos con zona "
            "pet-friendly, y según la base de datos tiene un gato."
        ),
        "context": (
            "Manual sección 10 (mascotas permitidas en Tecnología y Operaciones, no en "
            "Comercial/Legal/Finanzas/Atención al Cliente) + tabla empleados "
            "(departamento y tiene_mascota/tipo_mascota de Lucía)."
        ),
    },
    {
        "id": "q07",
        "category": "hybrid",
        "question": "¿Puede Iván Cortés Aranda teletrabajar en modalidad remota completa?",
        "expected_answer": (
            "Sí, es plausible: trabaja en Tecnología, lleva más de un año en la empresa "
            "y su rendimiento anual es 4, lo que cumple los requisitos de la política."
        ),
        "context": (
            "Manual sección 5 (remoto para Tecnología/Marketing/Finanzas si >1 año y "
            "rendimiento >=3) + tabla empleados (departamento, fecha_contratacion, "
            "rendimiento_anual de Iván)."
        ),
    },
    {
        "id": "q08",
        "category": "hybrid_complex",
        "question": (
            "Dame un resumen de Beatriz Salas Núñez: departamento, antigüedad, "
            "vacaciones disfrutadas y pendientes, y si puede teletrabajar."
        ),
        "expected_answer": (
            "Beatriz es Directora de RRHH, contratada en 2016 (más de 10 años de "
            "antigüedad, 30 días de vacaciones), con los días disfrutados que indique "
            "la base de datos restados de esos 30. RRHH puede acceder a modalidad "
            "híbrida (hasta 2 días/semana) tras el primer año, no a remoto completo "
            "salvo aprobación especial."
        ),
        "context": "Manual secciones 5 y 6 + tabla empleados, fila de Beatriz Salas Núñez.",
    },
    {
        "id": "q09",
        "category": "ambiguous",
        "question": "¿Puedo pedir más días de vacaciones si tengo hijos?",
        "expected_answer": (
            "No: tener hijos no aumenta los días de vacaciones. La política de "
            "conciliación para empleados con hijos menores de 12 años da acceso a "
            "horario flexible, no a más vacaciones."
        ),
        "context": "Manual sección 11 (conciliación e hijos) vs sección 6 (vacaciones por antigüedad, sin mención a hijos).",
    },
    {
        "id": "q10",
        "category": "out_of_context",
        "question": "¿Cuál es la capital de Australia?",
        "expected_answer": (
            "No es una pregunta relacionada con Aurion Consulting; el chatbot debería "
            "decir que no puede ayudar con eso o derivarlo a la tool de búsqueda web, "
            "no inventar ni responder como si fuera parte de su dominio."
        ),
        "context": None,
    },
    {
        "id": "q11",
        "category": "insufficient_info",
        "question": "¿Cuántos días de vacaciones tiene Pedro García?",
        "expected_answer": (
            "No existe ningún empleado llamado Pedro García en la base de datos; el "
            "chatbot debería decirlo explícitamente, no inventar un dato."
        ),
        "context": "Tabla empleados no contiene ningún 'Pedro García'.",
    },
    {
        "id": "q12",
        "category": "insufficient_info",
        "question": "¿Cuál es la política de la empresa sobre el uso de bicicletas para ir a trabajar?",
        "expected_answer": (
            "El manual no cubre ninguna política específica sobre bicicletas; el "
            "chatbot debería decir que no tiene esa información en vez de inventarla."
        ),
        "context": "El manual no menciona bicicletas en ninguna sección.",
    },
    {
        "id": "q13",
        "category": "ambiguous",
        "question": "¿Y cuántos hijos tiene?",
        "expected_answer": (
            "La pregunta no especifica de quién se habla; el chatbot debería pedir "
            "aclaración (nombre del empleado) en vez de asumir o inventar una persona."
        ),
        "context": None,
    },
    {
        "id": "q14",
        "category": "simple_rag",
        "question": "¿Cómo se calcula el bonus anual variable de un empleado?",
        "expected_answer": (
            "Es un porcentaje del salario bruto según el rendimiento anual (0 a 4), "
            "de 0% (rendimiento 1) hasta 15% (rendimiento 5)."
        ),
        "context": "Manual, sección 15 (Evaluaciones de desempeño y promociones).",
    },
    {
        "id": "q15",
        "category": "hybrid_complex",
        "question": (
            "¿Quién tiene más días de vacaciones pendientes, Cristina Vidal Serrano o "
            "Silvia Quintana Osorio?"
        ),
        "expected_answer": (
            "Depende de su antigüedad (Cristina >10 años -> 30 días; Silvia entre 2 y 5 "
            "años -> 25 días) y de los días ya disfrutados según la base de datos; hay "
            "que calcular ambos y comparar."
        ),
        "context": "Manual sección 6 + tabla empleados, filas de ambas empleadas.",
    },
    {
        "id": "q16",
        "category": "simple_rag",
        "question": "¿Cuántos días de permiso retribuido tengo si me caso?",
        "expected_answer": "15 días naturales.",
        "context": "Manual, sección 7 (Permisos retribuidos): matrimonio o pareja de hecho -> 15 días naturales.",
    },
]


def load_dataset() -> list[dict]:
    return DATASET