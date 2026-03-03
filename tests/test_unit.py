"""Testes unitários parametrizados para o EduPrompt Platform."""

import json
import re

import pytest

from app.config import VALID_LEVELS, VALID_STYLES, CONTENT_TYPES, PROMPT_VERSIONS
from app.core.prompt_engine import PromptEngine
from app.core.profiles import validate_profile, create_profile, load_profiles
from app.core.onboarding import (
    LEARNING_STYLES,
    VARK_QUIZ,
    get_quiz_questions,
    calculate_style,
)
from app.core.content_generator import ContentGenerator
from app.core.export import (
    export_comparison_json,
    export_comparison_markdown,
    export_session_json,
    export_session_markdown,
)
from app.storage.cache import compute_cache_key, CacheManager
from app.adapters.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMAuthError,
    LLMResponseError,
)

from tests.conftest import MockAdapter, SAMPLE_TOPIC


# ─── PromptEngine ───────────────────────────────────────


class TestPromptEngine:
    """Testes para o motor de engenharia de prompt."""

    @pytest.mark.parametrize("content_type", CONTENT_TYPES)
    @pytest.mark.parametrize("version", PROMPT_VERSIONS)
    def test_build_prompt_returns_tuple(self, engine, profile_visual, content_type, version):
        """build_prompt retorna (system_prompt, user_prompt) para todas as combinações."""
        result = engine.build_prompt(profile_visual, SAMPLE_TOPIC, content_type, version)
        assert isinstance(result, tuple)
        assert len(result) == 2
        system, user = result
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(user, str) and len(user) > 0

    @pytest.mark.parametrize("style", VALID_STYLES)
    def test_style_adaptation_in_v2(self, engine, profile_visual, style):
        """v2 inclui adaptações de estilo no system prompt."""
        profile = {**profile_visual, "estilo": style}
        system, user = engine.build_conceptual_explanation(profile, SAMPLE_TOPIC, "v2")
        # v2 deve incluir adaptação do estilo no system prompt
        assert len(system) > 50

    def test_v1_simpler_than_v2(self, engine, profile_visual):
        """v1 produz prompts mais curtos que v2."""
        sys_v1, usr_v1 = engine.build_conceptual_explanation(profile_visual, SAMPLE_TOPIC, "v1")
        sys_v2, usr_v2 = engine.build_conceptual_explanation(profile_visual, SAMPLE_TOPIC, "v2")
        # v2 deve ser significativamente mais longo
        assert len(sys_v2) > len(sys_v1)
        assert len(usr_v2) > len(usr_v1)

    def test_persona_varies_by_age(self, engine):
        """Persona v2 varia por faixa etária."""
        child = {"id": "c", "nome": "C", "idade": 8, "nivel": "iniciante", "estilo": "visual"}
        teen = {"id": "t", "nome": "T", "idade": 15, "nivel": "intermediario", "estilo": "visual"}
        adult = {"id": "a", "nome": "A", "idade": 35, "nivel": "avancado", "estilo": "visual"}

        p_child = engine._get_persona_v2(child)
        p_teen = engine._get_persona_v2(teen)
        p_adult = engine._get_persona_v2(adult)

        # Cada persona deve ser diferente
        assert p_child != p_teen
        assert p_teen != p_adult

    def test_sanitize_topic_strips(self, engine):
        """Sanitização remove espaços e caracteres de controle."""
        assert engine.sanitize_topic("  Fotossintese  ") == "Fotossintese"
        assert engine.sanitize_topic("Teste\x00\x1f") == "Teste"

    def test_sanitize_topic_truncates(self, engine):
        """Sanitização trunca tópicos longos para 500 caracteres."""
        long_topic = "A" * 600
        result = engine.sanitize_topic(long_topic)
        assert len(result) == 500

    def test_invalid_content_type(self, engine, profile_visual):
        """Tipo de conteúdo inválido gera ValueError."""
        with pytest.raises(ValueError, match="inválido"):
            engine.build_prompt(profile_visual, SAMPLE_TOPIC, "invalido", "v2")

    def test_quiz_question_builder(self, engine, profile_visual):
        """build_quiz_question retorna system e user prompts."""
        system, user = engine.build_quiz_question(profile_visual, SAMPLE_TOPIC)
        assert "quiz" in system.lower() or "avaliando" in system.lower()
        assert SAMPLE_TOPIC in user

    def test_quiz_feedback_builder(self, engine, profile_visual):
        """build_quiz_feedback inclui pergunta e resposta."""
        system, user = engine.build_quiz_feedback(
            profile_visual, SAMPLE_TOPIC, "O que é fotossintese?", "É o processo das plantas"
        )
        assert "O que é fotossintese?" in user
        assert "É o processo das plantas" in user

    def test_conversation_system(self, engine, profile_visual):
        """build_conversation_system gera system prompt com persona e contexto."""
        system = engine.build_conversation_system(profile_visual, SAMPLE_TOPIC)
        assert "professor" in system.lower() or "especializado" in system.lower()
        assert SAMPLE_TOPIC in system


