"""Testes de integração para o EduPrompt Platform."""

import json
import pytest

from app.core.prompt_engine import PromptEngine
from app.core.content_generator import ContentGenerator
from app.core.session import SessionManager, COMMAND_MAP, COMMANDS_HELP
from app.core.comparison import compare_versions, compare_models
from app.core.evaluator import ContentEvaluator, EVALUATION_CRITERIA
from app.core.export import (
    export_session_json,
    export_session_markdown,
    export_comparison_json,
    export_comparison_markdown,
    save_export,
)
from app.storage.database import Database
from app.storage.cache import CacheManager

from tests.conftest import MockAdapter, SAMPLE_TOPIC, CONTENT_TYPES


# ─── SessionManager (integração) ───────────────────────


class TestSessionIntegration:
    """Testes de integração do SessionManager."""

    def test_full_session_flow(self, engine, temp_cache, temp_db, mock_adapter, profile_visual):
        """Fluxo completo: start_topic → send_message → execute_command → end."""
        sm = SessionManager(profile_visual, mock_adapter, engine, temp_cache, temp_db)

        # 1. Inicia tópico
        result = sm.start_topic(SAMPLE_TOPIC)
        assert result["content"] == "Resposta de teste."
        assert sm.current_topic == SAMPLE_TOPIC

        # 2. Envia mensagem livre
        result = sm.send_message("O que é fotossintese?")
        assert result["source"] == "api"

        # 3. Executa comando
        result = sm.execute_command("/exemplos")
        assert result["already_generated"] is False

        # 4. Comando repetido → already_generated
        result = sm.execute_command("/exemplos")
        assert result["already_generated"] is True

        # 5. Encerra
        sm.end()

        # Verifica persistência
        messages = temp_db.get_messages(sm.session_id)
        assert len(messages) >= 3  # conceitual + pergunta + resposta + exemplos

    def test_quiz_flow(self, engine, temp_cache, temp_db, mock_adapter, profile_visual):
        """Fluxo de quiz: handle_quiz → handle_quiz_answer."""
        sm = SessionManager(profile_visual, mock_adapter, engine, temp_cache, temp_db)
        sm.start_topic(SAMPLE_TOPIC)

        # Quiz
        result = sm.handle_quiz()
        assert sm.has_quiz_pending is True

        # Resposta
        result = sm.handle_quiz_answer("A planta usa luz para fazer energia")
        assert sm.has_quiz_pending is False
        assert result["source"] == "api"

    def test_change_topic(self, engine, temp_cache, temp_db, mock_adapter, profile_visual):
        """Troca de tópico limpa generated_types e cria nova sessão."""
        sm = SessionManager(profile_visual, mock_adapter, engine, temp_cache, temp_db)
        sm.start_topic(SAMPLE_TOPIC)
        old_session = sm.session_id

        sm.execute_command("/exemplos")
        assert "practical" in sm.generated_types

        result = sm.change_topic("Equações de segundo grau")
        assert sm.session_id != old_session
        assert sm.current_topic == "Equações de segundo grau"
        assert sm.generated_types == {"conceptual": "Resposta de teste."}

    def test_regenerate(self, engine, temp_cache, temp_db, mock_adapter, profile_visual):
        """Regenera conteúdo com nova chamada."""
        sm = SessionManager(profile_visual, mock_adapter, engine, temp_cache, temp_db)
        sm.start_topic(SAMPLE_TOPIC)

        sm.execute_command("/exemplos")
        result = sm.regenerate("practical")
        assert result["content_type"] == "practical"

    def test_sliding_window(self, engine, temp_cache, temp_db, profile_visual):
        """Janela deslizante ativa quando histórico é grande."""
        adapter = MockAdapter(response="Resposta curta.")
        sm = SessionManager(profile_visual, adapter, engine, temp_cache, temp_db)
        sm.start_topic(SAMPLE_TOPIC)

        # Adiciona muitas mensagens para exceder threshold
        for i in range(20):
            sm.messages.append({"role": "user", "content": f"Mensagem longa número {i} " * 50})
            sm.messages.append({"role": "assistant", "content": f"Resposta longa número {i} " * 50})

        # Aplica janela
        windowed = sm._apply_sliding_window()
        # Deve ter menos mensagens que o original
        assert len(windowed) < len(sm.messages)


