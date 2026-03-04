"""Gerenciador de sessão conversacional com suporte a comandos e histórico."""

import logging
import time
from uuid import uuid4

from app.config import (
    DEFAULT_PROMPT_VERSION,
    DEFAULT_TEMPERATURE,
    TOKEN_ESTIMATE_RATIO,
    SLIDING_WINDOW_THRESHOLD,
    SLIDING_WINDOW_KEEP_MESSAGES,
)
from app.adapters.base import LLMAdapter
from app.adapters.exceptions import LLMError, LLMResponseError
from app.core.prompt_engine import PromptEngine
from app.storage.cache import CacheManager
from app.storage.database import Database

logger = logging.getLogger(__name__)

# Mapeamento de comandos para content_type
COMMAND_MAP = {
    "/exemplos": "practical",
    "/perguntas": "reflection",
    "/resumo": "visual",
}

COMMANDS_HELP = {
    "/exemplos": "Gerar exemplos práticos contextualizados",
    "/perguntas": "Gerar perguntas de reflexão e pensamento crítico",
    "/resumo": "Gerar resumo visual (mapa mental/diagrama ASCII)",
    "/quiz_me": "Testar seu conhecimento sobre o tópico",
    "/novo_topico": "Iniciar um novo tópico de estudo",
    "/sair": "Encerrar a sessão de aprendizado",
}


