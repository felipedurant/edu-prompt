# Plano Final v4 — Desafio Técnico: Estágio em IA e Engenharia de Prompt

---

## 1. Decisões Consolidadas

| Ponto | Decisão |
|---|---|
| Linguagem | Python |
| APIs de geração | **Google Gemini 2.5 Flash**, **Groq** (Llama 3.3 70B), **DeepSeek** (V3.2) |
| API do Judge | **Google Gemini 2.5 Pro** (fixo) |
| Arquitetura | Adapter Pattern com classes abstratas (ABC) |
| Interface | CLI (**Typer + Rich**) + Web (Flask) |
| Persistência | SQLite |
| Deploy | Render (free tier) |
| Extras | LLM-as-judge, modo comparação multi-API, modo comparação v1/v2, quiz VARK, sessão conversacional, /quiz_me, exportação Markdown, geração paralela, testes com pytest |

### APIs

| Provedor | Modelo | Uso | RPD | Contexto | Cartão? | Compat. OpenAI? |
|---|---|---|---|---|---|---|
| Google Gemini | 2.5 Flash | Geração de conteúdo | ~250 | 1M | Não | Não (SDK próprio) |
| Google Gemini | 2.5 Pro | LLM-as-judge (exclusivo) | ~100 | 1M | Não | Não (SDK próprio) |
| Groq | Llama 3.3 70B | Geração de conteúdo | ~14.400 | 128K | Não | Sim |
| DeepSeek | V3.2 | Geração de conteúdo | Amplo (5M tok/30d) | 128K | Não | Sim |

- Groq e DeepSeek usam formato OpenAI → adapters quase idênticos (muda `base_url` e `model`)
- Gemini usa SDK próprio → demonstra flexibilidade do adapter pattern
- Nenhuma exige cartão de crédito
- O sistema só exibe APIs com chave configurada no `.env`

---

## 2. Estrutura de Diretórios

```
edu-prompt-platform/
├── app/
│   ├── __init__.py
│   ├── config.py                # Constantes, thresholds, configuração centralizada
│   ├── core/
│   │   ├── __init__.py
│   │   ├── profiles.py          # Gerenciamento de perfis de alunos
│   │   ├── prompt_engine.py     # Motor de engenharia de prompt (CORAÇÃO: 40% da nota)
│   │   ├── content_generator.py # Orquestrador de geração de conteúdo
│   │   ├── session.py           # Gerenciador de sessão conversacional
│   │   ├── onboarding.py        # Cadastro de aluno + quiz VARK
│   │   ├── evaluator.py         # LLM-as-judge (Gemini 2.5 Pro)
│   │   ├── comparison.py        # Modos de comparação (v1/v2 e multi-API)
│   │   └── export.py            # Exportação JSON e Markdown
│   ├── adapters/
│   │   ├── __init__.py          # Factory: get_adapter(provider) + list_available()
│   │   ├── base.py              # Classe abstrata LLMAdapter (ABC)
│   │   ├── gemini_adapter.py    # Adapter Google Gemini (SDK próprio)
│   │   ├── groq_adapter.py      # Adapter Groq (formato OpenAI)
│   │   └── deepseek_adapter.py  # Adapter DeepSeek (formato OpenAI)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLite: schema, migrations, queries
│   │   └── cache.py             # Cache de respostas (hash → resultado)
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py              # CLI com Typer + Rich
│   └── web/
│       ├── __init__.py
│       ├── app.py               # Factory create_app()
│       ├── routes.py            # Rotas Flask
│       ├── templates/
│       │   ├── base.html
│       │   ├── index.html
│       │   ├── profile_new.html
│       │   ├── session.html
│       │   ├── compare_versions.html
│       │   ├── compare_apis.html
│       │   └── history.html
│       └── static/
│           └── style.css
├── data/
│   ├── profiles.json            # 5 perfis pré-definidos
│   └── edu_content.db           # SQLite (criado em runtime)
├── samples/
│   ├── session_example.json
│   ├── session_example.md
│   ├── comparison_v1v2_example.json
│   ├── comparison_v1v2_example.md
│   ├── comparison_multiapi_example.json
│   └── comparison_multiapi_example.md
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_profiles.py
│   ├── test_prompt_engine.py
│   ├── test_adapters.py
│   ├── test_session.py
│   ├── test_onboarding.py
│   ├── test_cache.py
│   ├── test_evaluator.py
│   ├── test_comparison.py
│   └── test_content_generator.py
├── .env.example
├── .gitignore
├── Procfile
├── render.yaml
├── requirements.txt
├── README.md
├── ARCHITECTURE.md
└── PROMPT_ENGINEERING_NOTES.md
```

---

## 3. Configuração Centralizada — `app/config.py`

```python
"""
Configuração centralizada da plataforma EduPrompt.
Todas as constantes, thresholds e parâmetros ajustáveis ficam aqui.
"""

import os
from dotenv import load_dotenv

load_dotenv()

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
DATA_DIR = "data"
PROFILES_PATH = f"{DATA_DIR}/profiles.json"
DB_PATH = f"{DATA_DIR}/edu_content.db"
SAMPLES_DIR = "samples"

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
```

---

## 4. Adapter Pattern — `app/adapters/`

### `base.py`

```python
from abc import ABC, abstractmethod

class LLMAdapter(ABC):
    """Interface abstrata para adaptadores de LLM."""

    @abstractmethod
    def generate(self, messages: list[dict], system_prompt: str = "",
                 temperature: float = 0.7) -> str:
        """
        Envia histórico de mensagens e retorna texto gerado.

        Args:
            messages: Lista de dicts com 'role' (user|assistant) e 'content'.
            system_prompt: Prompt de sistema (persona, contexto).
            temperature: Criatividade da resposta (0.0-1.0).

        Returns:
            Texto gerado pela LLM.

        Raises:
            LLMConnectionError: Falha de conexão com a API.
            LLMRateLimitError: Rate limit atingido.
            LLMResponseError: Resposta inválida ou vazia.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Retorna nome do modelo (ex: 'gemini-2.5-flash')."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna nome do provedor (ex: 'gemini')."""
        pass
```

### Exceções customizadas — `app/adapters/exceptions.py`

```python
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
        super().__init__(f"Rate limit. Retry after: {retry_after}s" if retry_after else "Rate limit.")

class LLMAuthError(LLMError):
    """Chave inválida ou expirada (401/403)."""
    pass

class LLMResponseError(LLMError):
    """Resposta inválida, vazia ou truncada."""
    pass
```

### Implementações

**Groq e DeepSeek** — formato OpenAI, compartilham lógica:
```python
from openai import OpenAI
# Groq: base_url="https://api.groq.com/openai/v1", model="llama-3.3-70b-versatile"
# DeepSeek: base_url="https://api.deepseek.com", model="deepseek-chat"
```

