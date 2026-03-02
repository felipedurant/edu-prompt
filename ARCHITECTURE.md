# Arquitetura — EduPrompt Platform

Mapa da codebase para guiar desenvolvimento e sessões de IA.

## Estrutura de Diretórios

```
app/
├── config.py                 # Constantes, thresholds, configuração centralizada
├── adapters/                 # Adapter Pattern para LLMs
│   ├── __init__.py           # Factory: get_adapter(), list_available(), get_judge_adapter()
│   ├── base.py               # ABC LLMAdapter (generate, get_model_name, get_provider_name)
│   ├── exceptions.py         # LLMError, LLMConnectionError, LLMRateLimitError, etc.
│   ├── gemini_adapter.py     # Google Gemini (SDK próprio google-generativeai)
│   ├── groq_adapter.py       # Groq Llama 70B (formato OpenAI)
│   └── deepseek_adapter.py   # DeepSeek V3.2 (formato OpenAI)
├── core/                     # Lógica de negócio
│   ├── profiles.py           # CRUD de perfis (JSON file-based)
│   ├── prompt_engine.py      # CORAÇÃO: 4 builders × 2 versões × 4 estilos
│   ├── content_generator.py  # Orquestrador: engine + adapter + cache
│   ├── session.py            # SessionManager: conversa, comandos, quiz, sliding window
│   ├── onboarding.py         # Quiz VARK (7 perguntas) + estilos de aprendizado
│   ├── comparison.py         # Comparação v1/v2 e multi-API (ThreadPoolExecutor)
│   ├── evaluator.py          # LLM-as-judge (Gemini 2.5 Pro) — Fase 4
│   └── export.py             # Exportação JSON + Markdown
├── storage/
│   ├── database.py           # SQLite: schema, queries (sessions, messages, cache, evaluations)
│   └── cache.py              # CacheManager: SHA-256 hash, TTL, estatísticas
├── cli/
│   └── main.py               # CLI Typer + Rich: menu, sessão, comparações, histórico
└── web/                      # Flask — Fase 4
    ├── app.py
    ├── routes.py
    ├── templates/
    └── static/
```

## Fluxo de Dados

```
Usuário (CLI/Web)
    │
    ├─── Sessão Conversacional ──────────────────────────────┐
    │    1. select_profile() → dict                          │
    │    2. select_api() → get_adapter(provider)             │
    │    3. SessionManager(profile, adapter, engine, cache)  │
    │    4. start_topic(topic):                              │
    │       └─ PromptEngine.build_conceptual(profile, topic) │
    │          └─ CacheManager.get() → hit? return           │
    │             └─ adapter.generate() → content            │
    │                └─ CacheManager.set()                   │
    │    5. send_message() / execute_command() / quiz_me     │
    │    6. Database.add_message()                           │
    │                                                        │
    ├─── Comparação v1/v2 ──────────────────────────────────┐
    │    1. compare_versions(adapter, profile, topic, ...)   │
    │    2. ThreadPoolExecutor: 4 tipos × 2 versões = 8     │
    │    3. ContentGenerator.generate_single() para cada     │
    │    4. Cache consultado ANTES de cada chamada           │
    │    5. Resultados organizados por tipo                  │
    │                                                        │
    └─── Comparação Multi-API ──────────────────────────────┐
         1. compare_apis(profile, topic, ...)                │
         2. get_adapter() para cada API disponível           │
         3. ThreadPoolExecutor: 4 tipos × N APIs             │
         4. Cache global compartilhado entre modos           │
         5. APIs que falham → erro parcial, não trava        │
```

## Adapter Pattern

```
        LLMAdapter (ABC)
        ├── generate(messages, system_prompt, temperature) → str
        ├── get_model_name() → str
        └── get_provider_name() → str
             │
    ┌────────┼────────────┐
    │        │            │
GeminiAdapter  GroqAdapter  DeepSeekAdapter
(SDK próprio)  (OpenAI fmt)  (OpenAI fmt)
```

- **Factory**: `get_adapter("gemini")` retorna adapter configurado
- **Judge**: `get_judge_adapter()` retorna Gemini 2.5 Pro (exclusivo)
- **Disponibilidade**: `list_available()` filtra por chaves no `.env`

## Prompt Engine (40% da nota)

Técnicas aplicadas em TODOS os prompts:

| Técnica | v1 (Básico) | v2 (Otimizado) |
|---|---|---|
| Persona | Professor genérico | Especializado por faixa etária e estilo |
| Context | Dados básicos em texto | Perfil estruturado com level descriptions |
| Chain-of-Thought | "Pense passo a passo" | Scaffolding progressivo com checkpoints |
| Output Formatting | Instrução genérica | Estrutura detalhada com constraints |

4 estilos × 4 tipos × 2 versões = 32 combinações possíveis.

## Cache

- **Chave**: SHA-256 de `provider + model + system_prompt + messages + temperature`
- **Global**: compartilhado entre sessão, comparação v1/v2 e multi-API
- **TTL**: configurável (padrão 24h, 0 = sem expiração)
- **Stats**: hits/misses rastreados por sessão

## SQLite Schema

5 tabelas: `profiles`, `sessions`, `messages`, `cache`, `evaluations`

## Decisões Arquiteturais

1. **SQLite sobre JSON puro**: suporte a queries complexas, cache TTL, integridade referencial
2. **ThreadPoolExecutor sobre asyncio**: simplicidade, compatibilidade com SDKs síncronos
3. **Adapter Pattern**: demonstra flexibilidade (Gemini SDK próprio vs OpenAI-compatíveis)
4. **Cache global**: economia real cross-mode (sessão → comparação reutiliza resultados)
5. **Sliding window**: estimativa simples (chars/4), suficiente para PT-BR
