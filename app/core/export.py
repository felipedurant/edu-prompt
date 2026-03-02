"""Exportação de sessões e comparações em JSON e Markdown."""

import json
import logging
from datetime import datetime
from pathlib import Path

from app.config import SAMPLES_DIR
from app.storage.database import Database

logger = logging.getLogger(__name__)

CONTENT_TYPE_LABELS = {
    "conceptual": "Explicação Conceitual",
    "practical": "Exemplos Práticos",
    "reflection": "Perguntas de Reflexão",
    "visual": "Resumo Visual",
    "free_chat": "Conversa Livre",
    "quiz_question": "Quiz - Pergunta",
    "quiz_answer": "Quiz - Resposta",
    "quiz_feedback": "Quiz - Feedback",
}

CONTENT_TYPE_EMOJIS = {
    "conceptual": "\U0001f4da",
    "practical": "\U0001f52c",
    "reflection": "\u2753",
    "visual": "\U0001f5fa\ufe0f",
    "free_chat": "\U0001f4ac",
    "quiz_question": "\U0001f9e0",
    "quiz_answer": "\u270d\ufe0f",
    "quiz_feedback": "\u2705",
}


def export_session_json(session_id: str, db: Database) -> str:
    """Exporta sessão completa como JSON estruturado."""
    session = db.get_session(session_id)
    if not session:
        raise ValueError(f"Sessão não encontrada: {session_id}")

    messages = db.get_messages(session_id)
    evaluations = db.get_evaluations(session_id)

    data = {
        "session": session,
        "messages": messages,
        "evaluations": evaluations,
        "exported_at": datetime.now().isoformat(),
    }

    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def export_session_markdown(session_id: str, db: Database) -> str:
    """Exporta sessão como Markdown formatado."""
    session = db.get_session(session_id)
    if not session:
        raise ValueError(f"Sessão não encontrada: {session_id}")

    messages = db.get_messages(session_id)

    lines = [
        f"# Sessão: {session.get('topic', 'Sem tópico')}",
        f"**Perfil:** {session.get('profile_name', session['profile_id'])}",
        f"**API:** {session['provider']} ({session['model']}) | "
        f"**Modo:** {session['mode']} | "
        f"**Data:** {session['started_at']}",
        "",
    ]

    for msg in messages:
        ct = msg.get("content_type", "free_chat")
        emoji = CONTENT_TYPE_EMOJIS.get(ct, "")
        label = CONTENT_TYPE_LABELS.get(ct, ct)

        if msg["role"] == "user":
            lines.append(f"### {emoji} Aluno")
            lines.append(msg["content"])
            lines.append("")
        else:
            version_tag = f" (v{msg['prompt_version']})" if msg.get("prompt_version") else ""
            source_tag = f" [{msg['source']}]" if msg.get("source") else ""
            lines.append(f"### {emoji} {label}{version_tag}{source_tag}")
            lines.append(msg["content"])
            lines.append("")

    lines.append("---")
    lines.append("*Gerado por EduPrompt Platform*")

    return "\n".join(lines)


def export_comparison_json(comparison_data: dict) -> str:
    """Exporta resultado de comparação como JSON."""
    return json.dumps(comparison_data, ensure_ascii=False, indent=2, default=str)


def export_comparison_markdown(comparison_data: dict) -> str:
    """Exporta comparação como Markdown com tabelas e seções."""
    topic = comparison_data.get("topic", "")
    profile = comparison_data.get("profile", {})
    results = comparison_data.get("results", {})
    cache_stats = comparison_data.get("cache_stats", {})
    mode = "v1 vs v2" if "provider" in comparison_data else "Multi-API"

    lines = [
        f"# Comparação {mode}: {topic}",
        f"**Perfil:** {profile.get('nome', '')} ({profile.get('idade', '')} anos, "
        f"{profile.get('nivel', '')}, {profile.get('estilo', '')})",
    ]

    if "provider" in comparison_data:
        lines.append(f"**API:** {comparison_data['provider']} ({comparison_data.get('model', '')})")

    lines.append(f"**Tempo total:** {comparison_data.get('total_elapsed', 0)}s")
    lines.append("")

    for ct, data in results.items():
        label = data.get("label", ct)
        lines.append(f"## {CONTENT_TYPE_EMOJIS.get(ct, '')} {label}")
        lines.append("")

        if "v1" in data and "v2" in data:
            # Comparação v1/v2
            if data.get("v1"):
                source = data["v1"].get("source", "")
                lines.append(f"### v1 (Básico) [{source}]")
                lines.append(data["v1"]["content"])
                lines.append("")

            if data.get("v2"):
                source = data["v2"].get("source", "")
                lines.append(f"### v2 (Otimizado) [{source}]")
                lines.append(data["v2"]["content"])
                lines.append("")

        elif "providers" in data:
            # Comparação multi-API
            for provider, pdata in data["providers"].items():
                plabel = pdata.get("label", provider)
                if pdata.get("result"):
                    source = pdata["result"].get("source", "")
                    elapsed = pdata["result"].get("elapsed", 0)
                    lines.append(f"### {plabel} [{source}, {elapsed}s]")
                    lines.append(pdata["result"]["content"])
                    lines.append("")
                elif pdata.get("error"):
                    lines.append(f"### {plabel} [ERRO]")
                    lines.append(f"> {pdata['error']}")
                    lines.append("")

    # Estatísticas
    if cache_stats:
        lines.append("---")
        lines.append(
            f"**Cache:** {cache_stats.get('hits', 0)} hits / "
            f"{cache_stats.get('misses', 0)} misses "
            f"({cache_stats.get('hit_rate', 0)}% economia)"
        )

    lines.append("")
    lines.append("---")
    lines.append("*Gerado por EduPrompt Platform*")

    return "\n".join(lines)


def save_export(content: str, filename: str, subdir: str = "") -> Path:
    """Salva conteúdo exportado em arquivo."""
    output_dir = SAMPLES_DIR / subdir if subdir else SAMPLES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename
    filepath.write_text(content, encoding="utf-8")

    logger.info("Exportado: %s", filepath)
    return filepath