**Gemini** — SDK próprio (`google-generativeai`), adapter converte `messages[]` para formato Gemini.

Cada adapter faz `try/except` interno, captura exceções da biblioteca e relança como exceções customizadas (`LLMConnectionError`, `LLMRateLimitError`, etc.).

### Factory — `__init__.py`

```python
def get_adapter(provider: str) -> LLMAdapter:
    """
    Retorna adapter configurado para o provedor.

    Args:
        provider: Nome do provedor ('gemini', 'groq', 'deepseek').

    Raises:
        ValueError: Provedor desconhecido ou sem chave configurada.
    """
    adapters = {
        "gemini": GeminiAdapter,      # Gemini 2.5 Flash (geração)
        "groq": GroqAdapter,          # Llama 3.3 70B
        "deepseek": DeepSeekAdapter,  # DeepSeek V3.2
    }
    if provider not in adapters:
        raise ValueError(f"Provedor desconhecido: {provider}")
    if provider not in list_available():
        raise ValueError(f"Provedor '{provider}' sem chave configurada no .env")
    return adapters[provider]()

def get_judge_adapter() -> LLMAdapter:
    """Retorna adapter do Gemini 2.5 Pro (uso exclusivo como judge)."""
    return GeminiAdapter(model=GEMINI_PRO_MODEL)

def list_available() -> list[str]:
    """Retorna apenas provedores com chave configurada no .env."""
    available = []
    if GEMINI_API_KEY: available.append("gemini")
    if GROQ_API_KEY: available.append("groq")
    if DEEPSEEK_API_KEY: available.append("deepseek")
    return available
```

---

## 5. Motor de Engenharia de Prompt — `app/core/prompt_engine.py`

**CORAÇÃO DO PROJETO — 40% DA NOTA**

### Técnicas obrigatórias (aplicadas em TODOS os prompts)

| Técnica | Aplicação |
|---|---|
| **Persona Prompting** | System prompt com papel de professor especializado |
| **Context Setting** | Dados do aluno (idade, nível, estilo, contexto) injetados no prompt |
| **Chain-of-Thought** | Raciocínio passo a passo (especialmente em explicações conceituais) |
| **Output Formatting** | Formato de saída especificado por tipo de conteúdo |

### Versões v1 e v2

**v1 (literal/simples):** aplica as técnicas de forma direta e mínima, como descrito no enunciado.
- Persona: "Você é um professor experiente em Pedagogia"
- Context: dados básicos do aluno no prompt
- CoT: "Pense passo a passo"
- Output: instrução genérica de formato

**v2 (otimizado/avançado):** técnicas refinadas com engenharia de prompt moderna.
- Persona com especialização, tom e abordagem pedagógica calibrados por faixa etária
- Context com análise de pré-requisitos e exemplos do cotidiano do aluno
- CoT com scaffolding progressivo, checkpoints de compreensão, meta-cognição
- Output com estrutura detalhada, exemplos de formato, constraints de qualidade

**v2 é o padrão em toda a aplicação.** v1 só existe no modo comparação de versões.

### 4 builders

```python
class PromptEngine:
    """Motor de engenharia de prompt com suporte a 4 tipos × 2 versões × 4 estilos."""

    def build_conceptual_explanation(self, profile: dict, topic: str,
                                      version: str = "v2") -> tuple[str, str]:
        """Chain-of-thought para explicação conceitual."""

    def build_practical_examples(self, profile: dict, topic: str,
                                  version: str = "v2") -> tuple[str, str]:
        """Exemplos contextualizados para idade/nível."""

    def build_reflection_questions(self, profile: dict, topic: str,
                                    version: str = "v2") -> tuple[str, str]:
        """Perguntas que estimulam pensamento crítico."""

    def build_visual_summary(self, profile: dict, topic: str,
                              version: str = "v2") -> tuple[str, str]:
        """Mapa mental/diagrama ASCII ou descrição visual."""

    def build_quiz_question(self, profile: dict, topic: str,
                             conversation_context: str = "") -> tuple[str, str]:
        """Gera pergunta para testar conhecimento do aluno (/quiz_me)."""

    def build_quiz_feedback(self, profile: dict, topic: str,
                             question: str, answer: str) -> tuple[str, str]:
        """Avalia resposta do aluno e dá feedback construtivo."""
```

Cada builder retorna `(system_prompt, user_prompt)`.

### Adaptação por estilo de aprendizado

| Estilo | Adaptação no prompt |
|---|---|
| **Visual** | Diagramas, esquemas, analogias visuais, emojis como ícones |
| **Auditivo** | Linguagem conversacional, ritmo de explicação falada, repetição |
| **Leitura-escrita** | Texto estruturado, definições formais, referências |
| **Cinestésico** | Atividades práticas, exercícios hands-on, simulações mentais |

### Sanitização de input

```python
def sanitize_topic(self, topic: str) -> str:
    """
    Sanitiza tópico antes de injetar no prompt.
    Remove caracteres de controle, limita tamanho, escapa padrões
    que poderiam ser interpretados como instruções pela LLM.
    """
    topic = topic.strip()
    topic = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', topic)  # remove controle
    if len(topic) > 500:
        topic = topic[:500]
    return topic
```

---

## 6. Estratégia de Cache — `app/storage/cache.py`

### Composição da chave

Hash SHA-256 de: `provider + model + system_prompt + messages_json + temperature`

```python
def compute_cache_key(provider: str, model: str, system_prompt: str,
                      messages: list[dict], temperature: float) -> str:
    """Gera hash determinístico para identificar uma chamada."""
    payload = json.dumps({
        "provider": provider,
        "model": model,
        "system_prompt": system_prompt,
        "messages": messages,
        "temperature": temperature
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()
```

### Quando o cache é consultado

| Fluxo | Cache consulta? | Justificativa |
|---|---|---|
| **Sessão — conversa livre** | ❌ Não | Histórico é único a cada mensagem, hit improvável |
| **Sessão — comandos (/exemplos, etc.)** | ✅ Sim | Mesmo perfil + tópico + tipo pode ter hit de sessão anterior |
| **Repetição de comando (Opção B)** | 🟡 Memória | `generated_types` evita chamada sem consultar DB. Se regenerar, consulta cache antes de chamar API |
| **Comparação v1/v2** | ✅ Sim | Se rodar mesma combinação de perfil+tópico+API, retorna cache |
| **Comparação multi-API** | ✅ Sim | Se alguma API já gerou aquele conteúdo (ex: via sessão anterior), reutiliza |

### Reuso entre modos (diferencial)

O cache é **global e compartilhado** entre modos. Cenário concreto:

1. Aluno usa sessão conversacional com Gemini Flash sobre "fotossíntese" → gera `/exemplos` → cache armazena
2. Depois roda modo multi-API sobre "fotossíntese" → a parte do Gemini Flash já está em cache → **3 chamadas em vez de 4** para essa API
3. Se rodar modo v1/v2 com Gemini Flash sobre "fotossíntese" → o v2 de exemplos já está em cache → **7 chamadas em vez de 8**

### Indicador visual

Na CLI e na Web, toda resposta exibe a origem:

```
⚡ Cache (gerado em 01/03 14:30)    → resposta do cache
🌐 Gerado agora (1.2s)              → chamada nova à API
```

### Expiração

- TTL configurável em `config.py` (padrão: 24h)
- Cache expirado é ignorado na consulta e limpo periodicamente
- Sem expiração (`TTL = 0`) para modo demo/apresentação

### Estatísticas

Ao exportar ou ao final de uma comparação, exibir:
```
📊 Cache: 5 hits / 3 misses (62% economia)
```

---

## 7. Tratamento de Erros e Logging

### Exceções e respostas do sistema

| Cenário | Exceção | Resposta ao usuário |
|---|---|---|
| Timeout na API | `LLMConnectionError` | "⚠️ [API] não respondeu a tempo. Tente novamente ou escolha outra API." |
| Rate limit (429) | `LLMRateLimitError` | "⚠️ Limite de requisições atingido para [API]. Aguarde [N]s ou use outra API." |
| Chave inválida (401/403) | `LLMAuthError` | "❌ Chave de API inválida para [API]. Verifique seu .env." |
| Resposta vazia | `LLMResponseError` | "⚠️ [API] retornou resposta vazia. Tentando novamente..." (retry 1x) |
| Resposta truncada | `LLMResponseError` | "⚠️ Resposta truncada. Exibindo o que foi recebido." |
| Tópico vazio | `ValueError` | "❌ Digite um tópico de estudo." |
| Tópico muito longo | Truncado silenciosamente | Trunca para 500 chars, loga warning |
| Comando inexistente | — | "Comando não reconhecido. Digite / para ver comandos disponíveis." |
| API cai no meio de comparação multi-API | `LLMError` | "⚠️ [API] falhou. Exibindo resultados das APIs que responderam." |
| SQLite corrompido | `sqlite3.DatabaseError` | "❌ Erro no banco de dados. Recriando... (dados anteriores perdidos)" |
| Perfil incompleto | `ValueError` | Solicita campo faltante novamente |

### Retry automático

- Respostas vazias: retry 1x automaticamente
- Rate limit: espera `retry_after` se disponível, senão aguarda 5s
- Timeout: não faz retry (pode ser lentidão da API)
- Máximo de retries: 1 (para não travar o fluxo)

### Logging

```python
import logging
from app.config import LOG_LEVEL, LOG_FORMAT

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Exemplos de uso nos módulos:
logger.info("Chamando %s para '%s' (perfil: %s)", provider, topic, profile["nome"])
logger.info("Cache HIT para hash %s", cache_key[:12])
logger.warning("Cache MISS para hash %s", cache_key[:12])
logger.warning("Tópico truncado de %d para 500 caracteres", len(topic))
logger.error("Falha na API %s: %s", provider, str(error))
logger.debug("Prompt montado: system=%d chars, user=%d chars", len(sys), len(usr))
```

Níveis:
- `DEBUG`: conteúdo dos prompts, hashes, detalhes de decisão
- `INFO`: chamadas de API, cache hits, sessões iniciadas/encerradas
- `WARNING`: cache misses, truncamentos, retries
- `ERROR`: falhas de API, erros de DB

---

## 8. Geração Paralela — Modos de Comparação

### Implementação com `concurrent.futures.ThreadPoolExecutor`

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import MAX_PARALLEL_WORKERS

def generate_parallel(tasks: list[dict]) -> dict[str, str]:
    """
    Executa múltiplas chamadas de API em paralelo.

    Args:
        tasks: Lista de dicts com 'key', 'adapter', 'system_prompt', 'user_prompt'.

    Returns:
        Dict mapeando key → resposta.
    """
    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        future_to_key = {}
        for task in tasks:
            # Consulta cache antes de submeter
            cache_key = compute_cache_key(...)
            cached = cache.get(cache_key)
            if cached:
                results[task["key"]] = {"content": cached, "source": "cache"}
                continue
            future = executor.submit(task["adapter"].generate, ...)
            future_to_key[future] = task["key"]

        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                result = future.result(timeout=30)
                results[key] = {"content": result, "source": "api"}
                cache.set(cache_key, result)  # salva no cache
            except LLMError as e:
                errors[key] = str(e)
                logger.error("Falha paralela para %s: %s", key, e)

    return results, errors
```

### Onde é usado

| Modo | Sem paralelismo | Com paralelismo |
|---|---|---|
| Comparação v1/v2 | 8 chamadas sequenciais | Até 4 simultâneas (2 rodadas) |
| Comparação multi-API | 12 chamadas sequenciais | Até 4 simultâneas (3 rodadas) |

**Resultado prático:** tempo de espera cai de ~24s (12 × 2s) para ~6s (3 rodadas × 2s).

### Progress bar durante geração

```
⏳ Gerando 4 tipos × 3 APIs = 12 chamadas (v2)...
  ████████████░░░░░░░░ 8/12  [Groq ✅ | Gemini ⏳ | DeepSeek ✅]
```

---

## 9. Sessão Conversacional — `app/core/session.py`

### Fluxo (Abordagem C)

1. Aluno escolhe perfil → escolhe API (só as disponíveis) → digita tópico
2. Sistema gera **explicação conceitual** (CoT, v2) como ponto de partida
3. A partir daqui, o aluno pode:
   - **Conversar livremente** — digita qualquer mensagem, a LLM responde mantendo contexto
   - **Usar comandos** — `/exemplos`, `/perguntas`, `/resumo`, `/quiz_me` para gerar conteúdo com prompts otimizados
   - **Digitar `/`** — lista todos os comandos disponíveis com descrição (estilo Claude Code)
   - **`/novo_topico`** — inicia novo tópico (limpa histórico, mantém perfil e API)
   - **`/sair`** — encerra sessão
4. A sessão continua aberta até o aluno sair

### Comandos

```
/ (barra sozinha) → lista de comandos:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /exemplos     Gerar exemplos práticos contextualizados
  /perguntas    Gerar perguntas de reflexão e pensamento crítico
  /resumo       Gerar resumo visual (mapa mental/diagrama ASCII)
  /quiz_me      Testar seu conhecimento sobre o tópico
  /novo_topico  Iniciar um novo tópico de estudo
  /sair         Encerrar a sessão de aprendizado
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### `/quiz_me` — Teste de conhecimento

