"""Factory e utilitários para adaptadores de LLM."""

import os

from app.config import GEMINI_API_KEY, GEMINI_PRO_MODEL, MODEL_REGISTRY
from app.adapters.base import LLMAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.groq_adapter import GroqAdapter
from app.adapters.openrouter_adapter import OpenRouterAdapter
from app.adapters.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMAuthError,
    LLMResponseError,
)

__all__ = [
    "LLMAdapter",
    "GeminiAdapter",
    "GroqAdapter",
    "OpenRouterAdapter",
    "get_adapter",
    "get_judge_adapter",
    "list_available",
    "LLMError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMAuthError",
    "LLMResponseError",
]


def get_adapter(model_key: str) -> LLMAdapter:
    """
    Retorna adapter configurado para o modelo.

    Args:
        model_key: Chave do modelo no MODEL_REGISTRY.

    Raises:
        ValueError: Modelo desconhecido ou sem chave configurada.
    """
    if model_key not in MODEL_REGISTRY:
        raise ValueError(f"Modelo desconhecido: {model_key}")

    entry = MODEL_REGISTRY[model_key]
    api_key = os.getenv(entry["api_key_env"])
    if not api_key:
        raise ValueError(f"Modelo '{model_key}' sem chave configurada no .env ({entry['api_key_env']})")

    provider = entry["provider"]
    model_id = entry["model_id"]

    if provider == "gemini":
        return GeminiAdapter(model=model_id, api_key=api_key)
    elif provider == "groq":
        return GroqAdapter(model=model_id, api_key=api_key)
    elif provider == "openrouter":
        return OpenRouterAdapter(model=model_id, api_key=api_key)
    else:
        raise ValueError(f"Provider desconhecido no registry: {provider}")


def get_judge_adapter() -> LLMAdapter:
    """Retorna adapter do Gemini 2.5 Pro (uso exclusivo como judge)."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY necessária para o LLM-as-judge.")
    return GeminiAdapter(model=GEMINI_PRO_MODEL)


def list_available() -> list[str]:
    """Retorna model keys cujo API key está configurada no .env."""
    available = []
    for key, entry in MODEL_REGISTRY.items():
        if os.getenv(entry["api_key_env"]):
            available.append(key)
    return available
