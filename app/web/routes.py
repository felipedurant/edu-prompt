"""Flask routes — Blueprint principal da interface web."""

import json
import logging

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session as flask_session,
    redirect,
    url_for,
)

from app.adapters import get_adapter, list_available, LLMError
from app.config import MODEL_REGISTRY, CONTENT_TYPES
from app.core.profiles import load_profiles, create_profile, get_profile_by_id
from app.core.onboarding import LEARNING_STYLES, get_quiz_questions, calculate_style
from app.core.prompt_engine import PromptEngine
from app.core.session import SessionManager, COMMANDS_HELP
from app.core.comparison import compare_versions, compare_models, CONTENT_TYPE_LABELS
from app.core.evaluator import ContentEvaluator
from app.core.export import (
    export_comparison_json,
    export_comparison_markdown,
    save_export,
)
from app.storage.database import Database
from app.storage.cache import CacheManager

logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__, static_folder="static", static_url_path="/static")

# Singletons
_db = None
_cache = None
_engine = None
_sessions: dict[str, SessionManager] = {}


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager(get_db())
    return _cache


def get_engine() -> PromptEngine:
    global _engine
    if _engine is None:
        _engine = PromptEngine()
    return _engine


# ─── Páginas ────────────────────────────────────────────


@bp.route("/")
def home():
    """Página inicial."""
    profiles = load_profiles()
    available = list_available()
    models = {k: MODEL_REGISTRY[k] for k in available}
    return render_template(
        "home.html",
        profiles=profiles,
        models=models,
        styles=LEARNING_STYLES,
    )


@bp.route("/session", methods=["POST"])
def start_session():
    """Inicia sessão conversacional."""
    profile_id = request.form.get("profile_id")
    model_key = request.form.get("model_key")
    topic = request.form.get("topic", "").strip()

    if not profile_id or not model_key or not topic:
        return redirect(url_for("main.home"))

    profile = get_profile_by_id(profile_id)
    if not profile:
        return redirect(url_for("main.home"))

    try:
        adapter = get_adapter(model_key)
    except ValueError:
        return redirect(url_for("main.home"))

    sm = SessionManager(profile, adapter, get_engine(), get_cache(), get_db())
    result = sm.start_topic(topic)
    _sessions[sm.session_id] = sm

    flask_session["session_id"] = sm.session_id
    flask_session["model_key"] = model_key

    model_label = MODEL_REGISTRY.get(model_key, {}).get("label", model_key)

    return render_template(
        "session.html",
        profile=profile,
        topic=topic,
        model_label=model_label,
        session_id=sm.session_id,
        initial_content=result["content"],
        initial_source=result["source"],
        commands=COMMANDS_HELP,
    )


@bp.route("/api/chat", methods=["POST"])
def api_chat():
    """Endpoint AJAX para mensagens da sessão."""
    data = request.get_json()
    session_id = data.get("session_id")
    message = data.get("message", "").strip()

    sm = _sessions.get(session_id)
    if not sm:
        return jsonify({"error": "Sessão não encontrada."}), 404

    if not message:
        return jsonify({"error": "Mensagem vazia."}), 400

    try:
        # Comando /
        if message == "/":
            return jsonify({
                "type": "commands",
                "commands": COMMANDS_HELP,
            })

        if message == "/sair":
            sm.end()
            del _sessions[session_id]
            return jsonify({"type": "end", "message": "Sessão encerrada."})

        if message.startswith("/novo_topico"):
            new_topic = message.replace("/novo_topico", "").strip()
            if not new_topic:
                return jsonify({"error": "Informe o novo tópico."}), 400
            result = sm.change_topic(new_topic)
            return jsonify({
                "type": "content",
                "content": result["content"],
                "source": result["source"],
                "elapsed": result.get("elapsed", 0),
                "topic": new_topic,
                "label": "Explicação Conceitual",
            })

        if message == "/quiz_me":
            result = sm.handle_quiz()
            return jsonify({
                "type": "quiz",
                "content": result["content"],
                "source": result["source"],
                "elapsed": result.get("elapsed", 0),
            })

        if message in COMMANDS_HELP and message not in ("/quiz_me", "/novo_topico", "/sair"):
            result = sm.execute_command(message)

            if result.get("already_generated"):
                return jsonify({
                    "type": "already_generated",
                    "content": result["content"],
                    "content_type": result["content_type"],
                })

            label_map = {
                "/exemplos": "Exemplos Práticos",
                "/perguntas": "Perguntas de Reflexão",
                "/resumo": "Resumo Visual",
            }
            return jsonify({
                "type": "content",
                "content": result["content"],
                "source": result["source"],
                "elapsed": result.get("elapsed", 0),
                "label": label_map.get(message, message),
            })

        # Quiz pendente
        if sm.has_quiz_pending:
            result = sm.handle_quiz_answer(message)
            return jsonify({
                "type": "quiz_feedback",
                "content": result["content"],
                "source": result["source"],
                "elapsed": result.get("elapsed", 0),
            })

        # Conversa livre
        result = sm.send_message(message)
        return jsonify({
            "type": "message",
            "content": result["content"],
            "source": result["source"],
            "elapsed": result.get("elapsed", 0),
        })

    except LLMError as e:
        logger.error("Erro na API: %s", e)
        return jsonify({"error": str(e)}), 502