Fluxo:
1. Aluno digita `/quiz_me`
2. Sistema usa `PromptEngine.build_quiz_question()` com o tópico atual e contexto da conversa
3. LLM gera pergunta adequada ao nível do aluno
4. Aluno responde em texto livre
5. Sistema usa `PromptEngine.build_quiz_feedback()` com a pergunta + resposta do aluno
6. LLM avalia a resposta e dá feedback construtivo (acertou/parcial/errou + explicação)
7. Volta para o modo normal de conversa

Diferencial: inverte o fluxo pedagógico — em vez de a LLM ensinar, ela avalia o aluno. Demonstra compreensão profunda de pedagogia.

### Repetição de comandos (Opção B)

Se o aluno usar um comando que já foi executado no tópico atual:
1. **Não chama a API**
2. Exibe: "Já gerei [tipo] para este tópico."
3. Oferece: `[1] Ver o anterior  [2] Regenerar (nova chamada)`
4. Se `[1]`: exibe o conteúdo salvo em `generated_types` (zero custo)
5. Se `[2]`: consulta cache primeiro → se miss, chama API → atualiza `generated_types`

Exceção: `/quiz_me` pode ser repetido livremente (cada quiz gera pergunta diferente baseada no contexto atual).

### Gestão de histórico e tokens

- Todas as mensagens (conversa livre + outputs de comandos) acumulam no histórico
- A cada chamada de API, o histórico completo é enviado
- **Estimativa de tokens:** `len(text) / TOKEN_ESTIMATE_RATIO` (~4 chars/token em PT-BR)
- Quando o histórico exceder `SLIDING_WINDOW_THRESHOLD` (~3000 tokens):
  - Manter últimas `SLIDING_WINDOW_KEEP_MESSAGES` (8) mensagens integrais
  - Resumir mensagens antigas em parágrafo curto injetado no system prompt
  - Logar: `logger.info("Janela deslizante ativada: %d msgs resumidas", n_resumidas)`
- Gemini (1M contexto): threshold raramente atingido
- Groq/DeepSeek (128K): relevante em sessões longas

### SessionManager

```python
class SessionManager:
    """Gerencia sessão conversacional com suporte a comandos e histórico."""

    def __init__(self, profile: dict, adapter: LLMAdapter, engine: PromptEngine,
                 cache: CacheManager, db: Database):
        self.profile = profile
        self.adapter = adapter
        self.engine = engine
        self.cache = cache
        self.db = db
        self.messages: list[dict] = []
        self.session_id: str = str(uuid4())
        self.current_topic: str = ""
        self.generated_types: dict[str, str] = {}  # {"exemplos": "conteúdo...", ...}
        self.system_prompt: str = ""

    def start_topic(self, topic: str) -> str:
        """Inicia tópico: sanitiza, gera explicação conceitual, retorna."""

    def send_message(self, user_message: str) -> str:
        """Processa mensagem livre do aluno. Retorna resposta da LLM."""

    def execute_command(self, command: str) -> tuple[str, bool]:
        """
        Executa comando (/exemplos, /perguntas, /resumo, /quiz_me).
        Retorna (conteúdo, is_cached).
        Se is_cached=True e não é /quiz_me, oferece opção de regenerar.
        """

    def regenerate(self, content_type: str) -> str:
        """Regenera conteúdo: consulta cache → se miss, chama API."""

    def handle_quiz(self) -> str:
        """Gera pergunta de quiz. Retorna pergunta."""

    def handle_quiz_answer(self, answer: str) -> str:
        """Avalia resposta do aluno. Retorna feedback."""

    def change_topic(self, new_topic: str) -> str:
        """Troca de tópico: limpa generated_types, mantém perfil e API."""

    def get_history(self) -> list[dict]:
        """Retorna histórico completo com metadata."""

    def save(self) -> None:
        """Persiste sessão e mensagens no SQLite."""
```

---

## 10. Modo Comparação de Versões (v1 vs v2) — `app/core/comparison.py`

### Fluxo

1. Aluno escolhe perfil → escolhe **uma única API** → digita tópico
2. Sistema gera os 4 tipos de conteúdo com v1 **E** v2 = **8 chamadas** (paralelas, com cache)
3. Exibição lado a lado com Rich, organizada por etapa:

```
━━━━━━━━━━━━━━ Explicação Conceitual ━━━━━━━━━━━━━━
┌──────────── v1 (Básico) ────────────┐┌──────────── v2 (Otimizado) ─────────┐
│ [conteúdo v1]                       ││ [conteúdo v2]                       │
│                                     ││                                     │
│ 🌐 Gerado agora (1.4s)             ││ ⚡ Cache (01/03 14:30)              │
└─────────────────────────────────────┘└─────────────────────────────────────┘

━━━━━━━━━━━━━━ Exemplos Práticos ━━━━━━━━━━━━━━━━━
┌──────────── v1 (Básico) ────────────┐┌──────────── v2 (Otimizado) ─────────┐
│ [conteúdo v1]                       ││ [conteúdo v2]                       │
└─────────────────────────────────────┘└─────────────────────────────────────┘

━━━━━━━━━━━━━ Perguntas de Reflexão ━━━━━━━━━━━━━━
┌──────────── v1 (Básico) ────────────┐┌──────────── v2 (Otimizado) ─────────┐
│ [conteúdo v1]                       ││ [conteúdo v2]                       │
└─────────────────────────────────────┘└─────────────────────────────────────┘

━━━━━━━━━━━━━━ Resumo Visual ━━━━━━━━━━━━━━━━━━━━
┌──────────── v1 (Básico) ────────────┐┌──────────── v2 (Otimizado) ─────────┐
│ [conteúdo v1]                       ││ [conteúdo v2]                       │
└─────────────────────────────────────┘└─────────────────────────────────────┘

📊 Cache: 2 hits / 6 misses
```

4. Ao final: "Deseja avaliar com LLM-as-judge (Gemini 2.5 Pro)? (s/n)"
5. Se sim → avaliação → notas + justificativa por tipo
6. **Sem continuação de conversa** — é geração one-shot
7. Tudo salvo no SQLite + exportável

---

## 11. Modo Comparação Multi-API — `app/core/comparison.py`

### Fluxo

1. Aluno escolhe perfil → digita tópico
2. Sistema gera os 4 tipos com **todas as APIs disponíveis**, sempre **v2**, em **paralelo**
3. Se 3 APIs: 3 × 4 = **12 chamadas** (com cache + paralelismo)
4. Exibição organizada por etapa:

```
━━━━━━━━━━━━━━ Explicação Conceitual ━━━━━━━━━━━━━━
┌──── Gemini Flash ────┐┌──── Groq/Llama 70B ───┐┌──── DeepSeek V3.2 ────┐
│ [conteúdo]           ││ [conteúdo]            ││ [conteúdo]            │
│ ⚡ Cache             ││ 🌐 0.8s              ││ 🌐 1.5s              │
└──────────────────────┘└───────────────────────┘└───────────────────────┘

[... mesma estrutura para Exemplos Práticos, Perguntas de Reflexão, Resumo Visual]

📊 Cache: 4 hits / 8 misses (33% economia) | Tempo total: 4.2s
```

