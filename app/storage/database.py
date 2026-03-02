"""SQLite: schema, migrations e queries."""

import json
import logging
import sqlite3
from pathlib import Path

from app.config import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('iniciante', 'intermediario', 'avancado')),
    learning_style TEXT NOT NULL CHECK (learning_style IN ('visual', 'auditivo', 'leitura-escrita', 'cinestesico')),
    context TEXT,
    quiz_answers TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    topic TEXT,
    system_prompt TEXT,
    mode TEXT NOT NULL DEFAULT 'conversation'
        CHECK (mode IN ('conversation', 'compare_versions', 'compare_apis')),
    started_at TEXT DEFAULT (datetime('now')),
    ended_at TEXT,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_type TEXT CHECK (content_type IN (
        'free_chat', 'conceptual', 'practical', 'reflection', 'visual',
        'quiz_question', 'quiz_answer', 'quiz_feedback'
    )),
    prompt_version TEXT CHECK (prompt_version IN ('v1', 'v2')),
    source TEXT CHECK (source IN ('api', 'cache')),
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS cache (
    hash TEXT PRIMARY KEY,
    response TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    evaluation_type TEXT NOT NULL CHECK (evaluation_type IN ('version_comparison', 'api_comparison')),
    evaluator_model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    criteria_scores TEXT NOT NULL,
    justification TEXT NOT NULL,
    winner TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""


class Database:
    """Gerenciador de banco de dados SQLite."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or DB_PATH)
        self._ensure_dir()
        self._init_schema()

    def _ensure_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        try:
            with self._get_conn() as conn:
                conn.executescript(SCHEMA)
            logger.info("Schema SQLite inicializado: %s", self.db_path)
        except sqlite3.DatabaseError as e:
            logger.error("Erro ao inicializar DB: %s. Recriando...", e)
            Path(self.db_path).unlink(missing_ok=True)
            with self._get_conn() as conn:
                conn.executescript(SCHEMA)

    # ─── Sessions ────────────────────────────────────────

    def create_session(self, session_id: str, profile_id: str, provider: str,
                       model: str, topic: str = "", system_prompt: str = "",
                       mode: str = "conversation") -> None:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO sessions (id, profile_id, provider, model, topic, system_prompt, mode)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, profile_id, provider, model, topic, system_prompt, mode),
            )

    def end_session(self, session_id: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET ended_at = datetime('now') WHERE id = ?",
                (session_id,),
            )

    def update_session_topic(self, session_id: str, topic: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET topic = ? WHERE id = ?",
                (topic, session_id),
            )

    def get_session(self, session_id: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT s.*, p.name as profile_name
                   FROM sessions s
                   LEFT JOIN profiles p ON s.profile_id = p.id
                   ORDER BY s.started_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ─── Messages ────────────────────────────────────────

    def add_message(self, session_id: str, role: str, content: str,
                    content_type: str = "free_chat", prompt_version: str | None = None,
                    source: str | None = None) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO messages (session_id, role, content, content_type, prompt_version, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, role, content, content_type, prompt_version, source),
            )

    def get_messages(self, session_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ─── Profiles (DB) ───────────────────────────────────

    def save_profile(self, profile: dict) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO profiles (id, name, age, level, learning_style, context, quiz_answers)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile["id"],
                    profile["nome"],
                    profile["idade"],
                    profile["nivel"],
                    profile["estilo"],
                    profile.get("contexto", ""),
                    json.dumps(profile.get("quiz_answers")) if profile.get("quiz_answers") else None,
                ),
            )

    # ─── Evaluations ─────────────────────────────────────

    def save_evaluation(self, session_id: str, evaluation_type: str,
                        criteria_scores: dict, justification: str,
                        winner: str | None = None) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO evaluations (session_id, evaluation_type, criteria_scores, justification, winner)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, evaluation_type, json.dumps(criteria_scores), justification, winner),
            )

    def get_evaluations(self, session_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM evaluations WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["criteria_scores"] = json.loads(d["criteria_scores"])
                results.append(d)
            return results

    # ─── Cache ───────────────────────────────────────────

    def get_cache(self, cache_hash: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT * FROM cache WHERE hash = ?
                   AND (expires_at IS NULL OR expires_at > datetime('now'))""",
                (cache_hash,),
            ).fetchone()
            return dict(row) if row else None

    def set_cache(self, cache_hash: str, response: str, expires_at: str | None = None) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO cache (hash, response, expires_at)
                   VALUES (?, ?, ?)""",
                (cache_hash, response, expires_at),
            )

    def cleanup_expired_cache(self) -> int:
        """Remove entradas expiradas. Retorna quantidade removida."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at <= datetime('now')"
            )
            count = cursor.rowcount
            if count > 0:
                logger.info("Cache: %d entradas expiradas removidas.", count)
            return count

    def get_cache_stats(self) -> dict:
        """Retorna estatísticas do cache."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            valid = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at IS NULL OR expires_at > datetime('now')"
            ).fetchone()[0]
            return {"total": total, "valid": valid, "expired": total - valid}
