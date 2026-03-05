# [EduPrompt Platform](https://edu-prompt.onrender.com/)


Plataforma educacional com IA personalizada que gera conteudo adaptado ao perfil de cada aluno, utilizando tecnicas avancadas de engenharia de prompt.

## Visao Geral

O EduPrompt combina **engenharia de prompt** com **pedagogia adaptativa** para gerar conteudo educacional personalizado. O sistema utiliza multiplas APIs de LLM (Gemini, Groq, OpenRouter) e aplica 4 tecnicas fundamentais em todos os prompts:

- **Persona Prompting** -- professor especializado calibrado por faixa etaria
- **Context Setting** -- dados do aluno (idade, nivel, estilo de aprendizado) injetados no prompt
- **Chain-of-Thought** -- raciocinio passo a passo com scaffolding progressivo
- **Output Formatting** -- formato de saida especifico por tipo de conteudo

### Funcionalidades Principais

| Funcionalidade        | Descricao                                                                       |
| --------------------- | ------------------------------------------------------------------------------- |
| Perfis de aluno       | 5 pre-definidos + cadastro com quiz VARK (7 perguntas)                          |
| 4 tipos de conteudo   | Explicacao conceitual, exemplos praticos, perguntas de reflexao, resumo visual  |
| Sessao conversacional | Chat interativo com comandos (`/exemplos`, `/perguntas`, `/resumo`, `/quiz_me`) |
| Comparacao v1 vs v2   | Prompts basicos vs otimizados lado a lado                                       |
| Comparacao multi-API  | Mesma solicitacao em multiplos modelos de IA                                    |
| LLM-as-Judge          | Avaliacao automatica com DeepSeek V3.2 (4 criterios, notas 1-10)                |
| Cache inteligente     | SHA-256, global, compartilhado entre modos, TTL configuravel                    |
| Geracao paralela      | ThreadPoolExecutor para comparacoes (ate 4x mais rapido)                        |
| Exportacao            | JSON + Markdown                                                                 |
| Interface dupla       | CLI (Typer + Rich) + Web (Flask)                                                |

## Instalacao

### Pre-requisitos

- Python 3.12+
- Pelo menos 1 chave de API configurada

### Setup

```bash
# Clonar repositorio
git clone https://github.com/felipedurant/edu-prompt.git
cd edu-prompt

# Instalar dependencias
pip install -r requirements.txt

# Configurar chaves de API
cp .env.example .env
# Editar .env com suas chaves
```

### Chaves de API