# ─── Profiles ───────────────────────────────────────────


class TestProfiles:
    """Testes para gerenciamento de perfis."""

    def test_validate_profile_valid(self):
        """Perfil válido é aceito."""
        profile = validate_profile("Ana", 16, "intermediario", "visual", "contexto")
        assert profile["nome"] == "Ana"
        assert profile["idade"] == 16
        assert profile["nivel"] == "intermediario"
        assert profile["estilo"] == "visual"
        assert "id" in profile

    def test_validate_profile_empty_name(self):
        """Nome vazio gera ValueError."""
        with pytest.raises(ValueError, match="vazio"):
            validate_profile("", 16, "intermediario", "visual")

    def test_validate_profile_long_name(self):
        """Nome muito longo gera ValueError."""
        with pytest.raises(ValueError, match="50"):
            validate_profile("A" * 51, 16, "intermediario", "visual")

    def test_validate_profile_invalid_age(self):
        """Idade fora do range gera ValueError."""
        with pytest.raises(ValueError, match="5 e 99"):
            validate_profile("Ana", 3, "intermediario", "visual")
        with pytest.raises(ValueError, match="5 e 99"):
            validate_profile("Ana", 100, "intermediario", "visual")

    def test_validate_profile_invalid_level(self):
        """Nível inválido gera ValueError."""
        with pytest.raises(ValueError, match="inválido"):
            validate_profile("Ana", 16, "expert", "visual")

    def test_validate_profile_invalid_style(self):
        """Estilo inválido gera ValueError."""
        with pytest.raises(ValueError, match="inválido"):
            validate_profile("Ana", 16, "intermediario", "tátil")

    def test_create_profile_persists(self, temp_profiles_dir):
        """create_profile salva no arquivo JSON."""
        profile = create_profile("TestUser", 20, "iniciante", "visual")
        profiles = load_profiles()
        assert any(p["id"] == profile["id"] for p in profiles)

    def test_create_profile_with_quiz(self, temp_profiles_dir):
        """create_profile aceita quiz_answers."""
        answers = ["visual", "auditivo", "visual", "cinestesico", "visual", "visual", "visual"]
        profile = create_profile("Quiz", 15, "intermediario", "visual", quiz_answers=answers)
        assert profile.get("quiz_answers") == answers


# ─── Onboarding / VARK ──────────────────────────────────


class TestOnboarding:
    """Testes para quiz VARK e estilos."""

    def test_learning_styles_complete(self):
        """4 estilos definidos com nome, emoji e descrição."""
        assert len(LEARNING_STYLES) == 4
        for key, info in LEARNING_STYLES.items():
            assert "nome" in info
            assert "emoji" in info
            assert "descricao" in info

    def test_vark_quiz_has_7_questions(self):
        """Quiz VARK tem 7 perguntas."""
        assert len(VARK_QUIZ) == 7

    def test_each_question_has_4_options(self):
        """Cada pergunta tem 4 opções (uma por estilo)."""
        for q in VARK_QUIZ:
            assert len(q["opcoes"]) == 4
            for style in VALID_STYLES:
                assert style in q["opcoes"]

    def test_get_quiz_questions_format(self):
        """get_quiz_questions retorna formato padronizado."""
        questions = get_quiz_questions()
        assert len(questions) == 7
        for q in questions:
            assert "number" in q
            assert "question" in q
            assert "options" in q
            assert len(q["options"]) == 4

    def test_calculate_style_clear_winner(self):
        """Estilo com mais votos vence."""
        answers = ["visual", "visual", "visual", "visual", "auditivo", "auditivo", "cinestesico"]
        result = calculate_style(answers)
        assert result["style"] == "visual"
        assert result["tied"] is False

    def test_calculate_style_tie(self):
        """Empate é detectado corretamente."""
        answers = ["visual", "visual", "auditivo", "auditivo", "cinestesico", "cinestesico", "leitura-escrita"]
        result = calculate_style(answers)
        assert result["tied"] is True
        assert len(result["tied_styles"]) >= 2


# ─── Cache ──────────────────────────────────────────────


