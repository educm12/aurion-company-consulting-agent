"""
config.py
Configuración de la caché semántica, vía variables de entorno.
"""

import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_INDEX_NAME = os.getenv("CACHE_INDEX_NAME", "aurion_semantic_cache")

# El usuario piensa en "similitud" (más alto = más parecido); RedisVL
# trabaja en distancia coseno (más bajo = más parecido). Se convierte aquí,
# una sola vez, para que el resto del código no tenga que hacer la resta.
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.90"))
CACHE_DISTANCE_THRESHOLD = 1 - CACHE_SIMILARITY_THRESHOLD

EMBEDDING_MODEL = os.getenv("CACHE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

CACHE_TTL_POLICY_SECONDS = int(os.getenv("CACHE_TTL_POLICY_SECONDS", "86400"))     # 24h, política pura
CACHE_TTL_PERSONAL_SECONDS = int(os.getenv("CACHE_TTL_PERSONAL_SECONDS", "1800"))  # 30min, datos personales