5. Se alguma API falhar: exibe resultados das que responderam + mensagem de erro
6. Ao final: "Deseja avaliar com LLM-as-judge (Gemini 2.5 Pro)? (s/n)"
7. Se sim → avaliação comparativa entre APIs por tipo
8. **Sem continuação de conversa** — one-shot

---

## 12. LLM-as-Judge — `app/core/evaluator.py`

### Configuração

- **Sempre usa Gemini 2.5 Pro** (via `get_judge_adapter()`)
- **Só ativado nos modos de comparação**, nunca na sessão conversacional
- Duas modalidades: avaliação v1 vs v2 e avaliação multi-API

### Critérios de avaliação (1-10)

| Critério | O que avalia |
|---|---|
| Adequação ao nível | Conteúdo apropriado para a idade e nível do aluno |
| Clareza e coerência | Linguagem clara, lógica bem encadeada |
| Adequação ao estilo | Respeita o estilo de aprendizado do perfil |
| Engajamento pedagógico | Conteúdo interessante, motivador, pedagogicamente efetivo |

Além das notas, o judge gera justificativa textual e indica o vencedor.

```python
class ContentEvaluator:
    """Avaliador automático de conteúdo usando Gemini 2.5 Pro como judge."""

    def __init__(self):
        self.judge = get_judge_adapter()

    def evaluate_versions(self, v1_outputs: dict, v2_outputs: dict,
                          profile: dict, topic: str) -> dict:
        """Compara v1 vs v2 para cada tipo de conteúdo."""

    def evaluate_apis(self, api_outputs: dict[str, dict],
                      profile: dict, topic: str) -> dict:
        """Compara outputs de diferentes APIs para cada tipo."""
```

---

## 13. Exportação — `app/core/export.py`

### Dois formatos

**JSON** (requisito do desafio):
```python
def export_session_json(session_id: str, db: Database) -> str:
    """Exporta sessão completa como JSON estruturado."""

def export_comparison_json(comparison_data: dict) -> str:
    """Exporta resultado de comparação como JSON."""
```

**Markdown** (feature extra):
```python
def export_session_markdown(session_id: str, db: Database) -> str:
    """
    Exporta sessão como Markdown formatado.
    O avaliador pode abrir no GitHub/VS Code e ver o output bonito.
    """

def export_comparison_markdown(comparison_data: dict) -> str:
    """
    Exporta comparação como Markdown com tabelas e seções.
    Inclui notas do judge se disponíveis.
    """
```

Exemplo de Markdown exportado:
```markdown
# Sessão: Fotossíntese
**Perfil:** Ana (16 anos, intermediário, visual)
**API:** Gemini 2.5 Flash | **Data:** 01/03/2026 14:30

## 📚 Explicação Conceitual
[conteúdo]

## 🔬 Exemplos Práticos
[conteúdo]

## ❓ Perguntas de Reflexão
[conteúdo]

## 🗺️ Resumo Visual
[conteúdo]

---
*Gerado por EduPrompt Platform*
```

---

## 14. Onboarding — `app/core/onboarding.py`

### Dois fluxos de cadastro

**Fluxo direto:** nome → idade → nível → escolha de estilo (com descrições e emojis)

**Fluxo quiz VARK:** nome → idade → nível → "Não sei meu estilo" → 7 perguntas → calcula estilo → confirma ou altera

### Estilos

```python
LEARNING_STYLES = {
    "visual": {
        "nome": "Visual", "emoji": "👁️",
        "descricao": "Você aprende melhor com imagens, diagramas, gráficos e mapas mentais."
    },
    "auditivo": {
        "nome": "Auditivo", "emoji": "👂",
        "descricao": "Você aprende melhor ouvindo explicações e participando de discussões."
    },
    "leitura-escrita": {
        "nome": "Leitura/Escrita", "emoji": "📖",
        "descricao": "Você aprende melhor lendo textos, fazendo anotações e escrevendo resumos."
    },
    "cinestesico": {
        "nome": "Cinestésico", "emoji": "🤲",
        "descricao": "Você aprende melhor fazendo — atividades práticas e exercícios hands-on."
    }
}
```

### Quiz VARK (7 perguntas)

```python
VARK_QUIZ = [
    {
        "pergunta": "Quando precisa aprender a usar um novo aplicativo, você prefere:",
        "opcoes": {
            "visual": "Assistir um tutorial em vídeo com demonstrações",
            "auditivo": "Ouvir alguém explicar como funciona",
            "leitura-escrita": "Ler o manual ou um guia passo a passo",
            "cinestesico": "Abrir o app e ir explorando na prática"
        }
    },
    {
        "pergunta": "Em uma aula sobre um tema novo, o que mais te ajuda a entender?",
        "opcoes": {
            "visual": "Slides com gráficos, diagramas e esquemas",
            "auditivo": "A explicação falada do professor",
            "leitura-escrita": "Anotações detalhadas e textos complementares",
            "cinestesico": "Atividades em grupo ou exercícios práticos"
        }
    },
    {
        "pergunta": "Para estudar para uma prova, sua estratégia favorita é:",
        "opcoes": {
            "visual": "Fazer mapas mentais e esquemas coloridos",
            "auditivo": "Gravar resumos em áudio e ouvir depois",
            "leitura-escrita": "Reescrever a matéria com suas palavras",
            "cinestesico": "Resolver exercícios e problemas práticos"
        }
    },
    {
        "pergunta": "Quando alguém te explica um caminho, você prefere:",
        "opcoes": {
            "visual": "Ver um mapa ou desenho do trajeto",
            "auditivo": "Ouvir as instruções passo a passo",
            "leitura-escrita": "Receber as instruções escritas",
            "cinestesico": "Ir andando e descobrir pelo caminho"
        }
    },
    {
        "pergunta": "Ao montar um móvel novo, você:",
        "opcoes": {
            "visual": "Olha as figuras e diagramas do manual",
            "auditivo": "Pede para alguém te guiar falando",
            "leitura-escrita": "Lê todas as instruções antes de começar",
            "cinestesico": "Começa montando e consulta o manual só se travar"
        }
    },
    {
        "pergunta": "Para lembrar de uma informação importante, você:",
        "opcoes": {
            "visual": "Visualiza mentalmente onde leu ou viu aquilo",
            "auditivo": "Repete a informação em voz alta",
            "leitura-escrita": "Anota em um caderno ou post-it",
            "cinestesico": "Associa a informação a um gesto ou movimento"
        }
    },
    {
        "pergunta": "Se pudesse escolher como aprender um idioma novo, escolheria:",
        "opcoes": {
            "visual": "Flashcards com imagens e legendas",
            "auditivo": "Podcasts e músicas no idioma",
            "leitura-escrita": "Livros de gramática e exercícios escritos",
            "cinestesico": "Conversar com nativos e praticar em situações reais"
        }
    }
]
```