@bp.route("/api/regenerate", methods=["POST"])
def api_regenerate():
    """Regenera conteúdo de um comando."""
    data = request.get_json()
    session_id = data.get("session_id")
    content_type = data.get("content_type")

    sm = _sessions.get(session_id)
    if not sm:
        return jsonify({"error": "Sessão não encontrada."}), 404

    try:
        result = sm.regenerate(content_type)
        return jsonify({
            "type": "content",
            "content": result["content"],
            "source": result["source"],
            "elapsed": result.get("elapsed", 0),
        })
    except LLMError as e:
        return jsonify({"error": str(e)}), 502


# ─── Comparações ────────────────────────────────────────


@bp.route("/compare/versions", methods=["POST"])
def compare_versions_page():
    """Comparação v1 vs v2."""
    profile_id = request.form.get("profile_id")
    model_key = request.form.get("model_key")
    topic = request.form.get("topic", "").strip()

    if not profile_id or not model_key or not topic:
        return redirect(url_for("main.home"))

    profile = get_profile_by_id(profile_id)
    if not profile:
        return redirect(url_for("main.home"))

    try:
        adapter = get_adapter(model_key)
    except ValueError:
        return redirect(url_for("main.home"))

    cache = get_cache()
    cache.reset_stats()

    result = compare_versions(adapter, profile, topic, get_engine(), cache, get_db())
    model_label = MODEL_REGISTRY.get(model_key, {}).get("label", model_key)

    return render_template(
        "comparison.html",
        mode="versions",
        profile=profile,
        topic=topic,
        model_label=model_label,
        result=result,
        content_types=CONTENT_TYPES,
        labels=CONTENT_TYPE_LABELS,
    )


@bp.route("/compare/models", methods=["POST"])
def compare_models_page():
    """Comparação multi-modelo."""
    profile_id = request.form.get("profile_id")
    topic = request.form.get("topic", "").strip()
    model_keys = request.form.getlist("model_keys")

    if not profile_id or not topic or len(model_keys) < 2:
        return redirect(url_for("main.home"))

    profile = get_profile_by_id(profile_id)
    if not profile:
        return redirect(url_for("main.home"))

    cache = get_cache()
    cache.reset_stats()

    result = compare_models(model_keys, profile, topic, get_engine(), cache, get_db())

    return render_template(
        "comparison.html",
        mode="models",
        profile=profile,
        topic=topic,
        model_label="Multi-Modelo",
        result=result,
        content_types=CONTENT_TYPES,
        labels=CONTENT_TYPE_LABELS,
        model_registry=MODEL_REGISTRY,
    )


# ─── Perfis ────────────────────────────────────────────


@bp.route("/api/profiles", methods=["POST"])
def api_create_profile():
    """Cria novo perfil via AJAX."""
    data = request.get_json()
    nome = data.get("nome", "").strip()
    idade = data.get("idade")
    nivel = data.get("nivel")
    estilo = data.get("estilo")
    contexto = data.get("contexto", "")

    if not nome or not idade or not nivel or not estilo:
        return jsonify({"error": "Campos obrigatórios faltando."}), 400

    try:
        idade = int(idade)
    except (ValueError, TypeError):
        return jsonify({"error": "Idade inválida."}), 400

    profile = create_profile(nome, idade, nivel, estilo, contexto)
    return jsonify({"profile": profile})


@bp.route("/api/quiz-vark", methods=["GET"])
def api_quiz_vark():
    """Retorna perguntas do quiz VARK."""
    return jsonify({"questions": get_quiz_questions()})


@bp.route("/api/quiz-vark/result", methods=["POST"])
def api_quiz_vark_result():
    """Calcula resultado do quiz VARK."""
    data = request.get_json()
    answers = data.get("answers", [])
    result = calculate_style(answers)
    return jsonify(result)