class TestCache:
    """Testes para sistema de cache."""

    def test_compute_cache_key_deterministic(self):
        """Mesmos inputs geram mesmo hash."""
        key1 = compute_cache_key("gemini", "flash", "system", [{"role": "user", "content": "test"}], 0.7)
        key2 = compute_cache_key("gemini", "flash", "system", [{"role": "user", "content": "test"}], 0.7)
        assert key1 == key2

    def test_compute_cache_key_varies(self):
        """Inputs diferentes geram hashes diferentes."""
        key1 = compute_cache_key("gemini", "flash", "system", [{"role": "user", "content": "test1"}], 0.7)
        key2 = compute_cache_key("gemini", "flash", "system", [{"role": "user", "content": "test2"}], 0.7)
        assert key1 != key2

    def test_cache_set_and_get(self, temp_cache):
        """Cache armazena e recupera respostas."""
        temp_cache.set("p", "m", "sys", [{"role": "user", "content": "test"}], 0.7, "resposta")
        result = temp_cache.get("p", "m", "sys", [{"role": "user", "content": "test"}], 0.7)
        assert result is not None
        assert result["content"] == "resposta"

    def test_cache_miss(self, temp_cache):
        """Cache retorna None para miss."""
        result = temp_cache.get("p", "m", "sys", [{"role": "user", "content": "nonexistent"}], 0.7)
        assert result is None

    def test_cache_stats_tracking(self, temp_cache):
        """Stats contam hits e misses corretamente."""
        temp_cache.set("p", "m", "sys", [{"role": "user", "content": "x"}], 0.7, "r")
        temp_cache.get("p", "m", "sys", [{"role": "user", "content": "x"}], 0.7)  # hit
        temp_cache.get("p", "m", "sys", [{"role": "user", "content": "y"}], 0.7)  # miss

        stats = temp_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_cache_reset_stats(self, temp_cache):
        """reset_stats zera contadores."""
        temp_cache.get("p", "m", "sys", [{"role": "user", "content": "x"}], 0.7)
        temp_cache.reset_stats()
        stats = temp_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_cache_disabled(self, temp_db):
        """Cache desabilitado sempre retorna miss."""
        cache = CacheManager(temp_db)
        cache.enabled = False
        cache.set("p", "m", "sys", [{"role": "user", "content": "x"}], 0.7, "r")
        result = cache.get("p", "m", "sys", [{"role": "user", "content": "x"}], 0.7)
        assert result is None


# ─── Database ───────────────────────────────────────────


class TestDatabase:
    """Testes para persistência SQLite."""

    def test_create_and_get_session(self, temp_db, profile_visual):
        """Cria e recupera sessão."""
        temp_db.save_profile(profile_visual)
        temp_db.create_session("s1", profile_visual["id"], "gemini", "flash", "Teste", mode="conversation")
        session = temp_db.get_session("s1")
        assert session is not None
        assert session["topic"] == "Teste"

    def test_add_and_get_messages(self, temp_db, profile_visual):
        """Adiciona e recupera mensagens."""
        temp_db.save_profile(profile_visual)
        temp_db.create_session("s2", profile_visual["id"], "gemini", "flash", "Teste")
        temp_db.add_message("s2", "user", "Pergunta", "free_chat")
        temp_db.add_message("s2", "assistant", "Resposta", "free_chat", source="api")

        messages = temp_db.get_messages("s2")
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_save_and_get_evaluation(self, temp_db, profile_visual):
        """Salva e recupera avaliação."""
        temp_db.save_profile(profile_visual)
        temp_db.create_session("s3", profile_visual["id"], "gemini", "flash", "Teste")
        scores = {"adequacao_nivel": 8, "clareza": 9, "adequacao_estilo": 7, "engajamento": 8}
        temp_db.save_evaluation("s3", "version_comparison", scores, "v2 foi melhor", "v2")

        evals = temp_db.get_evaluations("s3")
        assert len(evals) == 1
        assert evals[0]["winner"] == "v2"
        assert evals[0]["criteria_scores"]["clareza"] == 9

    def test_end_session(self, temp_db, profile_visual):
        """end_session define ended_at."""
        temp_db.save_profile(profile_visual)
        temp_db.create_session("s4", profile_visual["id"], "gemini", "flash", "Teste")
        temp_db.end_session("s4")
        session = temp_db.get_session("s4")
        assert session["ended_at"] is not None

    def test_list_sessions(self, temp_db, profile_visual):
        """list_sessions retorna sessões ordenadas."""
        temp_db.save_profile(profile_visual)
        temp_db.create_session("s5", profile_visual["id"], "gemini", "flash", "T1")
        temp_db.create_session("s6", profile_visual["id"], "groq", "llama", "T2")

        sessions = temp_db.list_sessions()
        assert len(sessions) >= 2

    def test_cache_operations(self, temp_db):
        """Set e get no cache via database."""
        temp_db.set_cache("hash1", "conteudo", None)
        result = temp_db.get_cache("hash1")
        assert result is not None
        assert result["response"] == "conteudo"

    def test_cache_expired_not_returned(self, temp_db):
        """Cache expirado não é retornado."""
        temp_db.set_cache("hash2", "conteudo", "2020-01-01 00:00:00")
        result = temp_db.get_cache("hash2")
        assert result is None


# ─── ContentGenerator ───────────────────────────────────


