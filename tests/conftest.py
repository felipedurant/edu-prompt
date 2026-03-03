"""Fixtures compartilhadas para testes do EduPrompt."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.adapters.base import LLMAdapter
from app.core.prompt_engine import PromptEngine
from app.storage.database import Database
from app.storage.cache import CacheManager


# ─── Perfis de teste ────────────────────────────────────


@pytest.fixture
def profile_visual():
    """Perfil de aluno visual (adolescente, intermediário)."""
    return {
        "id": "test_ana_16_inte_visua_abc123",
        "nome": "Ana",
        "idade": 16,
        "nivel": "intermediario",
        "estilo": "visual",
        "contexto": "estudante de biologia",
    }


@pytest.fixture
def profile_cinestesico():
    """Perfil de aluno cinestésico (criança, iniciante)."""
    return {
        "id": "test_pedro_10_inic_cines_def456",
        "nome": "Pedro",
        "idade": 10,
        "nivel": "iniciante",
        "estilo": "cinestesico",
        "contexto": "",
    }


@pytest.fixture
def profile_auditivo():
    """Perfil de aluno auditivo (adulto, avançado)."""
    return {
        "id": "test_maria_30_avan_audit_ghi789",
        "nome": "Maria",
        "idade": 30,
        "nivel": "avancado",
        "estilo": "auditivo",
        "contexto": "professora de química",
    }


@pytest.fixture
def profile_leitura():
    """Perfil de aluno leitura-escrita (jovem adulto, intermediário)."""
    return {
        "id": "test_joao_20_inte_leitu_jkl012",
        "nome": "Joao",
        "idade": 20,
        "nivel": "intermediario",
        "estilo": "leitura-escrita",
        "contexto": "",
    }


# ─── Mock adapter ───────────────────────────────────────


class MockAdapter(LLMAdapter):
    """Adapter simulado para testes (não chama API real)."""

    def __init__(self, response: str = "Resposta de teste.", provider: str = "mock", model: str = "mock-v1"):
        self._response = response
        self._provider = provider
        self._model = model
        self.call_count = 0

    def generate(self, messages: list[dict], system_prompt: str = "",
                 temperature: float = 0.7) -> str:
        self.call_count += 1
        return self._response

    def get_model_name(self) -> str:
        return self._model

    def get_provider_name(self) -> str:
        return self._provider


@pytest.fixture
def mock_adapter():
    """Adapter mock que retorna resposta fixa."""
    return MockAdapter()


@pytest.fixture
def mock_adapter_factory():
    """Factory para criar adapters mock com respostas personalizadas."""
    def factory(response="Resposta de teste.", provider="mock", model="mock-v1"):
        return MockAdapter(response=response, provider=provider, model=model)
    return factory


# ─── Database de teste ──────────────────────────────────


@pytest.fixture
def temp_db():
    """Database SQLite temporário (apagado após o teste)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path=db_path)
    yield db

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


# ─── Cache de teste ─────────────────────────────────────


@pytest.fixture
def temp_cache(temp_db):
    """CacheManager com banco temporário."""
    return CacheManager(temp_db)


# ─── PromptEngine ───────────────────────────────────────


@pytest.fixture
def engine():
    """Instância do PromptEngine."""
    return PromptEngine()


# ─── Profiles JSON temporário ───────────────────────────


@pytest.fixture
def temp_profiles_dir(tmp_path, monkeypatch):
    """Diretório temporário para profiles.json."""
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("app.core.profiles.PROFILES_PATH", profiles_path)
    return profiles_path


# ─── Constantes de teste ────────────────────────────────


SAMPLE_TOPIC = "Fotossintese"
CONTENT_TYPES = ("conceptual", "practical", "reflection", "visual")
VERSIONS = ("v1", "v2")
STYLES = ("visual", "auditivo", "leitura-escrita", "cinestesico")