| Provedor      | Variavel             | Obtencao                                            |
| ------------- | -------------------- | --------------------------------------------------- |
| Google Gemini | `GEMINI_API_KEY`     | [aistudio.google.com](https://aistudio.google.com/) |
| Groq          | `GROQ_API_KEY`       | [console.groq.com](https://console.groq.com/)       |
| OpenRouter    | `OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai/)             |

Nenhuma exige cartao de credito. O sistema so exibe modelos com chave configurada.

## Uso

### CLI (Typer + Rich)

```bash
python -m app.cli.main run
```

Menu principal:
```
1. Listar perfis de alunos
2. Criar novo perfil
3. Iniciar sessao de aprendizado
4. Comparar versoes de prompt (v1 vs v2)
5. Comparar Modelos
6. Ver historico de sessoes
7. Exportar resultados (JSON / Markdown)
8. Sair
```

### Comandos na sessao conversacional

```
/exemplos     Gerar exemplos praticos contextualizados
/perguntas    Gerar perguntas de reflexao e pensamento critico
/resumo       Gerar resumo visual (mapa mental/diagrama ASCII)
/quiz_me      Testar seu conhecimento sobre o topico
/novo_topico  Iniciar um novo topico de estudo
/sair         Encerrar a sessao de aprendizado
```

### Web (Flask)

```bash
# Desenvolvimento
flask --app app.web.app:create_app run --debug

# Producao
gunicorn "app.web.app:create_app()" --bind 0.0.0.0:8000
```

## Arquitetura

```
app/
├── config.py                 # Configuracao centralizada
├── adapters/                 # Adapter Pattern para LLMs
│   ├── base.py               # ABC LLMAdapter
│   ├── exceptions.py         # Excecoes customizadas
│   ├── gemini_adapter.py     # Google Gemini (SDK proprio)
│   ├── groq_adapter.py       # Groq (formato OpenAI)
│   └── openrouter_adapter.py # OpenRouter (formato OpenAI)
├── core/                     # Logica de negocio
│   ├── prompt_engine.py      # Motor de prompt (4 tipos x 2 versoes x 4 estilos)
│   ├── content_generator.py  # Orquestrador: engine + adapter + cache
│   ├── session.py            # Sessao conversacional com comandos
│   ├── comparison.py         # Comparacao v1/v2 e multi-API (paralela)
│   ├── evaluator.py          # LLM-as-judge (DeepSeek V3.2 via OpenRouter)
│   ├── onboarding.py         # Quiz VARK + estilos de aprendizado
│   ├── profiles.py           # CRUD de perfis
│   └── export.py             # Exportacao JSON + Markdown
├── storage/
│   ├── database.py           # SQLite (5 tabelas)
│   └── cache.py              # Cache SHA-256 com TTL
├── cli/
│   └── main.py               # CLI Typer + Rich
└── web/
    ├── app.py                # Flask factory
    ├── routes.py             # Rotas + API AJAX
    ├── templates/            # HTML (Jinja2)
    └── static/               # CSS
```

### Decisoes Arquiteturais

1. **Adapter Pattern**: demonstra flexibilidade -- Gemini usa SDK proprio, Groq/OpenRouter usam formato OpenAI
2. **Cache global**: compartilhado entre sessao, comparacao v1/v2 e multi-API (economia real cross-mode)
3. **SQLite sobre JSON**: suporte a queries complexas, cache TTL, integridade referencial
4. **ThreadPoolExecutor sobre asyncio**: simplicidade e compatibilidade com SDKs sincronos
5. **Sliding window**: estimativa de tokens por caracteres (chars/4), suficiente para PT-BR

### Motor de Prompt (40% da nota)

32 combinacoes possiveis: **4 tipos x 2 versoes x 4 estilos**

| Tecnica           | v1 (Basico)            | v2 (Otimizado)                            |
| ----------------- | ---------------------- | ----------------------------------------- |
| Persona           | Professor generico     | Especializado por faixa etaria e estilo   |
| Context           | Dados basicos em texto | Perfil estruturado com level descriptions |
| Chain-of-Thought  | "Pense passo a passo"  | Scaffolding progressivo com checkpoints   |
| Output Formatting | Instrucao generica     | Estrutura detalhada com constraints       |

## Modelos Suportados

| Provedor      | Modelos                                    | Uso                        |
| ------------- | ------------------------------------------ | -------------------------- |
| Google Gemini | Gemini 2.5 Flash, Gemini 3 Flash Preview   | SDK proprio (google-genai) |
| Groq          | Llama 4 Scout, GPT-OSS 120B, Qwen 3 32B    | OpenAI-compativel          |
| OpenRouter    | GPT-4.1 Mini, Grok 4.1 Fast, DeepSeek V3.2 | OpenAI-compativel          |

LLM-as-Judge: DeepSeek V3.2 via OpenRouter (exclusivo para avaliacao automatica).

## Testes

```bash
# Rodar testes
pytest

# Com cobertura
pytest --cov=app --cov-report=term-missing

# Apenas testes unitarios
pytest tests/test_unit.py -v
```

## Deploy (Render)

O projeto inclui `render.yaml` e `Procfile` para deploy no Render (free tier):

```bash
# render.yaml ja configurado
# Basta conectar o repositorio no Render Dashboard
```

Variaveis de ambiente necessarias no Render:
- `GEMINI_API_KEY`
- `GROQ_API_KEY` (opcional)
- `OPENROUTER_API_KEY` (opcional)
- `FLASK_SECRET_KEY` (gerar valor aleatorio para producao)

## Estrutura do Banco de Dados

5 tabelas SQLite com integridade referencial:

- `profiles` -- perfis de alunos
- `sessions` -- sessoes (conversa, compare_versions, compare_apis)
- `messages` -- historico com content_type, prompt_version, source
- `cache` -- hash SHA-256, response, TTL
- `evaluations` -- avaliacoes do LLM-as-judge

## Exemplos de Output

Ver pasta `samples/` para exemplos completos em JSON e Markdown:

- `session_example.json` -- sessao conversacional sobre Matéria Escura (formato JSON estruturado)
- `session_example.md` -- mesma sessao exportada em Markdown legivel
- `comparison.json` -- sessão de conversa comparando prompts v1 e v2 ambas sobre Leis de Newton (formato JSON estruturado) -> LLM-as-Judge ilustrando bem a diferença de uma boa engenharia de prompt
- `comparison.md` -- mesma sessão exportada em Markdown legível

## Documentacao

- `ARCHITECTURE.md` -- mapa detalhado da codebase e decisoes arquiteturais
- `PROMPT_ENGINEERING_NOTES.md` -- documentacao das tecnicas de engenharia de prompt com exemplos e evidencias

## Tecnologias

- **Python 3.12+**
- **APIs**: google-genai, openai (Groq/OpenRouter)
- **CLI**: Typer + Rich
- **Web**: Flask + Jinja2 + JavaScript (AJAX)
- **Persistencia**: SQLite
- **Testes**: pytest + pytest-cov + pytest-mock
- **Deploy**: Gunicorn + Render