# ─── Comparison (integração) ────────────────────────────


class TestComparisonIntegration:
    """Testes de integração para comparações."""

    def test_compare_versions_full(self, engine, temp_cache, temp_db, mock_adapter, profile_visual):
        """compare_versions gera 8 resultados (4 tipos × 2 versões)."""
        result = compare_versions(mock_adapter, profile_visual, SAMPLE_TOPIC,
                                  engine, temp_cache, temp_db)

        assert "results" in result
        assert len(result["results"]) == 4
        for ct, data in result["results"].items():
            assert "v1" in data or "v1_error" in data
            assert "v2" in data or "v2_error" in data

        assert result["total_elapsed"] >= 0
        assert "cache_stats" in result

    def test_compare_versions_with_callback(self, engine, temp_cache, temp_db, mock_adapter, profile_visual):
        """Progress callback é chamado corretamente."""
        calls = []

        def callback(completed, total, desc):
            calls.append((completed, total, desc))

        compare_versions(mock_adapter, profile_visual, SAMPLE_TOPIC,
                         engine, temp_cache, temp_db, progress_callback=callback)

        assert len(calls) == 8  # 4 tipos × 2 versões


# ─── Evaluator ──────────────────────────────────────────


class TestEvaluator:
    """Testes para o avaliador LLM-as-judge."""

    def test_parse_evaluation_valid(self):
        """Parse de avaliação JSON válida."""
        response = json.dumps({
            "v1_scores": {"adequacao_nivel": 6, "clareza": 7, "adequacao_estilo": 5, "engajamento": 6},
            "v2_scores": {"adequacao_nivel": 9, "clareza": 8, "adequacao_estilo": 9, "engajamento": 9},
            "justificativa": "v2 é muito melhor",
            "vencedor": "v2",
        })
        result = ContentEvaluator._parse_evaluation(response)
        assert result["v1_scores"]["clareza"] == 7
        assert result["v2_scores"]["adequacao_nivel"] == 9
        assert result["vencedor"] == "v2"

    def test_parse_evaluation_with_code_block(self):
        """Parse funciona com resposta envolta em code block."""
        inner = json.dumps({
            "v1_scores": {"adequacao_nivel": 5, "clareza": 5, "adequacao_estilo": 5, "engajamento": 5},
            "v2_scores": {"adequacao_nivel": 8, "clareza": 8, "adequacao_estilo": 8, "engajamento": 8},
            "justificativa": "test",
            "vencedor": "v2",
        })
        response = f"```json\n{inner}\n```"
        result = ContentEvaluator._parse_evaluation(response)
        assert result["v1_scores"]["adequacao_nivel"] == 5

    def test_parse_evaluation_clamps_scores(self):
        """Scores são limitados entre 1 e 10."""
        response = json.dumps({
            "v1_scores": {"adequacao_nivel": 0, "clareza": 15, "adequacao_estilo": -1, "engajamento": 11},
            "v2_scores": {"adequacao_nivel": 1, "clareza": 10, "adequacao_estilo": 5, "engajamento": 5},
            "justificativa": "",
            "vencedor": "v2",
        })
        result = ContentEvaluator._parse_evaluation(response)
        assert result["v1_scores"]["adequacao_nivel"] == 1  # clamped from 0
        assert result["v1_scores"]["clareza"] == 10  # clamped from 15

    def test_parse_api_evaluation(self):
        """Parse de avaliação multi-API."""
        response = json.dumps({
            "scores": {
                "gemini": {"adequacao_nivel": 8, "clareza": 9, "adequacao_estilo": 7, "engajamento": 8},
                "groq": {"adequacao_nivel": 7, "clareza": 7, "adequacao_estilo": 8, "engajamento": 7},
            },
            "justificativa": "Gemini melhor no geral",
            "vencedor": "gemini",
        })
        result = ContentEvaluator._parse_api_evaluation(response, ["gemini", "groq"])
        assert result["scores"]["gemini"]["clareza"] == 9
        assert result["vencedor"] == "gemini"

    def test_evaluation_criteria_complete(self):
        """4 critérios de avaliação definidos."""
        assert len(EVALUATION_CRITERIA) == 4
        assert "adequacao_nivel" in EVALUATION_CRITERIA
        assert "clareza" in EVALUATION_CRITERIA
        assert "adequacao_estilo" in EVALUATION_CRITERIA
        assert "engajamento" in EVALUATION_CRITERIA


