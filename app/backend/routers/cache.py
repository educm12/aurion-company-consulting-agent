"""
cache.py
Endpoint de solo lectura para inspeccionar el rendimiento de la caché
semántica (hit rate, latencia comparada) mientras pruebas la app.
"""

from fastapi import APIRouter

from src.cache.metrics import get_metrics

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats")
async def cache_stats():
    return get_metrics().summary()