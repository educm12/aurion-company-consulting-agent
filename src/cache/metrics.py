"""
metrics.py
Contadores simples en memoria para medir el impacto real de la caché:
hit rate, latencia comparada, y llamadas al LLM/RAG/MCP evitadas.
No es persistente -- se resetea al reiniciar el backend, igual que el
resto del estado en memoria del proyecto (MemorySaver, _agents, etc.).
"""

import statistics
from dataclasses import dataclass, field


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    hit_latencies_ms: list[float] = field(default_factory=list)
    miss_latencies_ms: list[float] = field(default_factory=list)  # tiempo del flujo normal (agente completo)

    def record_hit(self, latency_ms: float):
        self.hits += 1
        self.hit_latencies_ms.append(latency_ms)

    def record_miss(self, latency_ms: float):
        self.misses += 1
        self.miss_latencies_ms.append(latency_ms)

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0

    def summary(self) -> dict:
        avg_hit = statistics.mean(self.hit_latencies_ms) if self.hit_latencies_ms else None
        avg_miss = statistics.mean(self.miss_latencies_ms) if self.miss_latencies_ms else None
        return {
            "total_requests": self.total,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "avg_hit_latency_ms": round(avg_hit, 1) if avg_hit else None,
            "avg_miss_latency_ms": round(avg_miss, 1) if avg_miss else None,
            "avg_latency_saved_ms": round(avg_miss - avg_hit, 1) if (avg_hit and avg_miss) else None,
        }


_metrics = CacheMetrics()


def get_metrics() -> CacheMetrics:
    return _metrics