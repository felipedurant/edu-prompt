"""Factory e utilitários para adaptadores de LLM."""

from app.config import GEMINI_API_KEY, GEMINI_PRO_MODEL, GROQ_API_KEY, DEEPSEEK_API_KEY
from app.adapters.base import LLMAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.groq_adapter import GroqAdapter
from app.adapters.deepseek_adapter import DeepSeekAdapter
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
    "DeepSeekAdapter",
    "get_adapter",
    "get_judge_adapter",
    "list_available",
    "LLMError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMAuthError",
    "LLMResponseError",
]


def get_adapter(provider: str) -> LLMAdapter:
    """
    Retorna adapter configurado para o provedor.

    Args:
        provider: Nome do provedor ('gemini', 'groq', 'deepseek').

    Raises:
        ValueError: Provedor desconhecido ou sem chave configurada.
    """
    adapters = {
        "gemini": GeminiAdapter,
        "groq": GroqAdapter,
        "deepseek": DeepSeekAdapter,
    }
    if provider not in adapters:
        raise ValueError(f"Provedor desconhecido: {provider}")
    if provider not in list_available():
        raise ValueError(f"Provedor '{provider}' sem chave configurada no .env")
    return adapters[provider]()


def get_judge_adapter() -> LLMAdapter:
    """Retorna adapter do Gemini 2.5 Pro (uso exclusivo como judge)."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY necessária para o LLM-as-judge.")
    return GeminiAdapter(model=GEMINI_PRO_MODEL)


def list_available() -> list[str]:
    """Retorna apenas provedores com chave configurada no .env."""
    available = []
    if GEMINI_API_KEY:
        available.append("gemini")
    if GROQ_API_KEY:
        available.append("groq")
    if DEEPSEEK_API_KEY:
        available.append("deepseek")
    return available
