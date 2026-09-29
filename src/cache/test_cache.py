"""
Prueba manual aislada: python -m src.cache.test_cache
No usa el agente todavía -- solo valida que Redis/RedisVL responden bien
a preguntas semánticamente parecidas, con el mismo scope.
"""

from src.cache.semantic_cache import build_scope, lookup, store

scope = build_scope(empleado_id=42, verificado=True)

print("--- Guardando una respuesta ---")
store(
    question="¿A que hora tengo que llegar a la oficina?",
    answer="Depende del departamento: Comercial y Atención al Cliente van en business casual...",
    scope=scope,
    category="policy",
)

print("\n--- Consultando con una pregunta parafraseada (debería ser HIT) ---")
r1 = lookup("¿A que hora hay que llegar a la oficina?", scope=scope)
print(f"Hit: {r1.hit}  similarity: {r1.similarity_score}  latency_ms: {r1.latency_ms:.1f}")
if r1.hit:
    print(f"Respuesta cacheada: {r1.answer[:100]}...")

print("\n--- Consultando con otro scope (debería ser MISS, aunque la pregunta sea idéntica) ---")
otro_scope = build_scope(empleado_id=99, verificado=True)
r2 = lookup("¿A que hora tengo que llegar a la oficina?", scope=otro_scope)
print(f"Hit: {r2.hit}  similarity: {r2.similarity_score}  latency_ms: {r2.latency_ms:.1f}")

print("\n--- Consultando algo semánticamente distinto (debería ser MISS) ---")
r3 = lookup("¿Cuál es el horario de verano?", scope=scope)
print(f"Hit: {r3.hit}  similarity: {r3.similarity_score}  latency_ms: {r3.latency_ms:.1f}")