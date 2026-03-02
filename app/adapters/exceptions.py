"""Exceções customizadas para adaptadores de LLM."""


class LLMError(Exception):
    """Base para erros de LLM."""
    pass


class LLMConnectionError(LLMError):
    """Falha de conexão (timeout, DNS, etc.)."""
    pass


class LLMRateLimitError(LLMError):
    """Rate limit atingido (429)."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        msg = f"Rate limit. Retry after: {retry_after}s" if retry_after else "Rate limit."
        super().__init__(msg)


class LLMAuthError(LLMError):
    """Chave inválida ou expirada (401/403)."""
    pass


class LLMResponseError(LLMError):
    """Resposta inválida, vazia ou truncada."""
    pass