# ─── Export (integração) ────────────────────────────────


class TestExportIntegration:
    """Testes de integração para exportação."""

    def test_save_export_creates_file(self, tmp_path, monkeypatch):
        """save_export cria arquivo no diretório correto."""
        monkeypatch.setattr("app.core.export.SAMPLES_DIR", tmp_path)
        path = save_export("conteúdo de teste", "test_export.json")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "conteúdo de teste"

    def test_save_export_with_subdir(self, tmp_path, monkeypatch):
        """save_export cria subdiretório se necessário."""
        monkeypatch.setattr("app.core.export.SAMPLES_DIR", tmp_path)
        path = save_export("data", "test.json", subdir="sessions")
        assert path.exists()
        assert "sessions" in str(path)

    def test_full_export_roundtrip(self, engine, temp_cache, temp_db, mock_adapter, profile_visual):
        """Exporta sessão completa e verifica integridade."""
        sm = SessionManager(profile_visual, mock_adapter, engine, temp_cache, temp_db)
        sm.start_topic(SAMPLE_TOPIC)
        sm.send_message("Pergunta teste")
        sm.end()

        # JSON
        json_str = export_session_json(sm.session_id, temp_db)
        data = json.loads(json_str)
        assert data["session"]["topic"] == SAMPLE_TOPIC
        assert len(data["messages"]) >= 2

        # Markdown
        md_str = export_session_markdown(sm.session_id, temp_db)
        assert SAMPLE_TOPIC in md_str


# ─── Flask Web (integração) ────────────────────────────


class TestFlaskApp:
    """Testes de integração para a aplicação Flask."""

    @pytest.fixture
    def client(self):
        """Test client Flask."""
        from app.web.app import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_home_page(self, client):
        """Página inicial retorna 200."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"EduPrompt" in response.data

    def test_404_page(self, client):
        """Página inexistente retorna 404."""
        response = client.get("/pagina-inexistente")
        assert response.status_code == 404

    def test_create_profile_api(self, client, temp_profiles_dir):
        """API de criação de perfil funciona."""
        response = client.post("/api/profiles", json={
            "nome": "TestFlask",
            "idade": 15,
            "nivel": "iniciante",
            "estilo": "visual",
            "contexto": "",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "profile" in data

    def test_quiz_vark_api(self, client):
        """API do quiz VARK retorna perguntas."""
        response = client.get("/api/quiz-vark")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["questions"]) == 7

    def test_quiz_vark_result_api(self, client):
        """API de resultado VARK calcula estilo."""
        response = client.post("/api/quiz-vark/result", json={
            "answers": ["visual", "visual", "visual", "visual", "auditivo", "auditivo", "cinestesico"],
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["style"] == "visual"

    def test_chat_api_no_session(self, client):
        """API de chat retorna 404 sem sessão."""
        response = client.post("/api/chat", json={
            "session_id": "nonexistent",
            "message": "oi",
        })
        assert response.status_code == 404
