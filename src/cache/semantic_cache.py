"""
semantic_cache.py
Caché semántica sobre Redis + RedisVL. Filtra por "scope" (empleado_id o
"public") con coincidencia EXACTA, y por similitud semántica dentro de ese
scope -- así nunca se devuelve a un usuario la respuesta cacheada de otro.

No se integra todavía en el flujo del agente: este
módulo solo expone lookup()/store() y se puede probar de forma aislada.
"""

import time
from dataclasses import dataclass

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import HFTextVectorizer

from src.cache.config import (
    CACHE_DISTANCE_THRESHOLD,
    CACHE_INDEX_NAME,
    EMBEDDING_MODEL,
    REDIS_URL,
)

_vectorizer = HFTextVectorizer(EMBEDDING_MODEL)

_cache = SemanticCache(
    name=CACHE_INDEX_NAME,
    redis_url=REDIS_URL,
    distance_threshold=CACHE_DISTANCE_THRESHOLD,
    ttl=3600,  # se reseta cada 1h si no se especifíca
    vectorizer=_vectorizer,
    filterable_fields=[
        {"name": "scope", "type": "tag"},      # emp:<id> o "public" -- filtro EXACTO
        {"name": "category", "type": "tag"},    # opcional, para políticas de TTL futuras
    ],
)


@dataclass
class CacheLookupResult:
    hit: bool
    answer: str | None
    similarity_score: float | None   # 1 - distancia, para hablar en términos de similitud
    latency_ms: float


def build_scope(empleado_id: int | None, verificado: bool) -> str:
    """Scope EXACTO (no semántico) que aísla la caché por identidad, para
    que la caché nunca mezcle respuestas de un usuario con las de otro."""
    if verificado and empleado_id is not None:
        return f"emp:{empleado_id}"
    return "public"


def lookup(question: str, scope: str) -> CacheLookupResult:
    from redisvl.query.filter import Tag

    start = time.perf_counter()
    results = _cache.check(
        prompt=question,
        filter_expression=(Tag("scope") == scope),
        num_results=1,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    if not results:
        return CacheLookupResult(hit=False, answer=None, similarity_score=None, latency_ms=latency_ms)

    top = results[0]
    similarity = 1 - top["vector_distance"]
    return CacheLookupResult(
        hit=True,
        answer=top["response"],
        similarity_score=round(similarity, 4),
        latency_ms=latency_ms,
    )


def store(question: str, answer: str, scope: str, category: str | None = None, ttl: int | None = None) -> None:
    _cache.store(
        prompt=question,
        response=answer,
        filters={"scope": scope, "category": category or "unknown"},
        ttl=ttl  # None -> usa el TTL global por defecto de la instancia
    )