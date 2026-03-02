"""Adapter para DeepSeek (formato OpenAI)."""

import logging

from openai import OpenAI, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from app.adapters.base import LLMAdapter
from app.adapters.exceptions import (
    LLMAuthError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)


class DeepSeekAdapter(LLMAdapter):
    """Adapter para DeepSeek usando formato OpenAI."""

    def __init__(self):
        self._model_name = DEEPSEEK_MODEL
        self._client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
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
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMResponseError("DeepSeek retornou resposta vazia.")

            return content

        except RateLimitError as e:
            logger.error("Rate limit DeepSeek: %s", e)
            retry_after = None
            if hasattr(e, "response") and e.response is not None:
                retry_after_header = e.response.headers.get("retry-after")
                if retry_after_header:
                    retry_after = int(retry_after_header)
            raise LLMRateLimitError(retry_after=retry_after) from e
        except AuthenticationError as e:
            logger.error("Auth error DeepSeek: %s", e)
            raise LLMAuthError(f"Chave DeepSeek inválida: {e}") from e
        except APIConnectionError as e:
            logger.error("Conexão DeepSeek: %s", e)
            raise LLMConnectionError(f"Falha de conexão DeepSeek: {e}") from e
        except APIStatusError as e:
            logger.error("Erro API DeepSeek: %s", e)
            raise LLMConnectionError(f"Erro DeepSeek: {e}") from e
        except LLMResponseError:
            raise
        except Exception as e:
            logger.error("Erro inesperado DeepSeek: %s", e)
            raise LLMConnectionError(f"Erro inesperado DeepSeek: {e}") from e

    def get_model_name(self) -> str:
        return self._model_name

    def get_provider_name(self) -> str:
        return "deepseek"
