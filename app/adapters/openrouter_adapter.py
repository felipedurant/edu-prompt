"""Adapter para OpenRouter (formato OpenAI)."""

import logging

from openai import OpenAI, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError

from app.adapters.base import LLMAdapter
from app.adapters.exceptions import (
    LLMAuthError,
    LLMConnectionError,
    LLMQuotaError,
    LLMRateLimitError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)


class OpenRouterAdapter(LLMAdapter):
    """Adapter para OpenRouter usando formato OpenAI."""

    def __init__(self, model: str, api_key: str):
        self._model_name = model
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=90.0,
        )

    def generate(self, messages: list[dict], system_prompt: str = "",
                 temperature: float = 0.7) -> str:
        try:
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})
            api_messages.extend(messages)

            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=api_messages,
                temperature=temperature,
                max_tokens=4096,
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMResponseError("OpenRouter retornou resposta vazia.")

            return content

        except RateLimitError as e:
            err_msg = str(e).lower()
            if "quota" in err_msg or "credits" in err_msg or "insufficient" in err_msg:
                logger.error("Quota esgotada OpenRouter: %s", e)
                raise LLMQuotaError(f"Cota OpenRouter esgotada: {e}") from e
            logger.error("Rate limit OpenRouter: %s", e)
            retry_after = None
            if hasattr(e, "response") and e.response is not None:
                retry_after_header = e.response.headers.get("retry-after")
                if retry_after_header:
                    retry_after = int(retry_after_header)
            raise LLMRateLimitError(retry_after=retry_after) from e
        except AuthenticationError as e:
            logger.error("Auth error OpenRouter: %s", e)
            raise LLMAuthError(f"Chave OpenRouter inválida: {e}") from e
        except APIConnectionError as e:
            logger.error("Conexão OpenRouter: %s", e)
            raise LLMConnectionError(f"Falha de conexão OpenRouter: {e}") from e
        except APIStatusError as e:
            err_msg = str(e).lower()
            if "quota" in err_msg or "credits" in err_msg or "insufficient" in err_msg:
                logger.error("Quota esgotada OpenRouter: %s", e)
                raise LLMQuotaError(f"Cota OpenRouter esgotada: {e}") from e
            logger.error("Erro API OpenRouter: %s", e)
            raise LLMConnectionError(f"Erro OpenRouter: {e}") from e
        except LLMResponseError:
            raise
        except Exception as e:
            logger.error("Erro inesperado OpenRouter: %s", e)
            raise LLMConnectionError(f"Erro inesperado OpenRouter: {e}") from e

    def get_model_name(self) -> str:
        return self._model_name

    def get_provider_name(self) -> str:
        return "openrouter"
