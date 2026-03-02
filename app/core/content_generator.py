"""Orquestrador de geração de conteúdo educacional."""

import logging
import time

from app.config import DEFAULT_PROMPT_VERSION, DEFAULT_TEMPERATURE, CONTENT_TYPES
from app.adapters.base import LLMAdapter
from app.adapters.exceptions import LLMResponseError
from app.core.prompt_engine import PromptEngine
from app.storage.cache import CacheManager

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Orquestra geração de conteúdo usando PromptEngine, adapters e cache."""

    def __init__(self, engine: PromptEngine, cache: CacheManager):
        self.engine = engine
        self.cache = cache

    def generate_single(self, adapter: LLMAdapter, profile: dict, topic: str,
                        content_type: str, version: str = DEFAULT_PROMPT_VERSION) -> dict:
        """
        Gera um único tipo de conteúdo.

        Returns:
            Dict com 'content', 'source' ('api'|'cache'), 'elapsed',
            'provider', 'model', 'content_type', 'version'.
        """
        system, user = self.engine.build_prompt(profile, topic, content_type, version)
        messages = [{"role": "user", "content": user}]

        provider = adapter.get_provider_name()
        model = adapter.get_model_name()

        # Consulta cache
        cached = self.cache.get(provider, model, system, messages, DEFAULT_TEMPERATURE)
        if cached:
            return {
                "content": cached["content"],
                "source": "cache",
                "elapsed": 0,
                "cached_at": cached["created_at"],
                "provider": provider,
                "model": model,
                "content_type": content_type,
                "version": version,
            }

        # Chamada à API
        start = time.time()
        try:
            content = adapter.generate(
                messages=messages,
                system_prompt=system,
                temperature=DEFAULT_TEMPERATURE,
            )
        except LLMResponseError:
            logger.warning("Resposta vazia para %s/%s, retry...", provider, content_type)
            content = adapter.generate(
                messages=messages,
                system_prompt=system,
                temperature=DEFAULT_TEMPERATURE,
            )
        elapsed = time.time() - start

        # Salva no cache
        self.cache.set(provider, model, system, messages, DEFAULT_TEMPERATURE, content)

        return {
            "content": content,
            "source": "api",
            "elapsed": round(elapsed, 1),
            "provider": provider,
            "model": model,
            "content_type": content_type,
            "version": version,
        }

    def generate_all_types(self, adapter: LLMAdapter, profile: dict, topic: str,
                           version: str = DEFAULT_PROMPT_VERSION) -> dict[str, dict]:
        """
        Gera todos os 4 tipos de conteúdo sequencialmente.

        Returns:
            Dict[content_type, result_dict]
        """
        results = {}
        for ct in CONTENT_TYPES:
            results[ct] = self.generate_single(adapter, profile, topic, ct, version)
        return results