Em caso de empate: sistema informa os estilos empatados e pede que o aluno escolha.

---

## 15. Persistência — `app/storage/`

### SQLite schema

```sql
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('iniciante', 'intermediario', 'avancado')),
    learning_style TEXT NOT NULL CHECK (learning_style IN ('visual', 'auditivo', 'leitura-escrita', 'cinestesico')),
    context TEXT,
    quiz_answers JSON,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE sessions (
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

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_type TEXT CHECK (content_type IN (
        'free_chat', 'conceptual', 'practical', 'reflection', 'visual', 'quiz_question', 'quiz_answer', 'quiz_feedback'
    )),
    prompt_version TEXT CHECK (prompt_version IN ('v1', 'v2')),
    source TEXT CHECK (source IN ('api', 'cache')),
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE cache (
    hash TEXT PRIMARY KEY,
    response TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT
);

CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    evaluation_type TEXT NOT NULL CHECK (evaluation_type IN ('version_comparison', 'api_comparison')),
    evaluator_model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    criteria_scores JSON NOT NULL,
    justification TEXT NOT NULL,
    winner TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## 16. CLI — `app/cli/main.py` (Typer + Rich)

### Menu Principal

```
╔══════════════════════════════════════════╗
║        🎓 EduPrompt Platform            ║
╠══════════════════════════════════════════╣
║ APIs disponíveis: Gemini ✅  Groq ✅     ║
║                   DeepSeek ✅            ║
╚══════════════════════════════════════════╝

1. 📋  Listar perfis de alunos
2. ➕  Criar novo perfil
3. 💬  Iniciar sessão de aprendizado
4. 🔄  Comparar versões de prompt (v1 vs v2)
5. 📊  Comparar APIs
6. 📜  Ver histórico de sessões
7. 📁  Exportar resultados (JSON / Markdown)
8. 🚪  Sair

Escolha: _
```

### Fluxo detalhado de cada opção

#### Opção 1 — Listar perfis

```
📋 Perfis de Alunos
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌────┬────────┬───────┬────────────────┬─────────────────┐
│ #  │ Nome   │ Idade │ Nível          │ Estilo          │
├────┼────────┼───────┼────────────────┼─────────────────┤
│ 1  │ Ana    │ 16    │ Intermediário  │ 👁️ Visual       │
│ 2  │ Pedro  │ 10    │ Iniciante      │ 🤲 Cinestésico  │
│ 3  │ Maria  │ 22    │ Avançado       │ 📖 Leit./Escr.  │
│ 4  │ João   │ 14    │ Iniciante      │ 👂 Auditivo     │
│ 5  │ Carla  │ 35    │ Intermediário  │ 👁️ Visual       │
└────┴────────┴───────┴────────────────┴─────────────────┘

[Enter para voltar ao menu]
```

#### Opção 2 — Criar novo perfil

```
➕ Criar Novo Perfil
━━━━━━━━━━━━━━━━━━━━

Nome: _                          (validação: não vazio, max 50 chars)
Idade: _                         (validação: número 5-99)
Nível: [1] Iniciante  [2] Intermediário  [3] Avançado

Estilo de aprendizado:
  👁️  [1] Visual — Aprende com imagens, diagramas e esquemas
  👂  [2] Auditivo — Aprende ouvindo explicações e discussões
  📖  [3] Leitura/Escrita — Aprende lendo e fazendo anotações
  🤲  [4] Cinestésico — Aprende fazendo, com atividades práticas
  ❓  [5] Não sei! Quero descobrir (quiz de 7 perguntas)

Escolha: _

[Se 5 → quiz VARK]
[Se empate → "Seus estilos predominantes são X e Y. Qual se identifica mais?"]

Perfil criado: Ana, 16 anos, Intermediário, Visual. Confirma? (s/n)
```

#### Opção 3 — Sessão de aprendizado

```
💬 Nova Sessão de Aprendizado
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Selecione o perfil: [lista]
Selecione a API: [1] Gemini Flash  [2] Groq (Llama 70B)  [3] DeepSeek V3.2

Qual o tópico de estudo? _

