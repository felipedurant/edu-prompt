"""CLI com Typer + Rich — Interface principal da plataforma EduPrompt."""

import logging
import os
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.columns import Columns
from rich.markdown import Markdown
from rich.text import Text

from app.config import LOG_LEVEL, LOG_FORMAT, VALID_LEVELS, VALID_STYLES, CONTENT_TYPES, MODEL_REGISTRY, JUDGE_API_KEY_ENV
from app.adapters import get_adapter, list_available, LLMError
from app.core.evaluator import ContentEvaluator
from app.core.profiles import load_profiles, create_profile, get_profile_by_index
from app.core.onboarding import (
    LEARNING_STYLES,
    get_quiz_questions,
    calculate_style,
    get_style_display,
)
from app.core.prompt_engine import PromptEngine
from app.core.session import SessionManager, COMMANDS_HELP
from app.core.comparison import (
    compare_versions,
    compare_models,
    CONTENT_TYPE_LABELS,
)
from app.core.export import (
    export_session_json,
    export_session_markdown,
    export_comparison_json,
    export_comparison_markdown,
    save_export,
)
from app.storage.database import Database
from app.storage.cache import CacheManager

# Setup logging — logs vão para arquivo para não poluir o terminal
_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "eduprompt.log")
os.makedirs(os.path.dirname(_log_file), exist_ok=True)
_file_handler = logging.FileHandler(_log_file, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logging.root.addHandler(_file_handler)
logging.root.setLevel(LOG_LEVEL)

# Silenciar logs de bibliotecas no console (httpx, openai, etc.)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Remover handlers de console que possam existir
for h in logging.root.handlers[:]:
    if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
        logging.root.removeHandler(h)

logger = logging.getLogger(__name__)

app = typer.Typer(help="EduPrompt Platform — Plataforma educacional com IA personalizada")
console = Console()

# ─── Instâncias globais ─────────────────────────────────

_db: Database | None = None
_cache: CacheManager | None = None
_engine: PromptEngine | None = None


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


# ─── Helpers de display ─────────────────────────────────

def show_header():
    """Exibe header com modelos disponíveis."""
    available = list_available()
    model_status = []
    for key, entry in MODEL_REGISTRY.items():
        status = "\u2705" if key in available else "\u274c"
        model_status.append(f"{entry['label']} {status}")

    console.print(Panel(
        f"[bold]Modelos dispon\u00edveis:[/bold]\n" + "\n".join(model_status),
        title="\U0001f393 EduPrompt Platform",
        border_style="blue",
    ))


def show_source_indicator(source: str, elapsed: float = 0, cached_at: str = ""):
    """Exibe indicador de origem (cache ou API)."""
    if source == "cache":
        when = f" (gerado em {cached_at})" if cached_at else ""
        console.print(f"  \u26a1 [yellow]Cache{when}[/yellow]")
    elif source == "api":
        console.print(f"  \U0001f310 [green]Gerado agora ({elapsed}s)[/green]")


def select_profile() -> dict | None:
    """Menu de seleção de perfil."""
    profiles = load_profiles()
    if not profiles:
        console.print("[red]Nenhum perfil cadastrado.[/red]")
        return None

    table = Table(title="\U0001f4cb Perfis de Alunos")
    table.add_column("#", style="dim", width=4)
    table.add_column("Nome", style="bold")
    table.add_column("Idade", justify="center")
    table.add_column("N\u00edvel")
    table.add_column("Estilo")

    for i, p in enumerate(profiles):
        table.add_row(
            str(i + 1),
            p["nome"],
            str(p["idade"]),
            p["nivel"].capitalize(),
            get_style_display(p["estilo"]),
        )

    console.print(table)

    while True:
        try:
            choice = IntPrompt.ask("[bold cyan]Perfil[/bold cyan]")
            profile = get_profile_by_index(choice - 1)
            if profile:
                return profile
            console.print("[red]N\u00famero inv\u00e1lido.[/red]")
        except KeyboardInterrupt:
            return None


def select_model() -> str | None:
    """Menu de seleção de modelo."""
    available = list_available()
    if not available:
        console.print("[red]Nenhum modelo configurado. Verifique seu .env[/red]")
        return None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Modelo")
    table.add_column("Provedor", style="dim")

    mapping = {}
    for i, key in enumerate(available):
        entry = MODEL_REGISTRY[key]
        table.add_row(str(i + 1), entry["label"], entry["provider"].capitalize())
        mapping[str(i + 1)] = key

    console.print(Panel(table, title="\U0001f916 Selecione o modelo", border_style="cyan"))

    while True:
        choice = Prompt.ask("[bold cyan]Modelo[/bold cyan]")
        if choice in mapping:
            return mapping[choice]
        console.print("[red]Op\u00e7\u00e3o inv\u00e1lida.[/red]")


# ─── Opção 1: Listar perfis ─────────────────────────────

def cmd_list_profiles():
    """Exibe lista de perfis."""
    profiles = load_profiles()
    if not profiles:
        console.print("[yellow]Nenhum perfil cadastrado. Use a op\u00e7\u00e3o 2 para criar.[/yellow]")
        return

    table = Table(title="\U0001f4cb Perfis de Alunos")
    table.add_column("#", style="dim", width=4)
    table.add_column("Nome", style="bold")
    table.add_column("Idade", justify="center")
    table.add_column("N\u00edvel")
    table.add_column("Estilo")
    table.add_column("Contexto", style="dim")

    for i, p in enumerate(profiles):
        table.add_row(
            str(i + 1),
            p["nome"],
            str(p["idade"]),
            p["nivel"].capitalize(),
            get_style_display(p["estilo"]),
            (p.get("contexto", "")[:40] + "...") if len(p.get("contexto", "")) > 40 else p.get("contexto", ""),
        )

    console.print(table)
    Prompt.ask("\n[dim]Enter para voltar ao menu[/dim]", default="")


# ─── Opção 2: Criar perfil ──────────────────────────────

def cmd_create_profile():
    """Fluxo de cadastro de perfil com quiz VARK opcional."""
    console.print(Panel("\u2795 Criar Novo Perfil", border_style="green"))

    # Nome
    while True:
        nome = Prompt.ask("Nome")
        if nome.strip() and len(nome.strip()) <= 50:
            break
        console.print("[red]Nome inv\u00e1lido (1-50 caracteres).[/red]")

    # Idade
    while True:
        try:
            idade = IntPrompt.ask("Idade")
            if 5 <= idade <= 99:
                break
            console.print("[red]Idade deve ser entre 5 e 99.[/red]")
        except ValueError:
            console.print("[red]Digite um n\u00famero v\u00e1lido.[/red]")

    # Nível
    console.print("N\u00edvel: [1] Iniciante  [2] Intermedi\u00e1rio  [3] Avan\u00e7ado")
    level_map = {"1": "iniciante", "2": "intermediario", "3": "avancado"}
    while True:
        choice = Prompt.ask("Escolha", default="1")
        if choice in level_map:
            nivel = level_map[choice]
            break
        console.print("[red]Op\u00e7\u00e3o inv\u00e1lida.[/red]")

    # Estilo
    console.print("\nEstilo de aprendizado:")
    for i, (key, info) in enumerate(LEARNING_STYLES.items(), 1):
        console.print(f"  {info['emoji']}  [{i}] {info['nome']} \u2014 {info['descricao']}")
    console.print(f"  \u2753  [5] N\u00e3o sei! Quero descobrir (quiz de 7 perguntas)")

    style_map = {str(i+1): key for i, key in enumerate(LEARNING_STYLES.keys())}
    quiz_answers = None

    while True:
        choice = Prompt.ask("Escolha", default="5")
        if choice in style_map:
            estilo = style_map[choice]
            break
        elif choice == "5":
            # Quiz VARK
            estilo, quiz_answers = _run_vark_quiz()
            break
        console.print("[red]Op\u00e7\u00e3o inv\u00e1lida.[/red]")

    # Contexto opcional
    contexto = Prompt.ask("Contexto adicional (opcional, ex: 'estudante de biologia')", default="")

    # Confirmação
    console.print(
        f"\nPerfil: [bold]{nome}[/bold], {idade} anos, "
        f"{nivel.capitalize()}, {get_style_display(estilo)}"
    )
    if Confirm.ask("Confirma?", default=True):
        profile = create_profile(nome, idade, nivel, estilo, contexto, quiz_answers)
        console.print(f"[green]\u2705 Perfil criado: {profile['nome']}[/green]")
    else:
        console.print("[yellow]Cancelado.[/yellow]")


def _run_vark_quiz() -> tuple[str, list[str]]:
    """Executa quiz VARK e retorna (estilo, respostas)."""
    console.print(Panel("\U0001f9e0 Quiz VARK \u2014 Descubra seu estilo de aprendizado", border_style="cyan"))
    console.print("[dim]Responda as 7 perguntas escolhendo a op\u00e7\u00e3o que mais combina com voc\u00ea.[/dim]\n")

    questions = get_quiz_questions()
    answers = []

    for q in questions:
        console.print(f"[bold]Pergunta {q['number']}/7:[/bold] {q['question']}")
        for i, opt in enumerate(q["options"]):
            console.print(f"  [{i+1}] {opt['emoji']} {opt['text']}")

        while True:
            choice = Prompt.ask("Escolha", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(q["options"]):
                    answers.append(q["options"][idx]["key"])
                    break
            except ValueError:
                pass
            console.print("[red]Op\u00e7\u00e3o inv\u00e1lida.[/red]")

        console.print()

    result = calculate_style(answers)

    if result["tied"]:
        console.print(
            f"[yellow]Empate entre: {', '.join(get_style_display(s) for s in result['tied_styles'])}[/yellow]"
        )
        console.print("Qual se identifica mais?")
        for i, s in enumerate(result["tied_styles"]):
            console.print(f"  [{i+1}] {get_style_display(s)}")

        while True:
            choice = Prompt.ask("Escolha", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(result["tied_styles"]):
                    estilo = result["tied_styles"][idx]
                    break
            except ValueError:
                pass
            console.print("[red]Op\u00e7\u00e3o inv\u00e1lida.[/red]")
    else:
        estilo = result["style"]

    console.print(f"\n\u2705 Seu estilo: [bold]{get_style_display(estilo)}[/bold]")
    console.print(f"[dim]Pontua\u00e7\u00e3o: {result['scores']}[/dim]")

    return estilo, answers


# ─── Opção 3: Sessão conversacional ─────────────────────

def cmd_session():
    """Sessão conversacional interativa."""
    console.print(Panel("\U0001f4ac Nova Sess\u00e3o de Aprendizado", border_style="cyan"))

    profile = select_profile()
    if not profile:
        return

    model_key = select_model()
    if not model_key:
        return

    topic = Prompt.ask("\U0001f4d6 [bold cyan]Qual o t\u00f3pico de estudo?[/bold cyan]")
    if not topic.strip():
        console.print("[red]T\u00f3pico n\u00e3o pode ser vazio.[/red]")
        return

    try:
        adapter = get_adapter(model_key)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return

    session = SessionManager(profile, adapter, get_engine(), get_cache(), get_db())

    # Gera explicação conceitual inicial
    with console.status("\u23f3 Gerando explica\u00e7\u00e3o conceitual..."):
        try:
            result = session.start_topic(topic)
        except LLMError as e:
            console.print(f"[red]\u26a0\ufe0f Erro: {e}[/red]")
            return

    _display_content("Explica\u00e7\u00e3o Conceitual", topic, result)

    console.print(
        f'\n\U0001f4ac [bold]Sess\u00e3o ativa[/bold] \u2014 {profile["nome"]} \u2022 {topic}\n'
    )
    _print_command_hint()

    # Loop da sessão
    while True:
        try:
            if session.has_quiz_pending:
                prompt_label = "[bold magenta]Sua resposta[/bold magenta]"
            else:
                topic_short = session.current_topic[:25] + ("..." if len(session.current_topic) > 25 else "")
                prompt_label = f"[bold cyan]Voc\u00ea[/bold cyan] [dim]({topic_short})[/dim]"
            user_input = Prompt.ask(prompt_label)
        except (KeyboardInterrupt, EOFError):
            session.end()
            console.print("\n[yellow]Sess\u00e3o encerrada.[/yellow]")
            break

        user_input = user_input.strip()
        if not user_input:
            _show_commands()
            continue

        # /sair
        if user_input == "/sair":
            session.end()
            console.print("[green]\u2705 Sess\u00e3o encerrada. Hist\u00f3rico salvo.[/green]")
            break

        # /novo_topico
        if user_input.startswith("/novo_topico"):
            new_topic = user_input.replace("/novo_topico", "").strip()
            if not new_topic:
                new_topic = Prompt.ask("Novo t\u00f3pico")
            if not new_topic.strip():
                console.print("[red]T\u00f3pico n\u00e3o pode ser vazio.[/red]")
                continue

            with console.status("\u23f3 Gerando explica\u00e7\u00e3o conceitual..."):
                try:
                    result = session.change_topic(new_topic)
                except LLMError as e:
                    console.print(f"[red]\u26a0\ufe0f {e}[/red]")
                    continue

            _display_content("Explica\u00e7\u00e3o Conceitual", new_topic, result)
            _print_command_hint()
            continue

        # /quiz_me
        if user_input == "/quiz_me":
            _handle_quiz(session)
            continue

        # Comandos de conteúdo (/exemplos, /perguntas, /resumo)
        if user_input in COMMANDS_HELP and user_input not in ("/quiz_me", "/novo_topico", "/sair"):
            _handle_content_command(session, user_input)
            _print_command_hint()
            continue

        # Resposta ao quiz pendente
        if session.has_quiz_pending:
            with console.status("\u23f3 Avaliando sua resposta..."):
                try:
                    result = session.handle_quiz_answer(user_input)
                except LLMError as e:
                    console.print(f"[red]\u26a0\ufe0f {e}[/red]")
                    continue
            console.print()
            console.print(Markdown(result["content"]))
            show_source_indicator(result["source"], result["elapsed"])
            console.print()
            _print_command_hint()
            continue

        # Conversa livre
        with console.status("\u23f3 Pensando..."):
            try:
                result = session.send_message(user_input)
            except LLMError as e:
                console.print(f"[red]\u26a0\ufe0f {e}[/red]")
                continue

        console.print()
        console.print(Markdown(result["content"]))
        show_source_indicator(result["source"], result["elapsed"])
        console.print()
        _print_command_hint()


def _print_command_hint():
    """Imprime linha compacta com comandos disponíveis."""
    hint = Text()
    hint.append("  [Enter = detalhar comandos]", style="dim")
    hint.append("  Comandos: ", style="dim")
    commands = ["/exemplos", "/perguntas", "/resumo", "/quiz_me", "/novo_topico", "/sair"]
    for i, cmd in enumerate(commands):
        if i > 0:
            hint.append("  ", style="dim")
        hint.append(cmd, style="dim cyan")
    console.print(hint)


def _show_commands():
    """Exibe lista de comandos disponíveis com descrições."""
    detailed_commands = {
        "Enter": "Ver esta lista de comandos",
        "/exemplos": "Gera exemplos práticos do tópico adaptados ao seu perfil",
        "/perguntas": "Gera perguntas de reflexão para testar compreensão",
        "/resumo": "Gera mapa mental ou diagrama ASCII do tópico",
        "/quiz_me": "A IA faz uma pergunta e avalia sua resposta",
        "/novo_topico": "Troca o tópico (mantém perfil e API)",
        "/sair": "Encerra e salva a sessão",
    }
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Comando", style="bold cyan")
    table.add_column("Descri\u00e7\u00e3o")
    for cmd, desc in detailed_commands.items():
        table.add_row(cmd, desc)
    console.print(Panel(table, title="Comandos dispon\u00edveis", border_style="cyan"))


def _display_content(title: str, topic: str, result: dict):
    """Exibe conteúdo gerado com formatação Rich."""
    console.print()
    header = f"\U0001f4da {title} \u2014 {topic}"
    console.print(Panel(Markdown(result["content"]), title=header, border_style="green"))
    show_source_indicator(result["source"], result.get("elapsed", 0), result.get("cached_at", ""))


def _handle_content_command(session: SessionManager, command: str):
    """Trata comandos de conteúdo com lógica de repetição."""
    label_map = {
        "/exemplos": "exemplos pr\u00e1ticos",
        "/perguntas": "perguntas de reflex\u00e3o",
        "/resumo": "resumo visual",
    }
    label = label_map.get(command, command)

    with console.status(f"\u23f3 Gerando {label}..."):
        try:
            result = session.execute_command(command)
        except LLMError as e:
            console.print(f"[red]\u26a0\ufe0f {e}[/red]")
            return

    if result.get("already_generated"):
        console.print(f"\n[yellow]\u26a0\ufe0f  J\u00e1 gerei {label} para este t\u00f3pico.[/yellow]")
        console.print("  [1] Ver o anterior")
        console.print("  [2] Regenerar (nova chamada de API)")

        choice = Prompt.ask("Escolha", default="1")
        if choice == "2":
            ct = result["content_type"]
            with console.status(f"\u23f3 Regenerando {label}..."):
                try:
                    result = session.regenerate(ct)
                except LLMError as e:
                    console.print(f"[red]\u26a0\ufe0f {e}[/red]")
                    return
        # else: exibe o anterior (result já contém)

    title_map = {
        "/exemplos": "Exemplos Pr\u00e1ticos",
        "/perguntas": "Perguntas de Reflex\u00e3o",
        "/resumo": "Resumo Visual",
    }
    _display_content(title_map.get(command, command), session.current_topic, result)


def _handle_quiz(session: SessionManager):
    """Fluxo do /quiz_me."""
    with console.status("\u23f3 Gerando pergunta de quiz..."):
        try:
            result = session.handle_quiz()
        except LLMError as e:
            console.print(f"[red]\u26a0\ufe0f {e}[/red]")
            return

    console.print()
    console.print(Panel(
        Markdown(result["content"]),
        title=f"\U0001f9e0 Hora do Quiz! \u2014 {session.current_topic}",
        border_style="magenta",
    ))
    show_source_indicator(result["source"], result["elapsed"])
    console.print("\n[bold magenta]Sua resposta:[/bold magenta] ", end="")


# ─── Opção 4: Comparar versões ──────────────────────────

def cmd_compare_versions():
    """Modo de comparação v1 vs v2."""
    console.print(Panel("\U0001f504 Compara\u00e7\u00e3o de Vers\u00f5es de Prompt", border_style="yellow"))

    profile = select_profile()
    if not profile:
        return

    model_key = select_model()
    if not model_key:
        return

    topic = Prompt.ask("\U0001f4d6 [bold cyan]Qual o t\u00f3pico?[/bold cyan]")
    if not topic.strip():
        console.print("[red]T\u00f3pico n\u00e3o pode ser vazio.[/red]")
        return

    try:
        adapter = get_adapter(model_key)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return

    cache = get_cache()
    cache.reset_stats()

    total = len(CONTENT_TYPES) * 2

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"\u23f3 Gerando {total} conte\u00fados (4 tipos \u00d7 2 vers\u00f5es)...",
            total=total,
        )

        def on_progress(completed, total_tasks, desc):
            progress.update(task, completed=completed, description=f"\u23f3 {desc}")

        try:
            result = compare_versions(
                adapter, profile, topic, get_engine(), cache, get_db(),
                progress_callback=on_progress,
            )
        except LLMError as e:
            console.print(f"[red]\u26a0\ufe0f {e}[/red]")
            return

    # Exibir resultados lado a lado
    _display_version_comparison(result)

    # Estatísticas de cache
    stats = result["cache_stats"]
    console.print(
        f"\n\U0001f4ca Cache: {stats['hits']} hits / {stats['misses']} misses | "
        f"Tempo total: {result['total_elapsed']}s"
    )

    # LLM-as-judge
    v1_outputs = {}
    v2_outputs = {}
    for ct, info in result["results"].items():
        if info.get("v1") and info.get("v2"):
            v1_outputs[ct] = info["v1"]["content"]
            v2_outputs[ct] = info["v2"]["content"]

    if v1_outputs and v2_outputs:
        if not os.getenv(JUDGE_API_KEY_ENV):
            console.print(f"\n[dim]LLM-as-judge indispon\u00edvel: {JUDGE_API_KEY_ENV} n\u00e3o configurada.[/dim]")
        elif Confirm.ask("\nDeseja avaliar com LLM-as-judge (DeepSeek V3.2)?", default=False):
            with console.status("\u23f3 Avaliando com LLM-as-judge..."):
                try:
                    evaluator = ContentEvaluator()
                    eval_result = evaluator.evaluate_versions(
                        v1_outputs, v2_outputs, profile, topic
                    )
                except Exception as e:
                    console.print(f"[red]\u26a0\ufe0f Erro no judge: {e}[/red]")
                    eval_result = None
            if eval_result:
                _display_judge_versions(eval_result)

    # Oferecer exportação
    if Confirm.ask("\nDeseja exportar os resultados?", default=False):
        _export_comparison(result)


def _display_judge_versions(eval_result: dict):
    """Exibe resultados do LLM-as-judge para comparação v1 vs v2."""
    criteria_labels = {
        "adequacao_nivel": "Adequa\u00e7\u00e3o N\u00edvel",
        "clareza": "Clareza",
        "adequacao_estilo": "Adequa\u00e7\u00e3o Estilo",
        "engajamento": "Engajamento",
    }

    console.print()
    console.print(Panel(
        f"[bold]Avaliado por:[/bold] {eval_result.get('evaluator_model', 'DeepSeek V3.2')}",
        title="\u2696\ufe0f Avalia\u00e7\u00e3o LLM-as-Judge",
        border_style="magenta",
    ))

    for ct, ev in eval_result["evaluations"].items():
        if ev.get("error"):
            console.print(f"\n[red]\u26a0\ufe0f {ev['label']}: {ev['error']}[/red]")
            continue

        table = Table(title=ev["label"], show_header=True, header_style="bold")
        table.add_column("Crit\u00e9rio", style="dim")
        table.add_column("v1 (B\u00e1sico)", justify="center", style="red")
        table.add_column("v2 (Otimizado)", justify="center", style="green")

        for key, label in criteria_labels.items():
            v1_score = ev["v1_scores"].get(key, "-")
            v2_score = ev["v2_scores"].get(key, "-")
            table.add_row(label, str(v1_score), str(v2_score))

        console.print(table)

        winner = ev.get("vencedor", "")
        winner_style = "green" if winner == "v2" else "red"
        console.print(f"  Vencedor: [{winner_style}]{winner.upper()}[/{winner_style}]")
        if ev.get("justificativa"):
            console.print(f"  [dim]{ev['justificativa']}[/dim]")

    # Resumo geral
    winner = eval_result.get("overall_winner", "")
    winner_style = "green" if winner == "v2" else "red"
    console.print(
        f"\n[bold]Resultado Geral:[/bold] "
        f"v1 m\u00e9dia {eval_result['overall_v1_avg']} \u00d7 "
        f"v2 m\u00e9dia {eval_result['overall_v2_avg']} \u2192 "
        f"[{winner_style}]\U0001f3c6 {winner.upper()} VENCEU[/{winner_style}]"
    )


def _display_version_comparison(data: dict):
    """Exibe comparação v1 vs v2 lado a lado."""
    for ct, info in data["results"].items():
        console.print(f"\n{'='*60}")
        console.print(f"[bold]{info['label']}[/bold]", justify="center")
        console.print(f"{'='*60}")

        panels = []

        # v1
        if info.get("v1"):
            v1_source = info["v1"]["source"]
            v1_text = info["v1"]["content"][:2000]  # truncar para display
            indicator = "\u26a1 Cache" if v1_source == "cache" else f"\U0001f310 {info['v1'].get('elapsed', 0)}s"
            panels.append(Panel(
                Markdown(v1_text),
                title=f"v1 (B\u00e1sico) [{indicator}]",
                border_style="red",
                width=60,
            ))
        elif info.get("v1_error"):
            panels.append(Panel(f"[red]Erro: {info['v1_error']}[/red]", title="v1", width=60))

        # v2
        if info.get("v2"):
            v2_source = info["v2"]["source"]
            v2_text = info["v2"]["content"][:2000]
            indicator = "\u26a1 Cache" if v2_source == "cache" else f"\U0001f310 {info['v2'].get('elapsed', 0)}s"
            panels.append(Panel(
                Markdown(v2_text),
                title=f"v2 (Otimizado) [{indicator}]",
                border_style="green",
                width=60,
            ))
        elif info.get("v2_error"):
            panels.append(Panel(f"[red]Erro: {info['v2_error']}[/red]", title="v2", width=60))

        if panels:
            console.print(Columns(panels, equal=True, expand=True))


# ─── Opção 5: Comparar Modelos ─────────────────────────

def cmd_compare_models():
    """Modo de comparação multi-modelo (1 modelo por provedor)."""
    console.print(Panel("\U0001f4ca Compara\u00e7\u00e3o entre Modelos", border_style="magenta"))

    profile = select_profile()
    if not profile:
        return

    topic = Prompt.ask("\U0001f4d6 [bold cyan]Qual o t\u00f3pico?[/bold cyan]")
    if not topic.strip():
        console.print("[red]T\u00f3pico n\u00e3o pode ser vazio.[/red]")
        return

    available = list_available()
    if not available:
        console.print("[red]Nenhum modelo configurado. Verifique seu .env[/red]")
        return

    # Agrupar modelos disponíveis por provedor
    providers_models: dict[str, list[str]] = {}
    for key in available:
        provider = MODEL_REGISTRY[key]["provider"]
        providers_models.setdefault(provider, []).append(key)

    if len(providers_models) < 2:
        console.print("[red]Configure ao menos 2 provedores para comparar modelos.[/red]")
        return

    # Selecionar 1 modelo por provedor
    selected_keys = []
    provider_display = {"gemini": "Google", "groq": "Groq", "openrouter": "OpenRouter"}

    for provider, keys in providers_models.items():
        display_name = provider_display.get(provider, provider)

        if len(keys) == 1:
            label = MODEL_REGISTRY[keys[0]]["label"]
            selected_keys.append(keys[0])
            console.print(f"  [dim]{display_name}:[/dim] {label} [dim](auto)[/dim]")
            continue

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("#", style="bold cyan", width=3, justify="right")
        table.add_column("Modelo")
        mapping = {}
        for i, key in enumerate(keys):
            table.add_row(str(i + 1), MODEL_REGISTRY[key]["label"])
            mapping[str(i + 1)] = key
        console.print(Panel(table, title=f"{display_name}", border_style="dim"))

        while True:
            choice = Prompt.ask(f"[bold cyan]{display_name}[/bold cyan]")
            if choice in mapping:
                selected_keys.append(mapping[choice])
                break
            console.print("[red]Op\u00e7\u00e3o inv\u00e1lida.[/red]")

    cache = get_cache()
    cache.reset_stats()

    total = len(CONTENT_TYPES) * len(selected_keys)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"\u23f3 Gerando {total} conte\u00fados (4 tipos \u00d7 {len(selected_keys)} modelos, v2)...",
            total=total,
        )

        def on_progress(completed, total_tasks, desc):
            progress.update(task, completed=completed, description=f"\u23f3 {desc}")

        try:
            result = compare_models(
                selected_keys, profile, topic, get_engine(), cache, get_db(),
                progress_callback=on_progress,
            )
        except (LLMError, ValueError) as e:
            console.print(f"[red]\u26a0\ufe0f {e}[/red]")
            return

    # Exibir resultados
    _display_model_comparison(result)

    stats = result["cache_stats"]
    console.print(
        f"\n\U0001f4ca Cache: {stats['hits']} hits / {stats['misses']} misses "
        f"({stats['hit_rate']}% economia) | Tempo total: {result['total_elapsed']}s"
    )

    # LLM-as-judge
    api_outputs = {}
    for ct, info in result["results"].items():
        api_outputs[ct] = {}
        for model_key, mdata in info["models"].items():
            if mdata.get("result"):
                api_outputs[ct][model_key] = mdata["result"]["content"]

    if any(len(v) >= 2 for v in api_outputs.values()):
        if not os.getenv(JUDGE_API_KEY_ENV):
            console.print(f"\n[dim]LLM-as-judge indispon\u00edvel: {JUDGE_API_KEY_ENV} n\u00e3o configurada.[/dim]")
        elif Confirm.ask("\nDeseja avaliar com LLM-as-judge (DeepSeek V3.2)?", default=False):
            with console.status("\u23f3 Avaliando com LLM-as-judge..."):
                try:
                    evaluator = ContentEvaluator()
                    eval_result = evaluator.evaluate_apis(api_outputs, profile, topic)
                except Exception as e:
                    console.print(f"[red]\u26a0\ufe0f Erro no judge: {e}[/red]")
                    eval_result = None
            if eval_result:
                _display_judge_apis(eval_result)

    if Confirm.ask("\nDeseja exportar os resultados?", default=False):
        _export_comparison(result)


def _display_judge_apis(eval_result: dict):
    """Exibe resultados do LLM-as-judge para comparação multi-modelo."""
    criteria_labels = {
        "adequacao_nivel": "Adequa\u00e7\u00e3o N\u00edvel",
        "clareza": "Clareza",
        "adequacao_estilo": "Adequa\u00e7\u00e3o Estilo",
        "engajamento": "Engajamento",
    }

    console.print()
    console.print(Panel(
        f"[bold]Avaliado por:[/bold] {eval_result.get('evaluator_model', 'DeepSeek V3.2')}",
        title="\u2696\ufe0f Avalia\u00e7\u00e3o LLM-as-Judge \u2014 Multi-Modelo",
        border_style="magenta",
    ))

    for ct, ev in eval_result["evaluations"].items():
        if ev.get("error"):
            console.print(f"\n[red]\u26a0\ufe0f {ev['label']}: {ev['error']}[/red]")
            continue

        scores = ev.get("scores", {})
        model_keys = list(scores.keys())

        table = Table(title=ev["label"], show_header=True, header_style="bold")
        table.add_column("Crit\u00e9rio", style="dim")
        for mk in model_keys:
            label = MODEL_REGISTRY.get(mk, {}).get("label", mk)
            table.add_column(label, justify="center")

        for key, label in criteria_labels.items():
            row = [label]
            for mk in model_keys:
                row.append(str(scores[mk].get(key, "-")))
            table.add_row(*row)

        console.print(table)

        vencedor_mk = ev.get("vencedor", "")
        vencedor_label = MODEL_REGISTRY.get(vencedor_mk, {}).get("label", vencedor_mk)
        console.print(f"  Vencedor: [green]{vencedor_label}[/green]")
        if ev.get("justificativa"):
            console.print(f"  [dim]{ev['justificativa']}[/dim]")

    # Resumo geral
    overall = eval_result.get("overall_winner", "")
    overall_label = MODEL_REGISTRY.get(overall, {}).get("label", overall)
    averages = eval_result.get("model_averages", {})
    avg_text = " | ".join(
        f"{MODEL_REGISTRY.get(mk, {}).get('label', mk)}: {v}"
        for mk, v in averages.items()
    )
    console.print(f"\n[bold]Resultado Geral:[/bold] {avg_text}")
    console.print(f"[green bold]\U0001f3c6 VENCEDOR GERAL: {overall_label}[/green bold]")


def _display_model_comparison(data: dict):
    """Exibe comparação multi-modelo."""
    for ct, info in data["results"].items():
        console.print(f"\n{'='*60}")
        console.print(f"[bold]{info['label']}[/bold]", justify="center")
        console.print(f"{'='*60}")

        panels = []
        for model_key, mdata in info["models"].items():
            label = mdata["label"]
            if mdata.get("result"):
                source = mdata["result"]["source"]
                text = mdata["result"]["content"][:1500]
                indicator = "\u26a1 Cache" if source == "cache" else f"\U0001f310 {mdata['result'].get('elapsed', 0)}s"
                panels.append(Panel(
                    Markdown(text),
                    title=f"{label} [{indicator}]",
                    border_style="blue",
                    width=40,
                ))
            elif mdata.get("error"):
                panels.append(Panel(
                    f"[red]\u26a0\ufe0f {mdata['error']}[/red]",
                    title=label,
                    border_style="red",
                    width=40,
                ))

        if panels:
            console.print(Columns(panels, equal=True, expand=True))


# ─── Opção 6: Histórico ─────────────────────────────────

def cmd_history():
    """Exibe histórico de sessões."""
    console.print(Panel("\U0001f4dc Hist\u00f3rico de Sess\u00f5es", border_style="cyan"))

    db = get_db()
    sessions = db.list_sessions()

    if not sessions:
        console.print("[yellow]Nenhuma sess\u00e3o registrada.[/yellow]")
        return

    table = Table()
    table.add_column("#", style="dim", width=4)
    table.add_column("Data")
    table.add_column("Perfil")
    table.add_column("T\u00f3pico")
    table.add_column("Modelo")
    table.add_column("Modo")

    mode_labels = {
        "conversation": "Conversa",
        "compare_versions": "v1 vs v2",
        "compare_models": "Multi-Modelo",
        "compare_apis": "Multi-Modelo",
    }

    for i, s in enumerate(sessions):
        table.add_row(
            str(i + 1),
            s.get("started_at", "")[:16],
            s.get("profile_name", s["profile_id"][:12]),
            (s.get("topic", "")[:20] + "...") if len(s.get("topic", "")) > 20 else s.get("topic", ""),
            s["provider"],
            mode_labels.get(s["mode"], s["mode"]),
        )

    console.print(table)

    choice = Prompt.ask("\nSelecione uma sess\u00e3o para ver detalhes (ou Enter para voltar)", default="")
    if not choice.strip():
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            _show_session_detail(sessions[idx]["id"])
        else:
            console.print("[red]N\u00famero inv\u00e1lido.[/red]")
    except ValueError:
        console.print("[red]Entrada inv\u00e1lida.[/red]")


def _show_session_detail(session_id: str):
    """Exibe detalhes de uma sessão."""
    db = get_db()
    messages = db.get_messages(session_id)

    if not messages:
        console.print("[yellow]Sess\u00e3o sem mensagens.[/yellow]")
        return

    for msg in messages:
        ct = msg.get("content_type", "free_chat")
        role_style = "bold cyan" if msg["role"] == "user" else "bold green"
        role_label = "Aluno" if msg["role"] == "user" else "Professor"

        version_tag = f" (v{msg['prompt_version']})" if msg.get("prompt_version") else ""
        source_tag = f" [{msg['source']}]" if msg.get("source") else ""

        console.print(f"\n[{role_style}]{role_label}[/{role_style}]{version_tag}{source_tag} [{ct}]:")
        console.print(Markdown(msg["content"][:1000]))

    Prompt.ask("\n[dim]Enter para voltar[/dim]", default="")


# ─── Opção 7: Exportar ──────────────────────────────────

def cmd_export():
    """Menu de exportação."""
    console.print(Panel("\U0001f4c1 Exportar Resultados", border_style="green"))

    console.print("  [1] Exportar sess\u00e3o espec\u00edfica")
    console.print("  [2] Exportar todas as sess\u00f5es")

    choice = Prompt.ask("Escolha", default="1")

    # Formato
    console.print("\nFormato: [1] JSON  [2] Markdown  [3] Ambos")
    fmt = Prompt.ask("Formato", default="3")

    db = get_db()

    if choice == "1":
        sessions = db.list_sessions()
        if not sessions:
            console.print("[yellow]Nenhuma sess\u00e3o registrada.[/yellow]")
            return

        # Mostra lista e pede seleção
        for i, s in enumerate(sessions):
            console.print(f"  [{i+1}] {s.get('topic', 'Sem tópico')} ({s['mode']}, {s.get('started_at', '')[:16]})")

        idx_str = Prompt.ask("Selecione", default="1")
        try:
            idx = int(idx_str) - 1
            if idx < 0 or idx >= len(sessions):
                console.print("[red]Inválido.[/red]")
                return
        except ValueError:
            console.print("[red]Inválido.[/red]")
            return

        sid = sessions[idx]["id"]
        _export_session(sid, fmt, db)

    elif choice == "2":
        sessions = db.list_sessions()
        for s in sessions:
            _export_session(s["id"], fmt, db)


def _export_session(session_id: str, fmt: str, db: Database):
    """Exporta uma sessão nos formatos selecionados."""
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = session_id[:8]

    try:
        if fmt in ("1", "3"):
            content = export_session_json(session_id, db)
            path = save_export(content, f"session_{short_id}_{ts}.json")
            console.print(f"[green]\u2705 Exportado: {path}[/green]")

        if fmt in ("2", "3"):
            content = export_session_markdown(session_id, db)
            path = save_export(content, f"session_{short_id}_{ts}.md")
            console.print(f"[green]\u2705 Exportado: {path}[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


def _export_comparison(data: dict):
    """Exporta resultado de comparação."""
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "versions" if "provider" in data else "models"

    json_content = export_comparison_json(data)
    path = save_export(json_content, f"comparison_{mode}_{ts}.json")
    console.print(f"[green]\u2705 Exportado: {path}[/green]")

    md_content = export_comparison_markdown(data)
    path = save_export(md_content, f"comparison_{mode}_{ts}.md")
    console.print(f"[green]\u2705 Exportado: {path}[/green]")


# ─── Menu Principal ──────────────────────────────────────

def main_menu():
    """Loop do menu principal."""
    while True:
        console.print()
        show_header()

        menu = Table(show_header=False, box=None, padding=(0, 1))
        menu.add_column("N", style="bold cyan", width=3, justify="right")
        menu.add_column("Op\u00e7\u00e3o")
        menu.add_row("1", "\U0001f4cb  Listar perfis de alunos")
        menu.add_row("2", "\u2795  Criar novo perfil")
        menu.add_row("3", "\U0001f4ac  Iniciar sess\u00e3o de aprendizado")
        menu.add_row("4", "\U0001f504  Comparar vers\u00f5es de prompt (v1 vs v2)")
        menu.add_row("5", "\U0001f4ca  Comparar Modelos")
        menu.add_row("6", "\U0001f4dc  Ver hist\u00f3rico de sess\u00f5es")
        menu.add_row("7", "\U0001f4c1  Exportar resultados (JSON / Markdown)")
        menu.add_row("8", "\U0001f6aa  Sair")
        console.print(menu)
        console.print()

        try:
            choice = Prompt.ask("[bold cyan]Escolha uma op\u00e7\u00e3o[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            choice = "8"

        if choice == "1":
            cmd_list_profiles()
        elif choice == "2":
            cmd_create_profile()
        elif choice == "3":
            cmd_session()
        elif choice == "4":
            cmd_compare_versions()
        elif choice == "5":
            cmd_compare_models()
        elif choice == "6":
            cmd_history()
        elif choice == "7":
            cmd_export()
        elif choice == "8":
            _show_exit_stats()
            break
        else:
            console.print("[red]Op\u00e7\u00e3o inv\u00e1lida.[/red]")


def _show_exit_stats():
    """Exibe estatísticas ao sair."""
    console.print("\n[bold]Obrigado por usar o EduPrompt![/bold] \U0001f44b")

    cache = get_cache()
    stats = cache.get_stats()
    if stats["total"] > 0:
        console.print(
            f"\n\U0001f4ca Estat\u00edsticas da sess\u00e3o:\n"
            f"  Cache: {stats['hits']} hits / {stats['misses']} misses "
            f"({stats['hit_rate']}% economia)"
        )


@app.command()
def run():
    """Inicia a plataforma EduPrompt."""
    main_menu()


if __name__ == "__main__":
    app()