class SessionManager:
    """Gerencia sessão conversacional com suporte a comandos e histórico."""

    def __init__(self, profile: dict, adapter: LLMAdapter, engine: PromptEngine,
                 cache: CacheManager, db: Database, output_format: str = "ascii"):
        self.profile = profile
        self.adapter = adapter
        self.engine = engine
        self.cache = cache
        self.db = db
        self.output_format = output_format
        self.messages: list[dict] = []
        self.session_id: str = str(uuid4())
        self.current_topic: str = ""
        self.generated_types: dict[str, str] = {}
        self.system_prompt: str = ""
        self._quiz_pending: str | None = None  # pergunta de quiz aguardando resposta

    def setup_topic(self, topic: str):
        """Configura tópico sem gerar conteúdo (para loading assíncrono na web)."""
        topic = self.engine.sanitize_topic(topic)
        self.current_topic = topic
        self.generated_types = {}
        self.messages = []
        self._quiz_pending = None

        # Monta system prompt para a sessão
        self.system_prompt = self.engine.build_conversation_system(self.profile, topic)

        # Sincroniza perfil no DB antes de criar sessão (FK constraint)
        self.db.save_profile(self.profile)

        # Cria sessão no DB
        self.db.create_session(
            session_id=self.session_id,
            profile_id=self.profile["id"],
            provider=self.adapter.get_provider_name(),
            model=self.adapter.get_model_name(),
            topic=topic,
            system_prompt=self.system_prompt,
            mode="conversation",
        )

    def start_topic(self, topic: str) -> dict:
        """
        Inicia tópico: sanitiza, configura e gera explicação conceitual.

        Returns:
            Dict com 'content', 'source' ('api'|'cache'), 'elapsed'.
        """
        self.setup_topic(topic)
        return self.generate_initial_content()

    def generate_initial_content(self) -> dict:
        """Gera explicação conceitual inicial (chamado assincronamente pela web)."""
        result = self._generate_content("conceptual")
        self.generated_types["conceptual"] = result["content"]
        return result

    def send_message(self, user_message: str) -> dict:
        """
        Processa mensagem livre do aluno. Retorna resposta da LLM.

        Returns:
            Dict com 'content', 'source', 'elapsed'.
        """
        # Adiciona mensagem do aluno ao histórico
        self.messages.append({"role": "user", "content": user_message})
        self.db.add_message(self.session_id, "user", user_message, "free_chat")

        # Aplica janela deslizante se necessário
        messages_to_send = self._apply_sliding_window()

        start = time.time()
        try:
            content = self.adapter.generate(
                messages=messages_to_send,
                system_prompt=self.system_prompt,
                temperature=DEFAULT_TEMPERATURE,
            )
        except LLMResponseError:
            # Retry 1x para respostas vazias
            logger.warning("Resposta vazia, tentando novamente...")
            content = self.adapter.generate(
                messages=messages_to_send,
                system_prompt=self.system_prompt,
                temperature=DEFAULT_TEMPERATURE,
            )
        elapsed = time.time() - start

        # Adiciona resposta ao histórico
        self.messages.append({"role": "assistant", "content": content})
        self.db.add_message(self.session_id, "assistant", content, "free_chat", source="api")

        return {"content": content, "source": "api", "elapsed": round(elapsed, 1)}

    def execute_command(self, command: str) -> dict:
        """
        Executa comando (/exemplos, /perguntas, /resumo).

        Returns:
            Dict com 'content', 'source', 'elapsed', 'already_generated' (bool),
            'content_type'.
        """
        content_type = COMMAND_MAP.get(command)
        if not content_type:
            return {
                "content": f"Comando não reconhecido: {command}. Digite / para ver comandos.",
                "source": "system",
                "elapsed": 0,
                "already_generated": False,
                "content_type": None,
            }

        # Verifica se já foi gerado (Opção B)
        if content_type in self.generated_types:
            return {
                "content": self.generated_types[content_type],
                "source": "memory",
                "elapsed": 0,
                "already_generated": True,
                "content_type": content_type,
            }

        result = self._generate_content(content_type)
        self.generated_types[content_type] = result["content"]
        result["already_generated"] = False
        result["content_type"] = content_type
        return result

    def regenerate(self, content_type: str) -> dict:
        """Regenera conteúdo: consulta cache → se miss, chama API."""
        result = self._generate_content(content_type)
        self.generated_types[content_type] = result["content"]
        result["content_type"] = content_type
        return result

    def handle_quiz(self) -> dict:
        """Gera pergunta de quiz. Retorna pergunta."""
        # Construir contexto da conversa para pergunta contextualizada
        context = ""
        if self.messages:
            recent = self.messages[-6:]  # últimas 6 mensagens
            context = "\n".join(
                f"{m['role']}: {m['content'][:200]}" for m in recent
            )

        system, user = self.engine.build_quiz_question(
            self.profile, self.current_topic, context
        )

        start = time.time()
        try:
            question = self.adapter.generate(
                messages=[{"role": "user", "content": user}],
                system_prompt=system,
                temperature=DEFAULT_TEMPERATURE,
            )
        except LLMResponseError:
            question = self.adapter.generate(
                messages=[{"role": "user", "content": user}],
                system_prompt=system,
                temperature=DEFAULT_TEMPERATURE,
            )
        elapsed = time.time() - start

        self._quiz_pending = question

        # Salva no histórico
        self.messages.append({"role": "assistant", "content": question})
        self.db.add_message(self.session_id, "assistant", question, "quiz_question", source="api")

        return {"content": question, "source": "api", "elapsed": round(elapsed, 1)}

    def handle_quiz_answer(self, answer: str) -> dict:
        """Avalia resposta do aluno. Retorna feedback."""
        if not self._quiz_pending:
            return {
                "content": "Nenhuma pergunta de quiz pendente. Use /quiz_me primeiro.",
                "source": "system",
                "elapsed": 0,
            }

        question = self._quiz_pending
        self._quiz_pending = None

        # Salva resposta do aluno
        self.messages.append({"role": "user", "content": answer})
        self.db.add_message(self.session_id, "user", answer, "quiz_answer")

        system, user = self.engine.build_quiz_feedback(
            self.profile, self.current_topic, question, answer
        )

        start = time.time()
        feedback = self.adapter.generate(
            messages=[{"role": "user", "content": user}],
            system_prompt=system,
            temperature=DEFAULT_TEMPERATURE,
        )
        elapsed = time.time() - start

        self.messages.append({"role": "assistant", "content": feedback})
        self.db.add_message(self.session_id, "assistant", feedback, "quiz_feedback", source="api")

        return {"content": feedback, "source": "api", "elapsed": round(elapsed, 1)}

    @property
    def has_quiz_pending(self) -> bool:
        return self._quiz_pending is not None

    def change_topic(self, new_topic: str) -> dict:
        """Troca de tópico: limpa generated_types, mantém perfil e API."""
        new_topic = self.engine.sanitize_topic(new_topic)

        # Salva sessão anterior
        self.db.end_session(self.session_id)

        # Nova sessão
        self.session_id = str(uuid4())
        self.current_topic = new_topic
        self.generated_types = {}
        self.messages = []
        self._quiz_pending = None

        self.system_prompt = self.engine.build_conversation_system(self.profile, new_topic)

        self.db.save_profile(self.profile)
        self.db.create_session(
            session_id=self.session_id,
            profile_id=self.profile["id"],
            provider=self.adapter.get_provider_name(),
            model=self.adapter.get_model_name(),
            topic=new_topic,
            system_prompt=self.system_prompt,
            mode="conversation",
        )

        # Gera explicação conceitual
        result = self._generate_content("conceptual")
        self.generated_types["conceptual"] = result["content"]
        return result

    def end(self) -> None:
        """Encerra sessão e persiste."""
        self.db.end_session(self.session_id)
        logger.info("Sessão %s encerrada.", self.session_id[:8])

    def get_history(self) -> list[dict]:
        """Retorna histórico completo da sessão."""
        return self.db.get_messages(self.session_id)

    # ─── Métodos internos ────────────────────────────────

    def _generate_content(self, content_type: str) -> dict:
        """Gera conteúdo via PromptEngine: consulta cache, se miss chama API."""
        system, user = self.engine.build_prompt(
            self.profile, self.current_topic, content_type, DEFAULT_PROMPT_VERSION,
            output_format=self.output_format
        )

        messages = [{"role": "user", "content": user}]

        # Consulta cache
        cached = self.cache.get(
            self.adapter.get_provider_name(),
            self.adapter.get_model_name(),
            system, messages, DEFAULT_TEMPERATURE,
        )
        if cached:
            content = cached["content"]
            # Adiciona ao histórico
            self.messages.append({"role": "assistant", "content": content})
            self.db.add_message(
                self.session_id, "assistant", content, content_type,
                DEFAULT_PROMPT_VERSION, "cache",
            )
            return {
                "content": content,
                "source": "cache",
                "elapsed": 0,
                "cached_at": cached["created_at"],
            }

        # Chamada à API
        start = time.time()
        try:
            content = self.adapter.generate(
                messages=messages,
                system_prompt=system,
                temperature=DEFAULT_TEMPERATURE,
            )
        except LLMResponseError:
            # Retry 1x
            logger.warning("Resposta vazia para %s, retry...", content_type)
            content = self.adapter.generate(
                messages=messages,
                system_prompt=system,
                temperature=DEFAULT_TEMPERATURE,
            )
        elapsed = time.time() - start

        # Salva no cache
        self.cache.set(
            self.adapter.get_provider_name(),
            self.adapter.get_model_name(),
            system, messages, DEFAULT_TEMPERATURE, content,
        )

        # Adiciona ao histórico
        self.messages.append({"role": "assistant", "content": content})
        self.db.add_message(
            self.session_id, "assistant", content, content_type,
            DEFAULT_PROMPT_VERSION, "api",
        )

        return {"content": content, "source": "api", "elapsed": round(elapsed, 1)}

    def _apply_sliding_window(self) -> list[dict]:
        """Aplica janela deslizante se o histórico exceder o threshold."""
        total_chars = sum(len(m["content"]) for m in self.messages)
        estimated_tokens = total_chars / TOKEN_ESTIMATE_RATIO

        if estimated_tokens <= SLIDING_WINDOW_THRESHOLD:
            return list(self.messages)

        # Manter últimas N mensagens integrais
        keep = self.messages[-SLIDING_WINDOW_KEEP_MESSAGES:]
        old = self.messages[:-SLIDING_WINDOW_KEEP_MESSAGES]

        if not old:
            return list(self.messages)

        # Resumir mensagens antigas
        summary_parts = []
        for m in old:
            prefix = "Aluno" if m["role"] == "user" else "Professor"
            summary_parts.append(f"{prefix}: {m['content'][:100]}...")

        summary = "Resumo da conversa anterior:\n" + "\n".join(summary_parts)

        n_summarized = len(old)
        logger.info("Janela deslizante ativada: %d msgs resumidas", n_summarized)

        result = [{"role": "user", "content": summary}]
        result.extend(keep)
        return result

    def _estimate_tokens(self) -> int:
        """Estima tokens do histórico."""
        total_chars = sum(len(m["content"]) for m in self.messages)
        return int(total_chars / TOKEN_ESTIMATE_RATIO)
