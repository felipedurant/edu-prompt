"""Adapter para Google Gemini (SDK google-genai)."""

import logging

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
from google.genai.types import HttpOptions

from app.config import GEMINI_API_KEY, GEMINI_FLASH_MODEL
from app.adapters.base import LLMAdapter
from app.adapters.exceptions import (
    LLMAuthError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)


class GeminiAdapter(LLMAdapter):
    """Adapter para Google Gemini usando SDK google-genai."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self._model_name = model or GEMINI_FLASH_MODEL
        self._client = genai.Client(
            api_key=api_key or GEMINI_API_KEY,
            http_options=HttpOptions(timeout=90_000),
        )

    def generate(self, messages: list[dict], system_prompt: str = "",
                 temperature: float = 0.7) -> str:
        try:
            # Converter formato messages[] para formato Gemini contents[]
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=msg["content"])],
                ))

            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_prompt if system_prompt else None,
            )

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=config,
            )

            if not response.text:
                raise LLMResponseError("Gemini retornou resposta vazia.")

            return response.text

        except ClientError as e:
            status = getattr(e, "status", None)
            if status == 429:
                logger.error("Rate limit Gemini: %s", e)
                raise LLMRateLimitError() from e
            elif status in (401, 403):
                logger.error("Auth error Gemini: %s", e)
                raise LLMAuthError(f"Chave Gemini inválida: {e}") from e
            logger.error("Client error Gemini: %s", e)
            raise LLMConnectionError(f"Erro Gemini: {e}") from e
        except ServerError as e:
            logger.error("Server error Gemini: %s", e)
            raise LLMConnectionError(f"Erro servidor Gemini: {e}") from e
        except APIError as e:
            logger.error("Erro API Gemini: %s", e)
            raise LLMConnectionError(f"Erro Gemini: {e}") from e
        except LLMResponseError:
            raise
        except Exception as e:
            logger.error("Erro inesperado Gemini: %s", e)
            raise LLMConnectionError(f"Erro inesperado Gemini: {e}") from e

    def get_model_name(self) -> str:
        return self._model_name

    def get_provider_name(self) -> str:
        return "gemini"
