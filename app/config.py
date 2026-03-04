"""
Configuração centralizada da plataforma EduPrompt.
Todas as constantes, thresholds e parâmetros ajustáveis ficam aqui.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Diretório raiz do projeto ───────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── APIs ────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ─── Modelos ─────────────────────────────────────────────
GEMINI_FLASH_MODEL = "gemini-2.5-flash"
JUDGE_MODEL = "deepseek/deepseek-v3.2"    # modelo usado pelo LLM-as-judge (OpenRouter)
JUDGE_PROVIDER = "openrouter"
JUDGE_API_KEY_ENV = "OPENROUTER_API_KEY"

# ─── Registro de modelos ──────────────────────────────
MODEL_REGISTRY = {
    "gemini-flash": {
        "provider": "gemini",
        "model_id": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash (Google)",
        "api_key_env": "GEMINI_API_KEY",
    },
    "gemini-3-flash": {
        "provider": "gemini",
        "model_id": "gemini-3-flash-preview",
        "label": "Gemini 3 Flash Preview (Google)",
        "api_key_env": "GEMINI_API_KEY",
    },
    "llama4-scout": {
        "provider": "groq",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "label": "Llama 4 Scout (Groq)",
        "api_key_env": "GROQ_API_KEY",
    },
    "gpt-oss-120b": {
        "provider": "groq",
        "model_id": "openai/gpt-oss-120b",
        "label": "GPT-OSS 120B (Groq)",
        "api_key_env": "GROQ_API_KEY",
    },
    "deepseek-r1-70b": {
        "provider": "groq",
        "model_id": "deepseek-r1-distill-llama-70b",
        "label": "DeepSeek R1 70B (Groq)",
        "api_key_env": "GROQ_API_KEY",
    },
    "qwen3-32b": {
        "provider": "groq",
        "model_id": "qwen/qwen3-32b",
        "label": "Qwen 3 32B (Groq)",
        "api_key_env": "GROQ_API_KEY",
    },
    "gpt-4.1-mini": {
        "provider": "openrouter",
        "model_id": "openai/gpt-4.1-mini-2025-04-14",
        "label": "GPT-4.1 Mini (OpenRouter)",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "grok-4.1-fast": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4.1-fast",
        "label": "Grok 4.1 Fast (OpenRouter)",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "deepseek-v3-or": {
        "provider": "openrouter",
        "model_id": "deepseek/deepseek-v3.2",
        "label": "DeepSeek V3.2 (OpenRouter)",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "mistral-small-3.1": {
        "provider": "openrouter",
        "model_id": "mistralai/mistral-small-3.1-24b-instruct:free",
        "label": "Mistral Small 3.1 (OpenRouter)",
        "api_key_env": "OPENROUTER_API_KEY",
    },
}

# ─── Geração ─────────────────────────────────────────────
DEFAULT_TEMPERATURE = 0.7
DEFAULT_PROMPT_VERSION = "v2"

# ─── Sessão / Tokens ────────────────────────────────────
TOKEN_ESTIMATE_RATIO = 4              # 1 token ≈ 4 caracteres em PT-BR
SLIDING_WINDOW_THRESHOLD = 3000       # tokens estimados antes de ativar janela
SLIDING_WINDOW_KEEP_MESSAGES = 8      # últimas N mensagens mantidas integrais

# ─── Cache ───────────────────────────────────────────────
CACHE_ENABLED = True
CACHE_TTL_HOURS = 24                  # expiração em horas (0 = sem expiração)

# ─── Paralelismo ─────────────────────────────────────────
MAX_PARALLEL_WORKERS = 4              # threads para geração paralela

# ─── Caminhos ────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
PROFILES_PATH = DATA_DIR / "profiles.json"
DB_PATH = DATA_DIR / "edu_content.db"
SAMPLES_DIR = PROJECT_ROOT / "samples"

# ─── Logging ─────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ─── Web ─────────────────────────────────────────────────
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-in-prod")

# ─── Níveis e estilos válidos ────────────────────────────
VALID_LEVELS = ("iniciante", "intermediario", "avancado")
VALID_STYLES = ("visual", "auditivo", "leitura-escrita", "cinestesico")
CONTENT_TYPES = ("conceptual", "practical", "reflection", "visual")
PROMPT_VERSIONS = ("v1", "v2")
