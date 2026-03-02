"""Classe abstrata para adaptadores de LLM."""

from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """Interface abstrata para adaptadores de LLM."""

    @abstractmethod
    def generate(self, messages: list[dict], system_prompt: str = "",
                 temperature: float = 0.7) -> str:
        """
        Envia histórico de mensagens e retorna texto gerado.

        Args:
            messages: Lista de dicts com 'role' (user|assistant) e 'content'.
            system_prompt: Prompt de sistema (persona, contexto).
            temperature: Criatividade da resposta (0.0-1.0).

        Returns:
            Texto gerado pela LLM.

        Raises:
            LLMConnectionError: Falha de conexão com a API.
            LLMRateLimitError: Rate limit atingido.
            LLMResponseError: Resposta inválida ou vazia.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Retorna nome do modelo (ex: 'gemini-2.5-flash')."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna nome do provedor (ex: 'gemini')."""
        pass