⏳ Gerando explicação conceitual...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Explicação Conceitual — Fotossíntese         🌐 Gerado (1.4s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[conteúdo gerado pela LLM]

💬 Sessão ativa — digite sua mensagem ou "/" para ver comandos

Você: /

  Comandos disponíveis:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    /exemplos     Gerar exemplos práticos contextualizados
    /perguntas    Gerar perguntas de reflexão
    /resumo       Gerar resumo visual (mapa mental ASCII)
    /quiz_me      Testar seu conhecimento sobre o tópico
    /novo_topico  Iniciar um novo tópico de estudo
    /sair         Encerrar a sessão
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Você: /exemplos

⏳ Gerando exemplos práticos...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔬 Exemplos Práticos — Fotossíntese             🌐 Gerado (1.1s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[conteúdo gerado]

Você: /exemplos

⚠️  Já gerei exemplos práticos para este tópico.
  [1] Ver o anterior
  [2] Regenerar (nova chamada de API)

Você: /quiz_me

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 Hora do Quiz! — Fotossíntese
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[pergunta gerada pela LLM]

Sua resposta: _

[feedback da LLM: ✅ Correto! / 🟡 Parcialmente correto / ❌ Não exatamente...]

Você: Mas e se a planta não receber luz?

[resposta da LLM em conversa livre, usando histórico completo]

Você: /sair

Sessão encerrada. Histórico salvo. ✅
[Volta ao menu principal]
```

#### Opção 4 — Comparar versões (v1 vs v2)

```
🔄 Comparação de Versões de Prompt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Selecione o perfil: [lista]
Selecione a API: [1] Gemini  [2] Groq  [3] DeepSeek
Qual o tópico? _

⏳ Gerando 4 tipos × 2 versões (paralelo)...
  ████████████████████ 8/8
  ✅ Explicação Conceitual (v1 ⚡cache + v2 🌐 1.2s)
  ✅ Exemplos Práticos (v1 🌐 1.0s + v2 🌐 1.3s)
  ✅ Perguntas de Reflexão (v1 🌐 0.9s + v2 🌐 1.1s)
  ✅ Resumo Visual (v1 🌐 1.4s + v2 🌐 1.5s)

[Exibe 4 blocos lado a lado — formato seção 10]

📊 Cache: 1 hit / 7 misses | Tempo total: 3.8s

Deseja avaliar com LLM-as-judge (Gemini 2.5 Pro)? (s/n): _

[Se sim → gera avaliação → exibe notas e justificativa por tipo]
[Volta ao menu]
```

#### Opção 5 — Comparar APIs

```
📊 Comparação entre APIs
━━━━━━━━━━━━━━━━━━━━━━━━

Selecione o perfil: [lista]
Qual o tópico? _

⏳ Gerando 4 tipos × 3 APIs (paralelo, v2)...
  ████████████████████ 12/12
  ✅ Gemini Flash — 4 tipos (2.3s)
  ✅ Groq Llama 70B — 4 tipos (0.8s)
  ✅ DeepSeek V3.2 — 4 tipos (1.5s)

[Exibe blocos por etapa com 3 colunas — formato seção 11]

📊 Cache: 3 hits / 9 misses (25% economia) | Tempo total: 4.2s

Deseja avaliar com LLM-as-judge (Gemini 2.5 Pro)? (s/n): _

[Se sim → avaliação comparativa]
[Volta ao menu]
```

#### Opção 6 — Histórico

```
📜 Histórico de Sessões
━━━━━━━━━━━━━━━━━━━━━━━

┌────┬─────────────┬────────┬───────────────┬───────────────┬──────────┐
│ #  │ Data        │ Perfil │ Tópico        │ API           │ Modo     │
├────┼─────────────┼────────┼───────────────┼───────────────┼──────────┤
│ 1  │ 01/03 14:30 │ Ana    │ Fotossíntese  │ Gemini Flash  │ Conversa │
│ 2  │ 01/03 15:00 │ Ana    │ Fotossíntese  │ Groq          │ v1 vs v2 │
│ 3  │ 01/03 15:30 │ Pedro  │ Frações       │ Todas         │ Multi-API│
└────┴─────────────┴────────┴───────────────┴───────────────┴──────────┘

Selecione uma sessão para ver detalhes (ou Enter para voltar): _

[Se selecionar → exibe histórico de mensagens com content_type tags]
[Se tiver avaliação do judge → exibe notas]
```

#### Opção 7 — Exportar

```
📁 Exportar Resultados
━━━━━━━━━━━━━━━━━━━━━━

  [1] Exportar sessão específica
  [2] Exportar todas as sessões
  [3] Exportar avaliações do judge

Formato: [1] JSON  [2] Markdown  [3] Ambos

Escolha: _

[Gera arquivo(s) em ./samples/ com timestamp]
[Exibe: "✅ Exportado: samples/session_20260301_143000.json"]
[Exibe: "✅ Exportado: samples/session_20260301_143000.md"]
```

#### Opção 8 — Sair

```
Obrigado por usar o EduPrompt! 👋
Sessões salvas: 3 | Avaliações: 1

📊 Estatísticas da sessão:
  Cache: 10 hits / 22 misses (31% economia)
  Chamadas de API: Gemini 12 | Groq 8 | DeepSeek 6
```

### Comportamentos transversais

| Situação | Comportamento |
|---|---|
| Erro de API | Mensagem amigável com sugestão de ação (ver tabela seção 7) |
| Voltar ao menu | `q` ou `Ctrl+C` em qualquer submenu |
| APIs disponíveis | Exibidas no header do menu principal |
| Loading | `rich.spinner` + progress bar durante chamadas |
| Comando inexistente | "Comando não reconhecido. Digite / para ver comandos." |
| Input inválido | Re-solicita com mensagem de erro específica |

---

## 17. Web (Flask) — `app/web/`

| Rota | Método | Descrição |
|---|---|---|
| `/` | GET | Dashboard: perfis, sessões recentes, APIs disponíveis |
| `/profile/new` | GET/POST | Cadastro com quiz VARK opcional |
| `/profile/<id>` | GET | Ver perfil |
| `/session/new` | POST | Iniciar sessão conversacional |
| `/session/<id>` | GET | Interface de chat |
| `/session/<id>/message` | POST | Enviar mensagem (AJAX) |
| `/compare/versions` | GET/POST | Comparação v1 vs v2 |
| `/compare/apis` | GET/POST | Comparação multi-API |
| `/evaluate` | POST | Disparar LLM-as-judge |
| `/history` | GET | Histórico com filtros |
| `/quiz` | GET/POST | Quiz VARK standalone |
| `/export/<session_id>` | GET | Download JSON ou Markdown |

Interface com Bootstrap 5 (CDN).

---

## 18. Perfis Pré-definidos — `data/profiles.json`

```json
[
  {
    "id": "ana_16_inter_visual",
    "nome": "Ana", "idade": 16,
    "nivel": "intermediario", "estilo": "visual",
    "contexto": "Estudante do 2º ano do ensino médio, gosta de infográficos e vídeos"
  },
  {
    "id": "pedro_10_inic_cinest",
    "nome": "Pedro", "idade": 10,
    "nivel": "iniciante", "estilo": "cinestesico",
    "contexto": "Aluno do 5º ano, aprende melhor fazendo atividades práticas"
  },
  {
    "id": "maria_22_avanc_leitura",
    "nome": "Maria", "idade": 22,
    "nivel": "avancado", "estilo": "leitura-escrita",
    "contexto": "Universitária de Biologia, prefere textos acadêmicos"
  },
  {
    "id": "joao_14_inic_audit",
    "nome": "João", "idade": 14,
    "nivel": "iniciante", "estilo": "auditivo",
    "contexto": "Aluno do 9º ano, aprende melhor com explicações faladas"
  },
  {
    "id": "carla_35_inter_visual",
    "nome": "Carla", "idade": 35,
    "nivel": "intermediario", "estilo": "visual",
    "contexto": "Profissional em transição de carreira, aprendendo programação"
  }
]
```

---

## 19. Testes — `tests/` (última fase)

### Estratégia

Testes são a **última prioridade**. São implementados apenas após todo o core, CLI e Web estarem funcionando. Todos usam `unittest.mock.patch` — zero chamadas reais de API.

### Estrutura

| Arquivo | O que testa |
|---|---|
| `conftest.py` | Fixtures: perfil fake, adapter fake (retorna texto determinístico), DB `:memory:` |
| `test_profiles.py` | CRUD, validação de campos, carregamento do JSON |
| `test_prompt_engine.py` | Montagem parametrizada: 4 tipos × 2 versões × 4 estilos, sanitização |
| `test_adapters.py` | Mock das 3 APIs: formato, erros (timeout, 429, 401, resposta vazia) |
| `test_session.py` | Histórico cresce, comandos, repetição (Opção B), /quiz_me, troca de tópico |
| `test_onboarding.py` | Quiz VARK: cálculo, empates, validações |
| `test_cache.py` | Hit/miss, hash consistency, expiração, reuso entre modos |
| `test_evaluator.py` | Mock Gemini Pro, parsing de notas, formato |
| `test_comparison.py` | v1/v2 (8 chamadas), multi-API (12 chamadas), paralelismo, falha parcial |
| `test_content_generator.py` | Fluxo completo orquestrado |

### Boas práticas

- `@pytest.mark.parametrize` para combinações tipo × versão × estilo (32 combinações em uma função)
- `pytest-cov` com target de cobertura 80%+
- Fixtures reutilizáveis no `conftest.py`
- Pelo menos 2 testes de integração (fluxo completo com mocks)
- Foco no core, não nos templates

---

## 20. Deploy — Render

```
# Procfile
web: gunicorn "app.web.app:create_app()" --bind 0.0.0.0:$PORT
```

```yaml
# render.yaml
services:
  - type: web
    name: edu-prompt-platform
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn "app.web.app:create_app()" --bind 0.0.0.0:$PORT
    envVars:
      - key: GEMINI_API_KEY
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: DEEPSEEK_API_KEY
        sync: false
      - key: FLASK_SECRET_KEY
        sync: false
```

---

## 21. Dependências — `requirements.txt`

```
# APIs
google-generativeai>=0.8.0
openai>=1.0.0

# Web
flask>=3.0.0
gunicorn>=22.0.0

# CLI
typer>=0.12.0
rich>=13.0.0

# Utilidades
python-dotenv>=1.0.0

# Testes (última fase)
pytest>=8.0.0
pytest-mock>=3.0.0
pytest-cov>=5.0.0
```

---

## 22. Documentação

### README.md
- Descrição e arquitetura (diagrama Mermaid)
- APIs suportadas e configuração
- Como rodar (CLI e Web)
- Screenshots / GIFs da CLI
- Exemplos de uso
- Como rodar testes
- Link do deploy

### ARCHITECTURE.md
- Mapa da codebase para outras ferramentas/sessões de IA
- Explicação do adapter pattern
- Fluxo de dados entre módulos
- Decisões arquiteturais e justificativas

### PROMPT_ENGINEERING_NOTES.md
- Justificativa de cada técnica
- Adaptação por estilo de aprendizado
- Diferenças v1 vs v2 com outputs reais
- Resultados do LLM-as-judge
- Lições aprendidas

---

## 23. Ordem de Implementação

```
Fase 1 — Fundação (~2h)
  ├── 1.1 Setup: estrutura, requirements, .env.example, .gitignore, config.py
  ├── 1.2 Adapters: base + exceções + gemini + groq + deepseek + factory
  ├── 1.3 Perfis: profiles.json + loader + CRUD
  ├── 1.4 SQLite: schema + database.py
  └── 1.5 Onboarding: estilos + quiz VARK + calculate_style

Fase 2 — Core (~3h)
  ├── 2.1 PromptEngine: 4 builders × 2 versões × 4 estilos + sanitização + /quiz_me builders
  ├── 2.2 Cache: hash + SQLite + TTL + indicador de origem
  ├── 2.3 SessionManager: histórico, comandos, repetição (Opção B), /quiz_me, janela deslizante
  ├── 2.4 ContentGenerator: orquestrador
  ├── 2.5 Comparison: v1/v2 e multi-API com geração paralela (ThreadPoolExecutor)
  └── 2.6 Export: JSON + Markdown

Fase 3 — CLI (~2.5h)
  ├── 3.1 Menu principal (Typer + Rich)
  ├── 3.2 Sessão conversacional com comandos, "/", /quiz_me
  ├── 3.3 Modo comparação v1/v2 (lado a lado + progress bar)
  ├── 3.4 Modo comparação multi-API (lado a lado + progress bar)
  ├── 3.5 Histórico + Exportar (JSON/Markdown)
  └── 3.6 ARCHITECTURE.md (mapa para sessões seguintes)

Fase 4 — Web + Extras (~2.5h)
  ├── 4.1 Flask: rotas + templates + chat AJAX
  ├── 4.2 LLM-as-judge (evaluator)
  ├── 4.3 Gerar samples/ com outputs reais (JSON + Markdown)
  └── 4.4 Logging e tratamento de erros: revisão geral

Fase 5 — Entrega (~1h)
  ├── 5.1 README.md
  ├── 5.2 PROMPT_ENGINEERING_NOTES.md (com exemplos reais)
  ├── 5.3 Deploy no Render
  └── 5.4 Revisão final

Fase 6 — Testes (se houver tempo)
  ├── 6.1 conftest.py + fixtures
  ├── 6.2 Testes unitários parametrizados
  ├── 6.3 Testes de integração
  └── 6.4 Coverage report
```

**Tempo estimado: ~12h (sem testes) / ~14h (com testes)**

### Estratégia multi-ferramenta

| Ferramenta | Fases | Justificativa |
|---|---|---|
| **Claude Code** | Fase 1 + 2 + início da 3 | Arquitetura, adapters, core, paralelismo, cache |
| **Copilot/Antigravity** | Resto da 3 + 4 | Templates Flask, CSS, rotas, documentação |
| **Claude Code** | Fase 5 + 6 | Revisão, deploy, testes |

Na Fase 3.6, criar `ARCHITECTURE.md` para guiar sessões seguintes.

---

## 24. Checklist Final

### Requisitos Funcionais
- [x] Perfis de aluno (5 pré-definidos + cadastro + quiz VARK)
- [x] Motor de Prompt (persona, context, CoT, output formatting)
- [x] 4 tipos de conteúdo (explicação, exemplos, perguntas, visual)
- [x] Persistência (SQLite + JSON + Markdown export)
- [x] Comparação v1 vs v2 (versões de prompt, lado a lado)
- [x] Comparação multi-API (entre LLMs, lado a lado)
- [x] CLI (Typer + Rich) + Web (Flask)
- [x] Deploy em nuvem (Render)

### Qualidade Técnica
- [x] config.py centralizado
- [x] Type hints + docstrings
- [x] Cache com reuso entre modos + indicador visual + estatísticas
- [x] Tratamento de erros com exceções customizadas + retry
- [x] Logging padronizado (DEBUG/INFO/WARNING/ERROR)
- [x] Geração paralela (ThreadPoolExecutor)
- [x] Sanitização de input (anti prompt-injection)
- [x] Segurança (.env, .gitignore, secret key)

### Critérios de Avaliação
- [x] **Engenharia de Prompt (40%)**: v1/v2, 4 estilos, 4 tipos, documentação
- [x] **Implementação (30%)**: adapter pattern, cache inteligente, error handling, paralelismo
- [x] **Documentação (20%)**: README, ARCHITECTURE, PROMPT_ENGINEERING_NOTES, samples
- [x] **Criatividade (10%)**: LLM-as-judge, quiz VARK, /quiz_me, multi-API, sessão conversacional, export Markdown

### Entrega
- [x] Repositório Git com histórico
- [x] requirements.txt
- [x] .env.example
- [x] /samples (JSON + Markdown)
- [x] PROMPT_ENGINEERING_NOTES.md
- [x] ARCHITECTURE.md
