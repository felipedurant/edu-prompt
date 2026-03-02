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
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# ─── Modelos ─────────────────────────────────────────────
GEMINI_FLASH_MODEL = "gemini-2.5-flash"
GEMINI_PRO_MODEL = "gemini-2.5-pro"       # exclusivo para judge
GROQ_MODEL = "llama-3.3-70b-versatile"
DEEPSEEK_MODEL = "deepseek-chat"

# ─── Geração ─────────────────────────────────────────────
DEFAULT_TEMPERATURE = 0.7
DEFAULT_PROMPT_VERSION = "v2"

# ─── Sessão / Tokens ────────────────────────────────────
TOKEN_ESTIMATE_RATIO = 4              # 1 token ≈ 4 caracteres em PT-BR
SLIDING_WINDOW_THRESHOLD = 3000       # tokens estimados antes de ativar janela
SLIDING_WINDOW_KEEP_MESSAGES = 8      # últimas N mensagens mantidas integrais
CONTEXT_LIMITS = {
    "gemini": 1_000_000,
    "groq": 128_000,
    "deepseek": 128_000,
}

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