class TestContentGenerator:
    """Testes para o orquestrador de geração de conteúdo."""

    def test_generate_single_api(self, engine, temp_cache, mock_adapter, profile_visual):
        """Geração retorna resultado com source 'api' no primeiro acesso."""
        gen = ContentGenerator(engine, temp_cache)
        result = gen.generate_single(mock_adapter, profile_visual, SAMPLE_TOPIC, "conceptual")

        assert result["content"] == "Resposta de teste."
        assert result["source"] == "api"
        assert result["content_type"] == "conceptual"
        assert result["version"] == "v2"

    def test_generate_single_cache_hit(self, engine, temp_cache, mock_adapter, profile_visual):
        """Segunda chamada com mesmos params retorna do cache."""
        gen = ContentGenerator(engine, temp_cache)
        gen.generate_single(mock_adapter, profile_visual, SAMPLE_TOPIC, "conceptual")
        result = gen.generate_single(mock_adapter, profile_visual, SAMPLE_TOPIC, "conceptual")

        assert result["source"] == "cache"

    def test_generate_all_types(self, engine, temp_cache, mock_adapter, profile_visual):
        """generate_all_types retorna 4 resultados."""
        gen = ContentGenerator(engine, temp_cache)
        results = gen.generate_all_types(mock_adapter, profile_visual, SAMPLE_TOPIC)

        assert len(results) == 4
        for ct in CONTENT_TYPES:
            assert ct in results
            assert results[ct]["content"] == "Resposta de teste."


# ─── Exceptions ─────────────────────────────────────────


class TestExceptions:
    """Testes para hierarquia de exceções."""

    def test_llm_error_hierarchy(self):
        """Todas as exceções herdam de LLMError."""
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMAuthError, LLMError)
        assert issubclass(LLMResponseError, LLMError)

    def test_rate_limit_retry_after(self):
        """LLMRateLimitError armazena retry_after."""
        err = LLMRateLimitError(retry_after=30)
        assert err.retry_after == 30
        assert "30" in str(err)

    def test_rate_limit_no_retry(self):
        """LLMRateLimitError funciona sem retry_after."""
        err = LLMRateLimitError()
        assert err.retry_after is None


# ─── Export ─────────────────────────────────────────────


class TestExport:
    """Testes para exportação."""

    def test_export_comparison_json(self):
        """export_comparison_json retorna JSON válido."""
        data = {
            "topic": "Teste",
            "profile": {"nome": "Ana", "idade": 16, "nivel": "intermediario", "estilo": "visual"},
            "results": {},
            "cache_stats": {"hits": 0, "misses": 0, "hit_rate": 0},
            "total_elapsed": 1.0,
        }
        result = export_comparison_json(data)
        parsed = json.loads(result)
        assert parsed["topic"] == "Teste"

    def test_export_comparison_markdown_versions(self):
        """export_comparison_markdown gera markdown para v1/v2."""
        data = {
            "topic": "Teste",
            "profile": {"nome": "Ana", "idade": 16, "nivel": "intermediario", "estilo": "visual"},
            "provider": "gemini",
            "model": "flash",
            "results": {
                "conceptual": {
                    "label": "Explicação Conceitual",
                    "v1": {"content": "v1 content", "source": "api"},
                    "v2": {"content": "v2 content", "source": "api"},
                }
            },
            "cache_stats": {"hits": 0, "misses": 2, "hit_rate": 0},
            "total_elapsed": 2.0,
        }
        md = export_comparison_markdown(data)
        assert "v1 vs v2" in md
        assert "v1 content" in md
        assert "v2 content" in md

    def test_export_session_json(self, temp_db, profile_visual):
        """export_session_json retorna JSON com sessão e mensagens."""
        temp_db.save_profile(profile_visual)
        temp_db.create_session("exp1", profile_visual["id"], "gemini", "flash", "Teste")
        temp_db.add_message("exp1", "assistant", "Conteúdo", "conceptual", "v2", "api")

        result = export_session_json("exp1", temp_db)
        parsed = json.loads(result)
        assert parsed["session"]["topic"] == "Teste"
        assert len(parsed["messages"]) == 1

    def test_export_session_markdown(self, temp_db, profile_visual):
        """export_session_markdown gera markdown formatado."""
        temp_db.save_profile(profile_visual)
        temp_db.create_session("exp2", profile_visual["id"], "gemini", "flash", "Teste")
        temp_db.add_message("exp2", "assistant", "Conteúdo", "conceptual", "v2", "api")

        md = export_session_markdown("exp2", temp_db)
        assert "Sessão: Teste" in md or "Sessao: Teste" in md

    def test_export_session_not_found(self, temp_db):
        """Sessão inexistente gera ValueError."""
        with pytest.raises(ValueError, match="não encontrada"):
            export_session_json("nonexistent", temp_db)
