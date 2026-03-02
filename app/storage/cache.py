"""Cache de respostas de LLM com hash SHA-256 e persistência SQLite."""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from app.config import CACHE_ENABLED, CACHE_TTL_HOURS

logger = logging.getLogger(__name__)


def compute_cache_key(provider: str, model: str, system_prompt: str,
                      messages: list[dict], temperature: float) -> str:
    """Gera hash SHA-256 determinístico para identificar uma chamada."""
    payload = json.dumps({
        "provider": provider,
        "model": model,
        "system_prompt": system_prompt,
        "messages": messages,
        "temperature": temperature,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


class CacheManager:
    """Gerencia cache de respostas com suporte a TTL e estatísticas."""

    def __init__(self, db):
        self.db = db
        self.hits = 0
        self.misses = 0
        self.enabled = CACHE_ENABLED

    def get(self, provider: str, model: str, system_prompt: str,
            messages: list[dict], temperature: float) -> dict | None:
        """
        Consulta cache. Retorna dict com 'content' e 'created_at' se hit,
        ou None se miss.
        """
        if not self.enabled:
            self.misses += 1
            return None

        cache_hash = compute_cache_key(provider, model, system_prompt, messages, temperature)
        result = self.db.get_cache(cache_hash)

        if result:
            self.hits += 1
            logger.info("Cache HIT para hash %s", cache_hash[:12])
            return {
                "content": result["response"],
                "created_at": result["created_at"],
            }

        self.misses += 1
        logger.warning("Cache MISS para hash %s", cache_hash[:12])
        return None

    def set(self, provider: str, model: str, system_prompt: str,
            messages: list[dict], temperature: float, response: str) -> None:
        """Armazena resposta no cache."""
        if not self.enabled:
            return

        cache_hash = compute_cache_key(provider, model, system_prompt, messages, temperature)

        expires_at = None
        if CACHE_TTL_HOURS > 0:
            expires_at = (
                datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS)
            ).strftime("%Y-%m-%d %H:%M:%S")

        self.db.set_cache(cache_hash, response, expires_at)
        logger.info("Cache SET para hash %s", cache_hash[:12])

    def get_stats(self) -> dict:
        """Retorna estatísticas da sessão de cache."""
        total = self.hits + self.misses
        rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": round(rate, 1),
        }

    def reset_stats(self) -> None:
        """Reseta contadores de hit/miss."""
        self.hits = 0
        self.misses = 0

    def cleanup(self) -> int:
        """Remove entradas expiradas."""
        return self.db.cleanup_expired_cache()
