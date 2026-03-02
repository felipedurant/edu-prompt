"""Cadastro de aluno + quiz VARK para identificar estilo de aprendizado."""

from collections import Counter

LEARNING_STYLES = {
    "visual": {
        "nome": "Visual",
        "emoji": "\U0001f441\ufe0f",
        "descricao": "Voc\u00ea aprende melhor com imagens, diagramas, gr\u00e1ficos e mapas mentais.",
    },
    "auditivo": {
        "nome": "Auditivo",
        "emoji": "\U0001f442",
        "descricao": "Voc\u00ea aprende melhor ouvindo explica\u00e7\u00f5es e participando de discuss\u00f5es.",
    },
    "leitura-escrita": {
        "nome": "Leitura/Escrita",
        "emoji": "\U0001f4d6",
        "descricao": "Voc\u00ea aprende melhor lendo textos, fazendo anota\u00e7\u00f5es e escrevendo resumos.",
    },
    "cinestesico": {
        "nome": "Cinest\u00e9sico",
        "emoji": "\U0001f932",
        "descricao": "Voc\u00ea aprende melhor fazendo \u2014 atividades pr\u00e1ticas e exerc\u00edcios hands-on.",
    },
}

VARK_QUIZ = [
    {
        "pergunta": "Quando precisa aprender a usar um novo aplicativo, voc\u00ea prefere:",
        "opcoes": {
            "visual": "Assistir um tutorial em v\u00eddeo com demonstra\u00e7\u00f5es",
            "auditivo": "Ouvir algu\u00e9m explicar como funciona",
            "leitura-escrita": "Ler o manual ou um guia passo a passo",
            "cinestesico": "Abrir o app e ir explorando na pr\u00e1tica",
        },
    },
    {
        "pergunta": "Em uma aula sobre um tema novo, o que mais te ajuda a entender?",
        "opcoes": {
            "visual": "Slides com gr\u00e1ficos, diagramas e esquemas",
            "auditivo": "A explica\u00e7\u00e3o falada do professor",
            "leitura-escrita": "Anota\u00e7\u00f5es detalhadas e textos complementares",
            "cinestesico": "Atividades em grupo ou exerc\u00edcios pr\u00e1ticos",
        },
    },
    {
        "pergunta": "Para estudar para uma prova, sua estrat\u00e9gia favorita \u00e9:",
        "opcoes": {
            "visual": "Fazer mapas mentais e esquemas coloridos",
            "auditivo": "Gravar resumos em \u00e1udio e ouvir depois",
            "leitura-escrita": "Reescrever a mat\u00e9ria com suas palavras",
            "cinestesico": "Resolver exerc\u00edcios e problemas pr\u00e1ticos",
        },
    },
    {
        "pergunta": "Quando algu\u00e9m te explica um caminho, voc\u00ea prefere:",
        "opcoes": {
            "visual": "Ver um mapa ou desenho do trajeto",
            "auditivo": "Ouvir as instru\u00e7\u00f5es passo a passo",
            "leitura-escrita": "Receber as instru\u00e7\u00f5es escritas",
            "cinestesico": "Ir andando e descobrir pelo caminho",
        },
    },
    {
        "pergunta": "Ao montar um m\u00f3vel novo, voc\u00ea:",
        "opcoes": {
            "visual": "Olha as figuras e diagramas do manual",
            "auditivo": "Pede para algu\u00e9m te guiar falando",
            "leitura-escrita": "L\u00ea todas as instru\u00e7\u00f5es antes de come\u00e7ar",
            "cinestesico": "Come\u00e7a montando e consulta o manual s\u00f3 se travar",
        },
    },
    {
        "pergunta": "Para lembrar de uma informa\u00e7\u00e3o importante, voc\u00ea:",
        "opcoes": {
            "visual": "Visualiza mentalmente onde leu ou viu aquilo",
            "auditivo": "Repete a informa\u00e7\u00e3o em voz alta",
            "leitura-escrita": "Anota em um caderno ou post-it",
            "cinestesico": "Associa a informa\u00e7\u00e3o a um gesto ou movimento",
        },
    },
    {
        "pergunta": "Se pudesse escolher como aprender um idioma novo, escolheria:",
        "opcoes": {
            "visual": "Flashcards com imagens e legendas",
            "auditivo": "Podcasts e m\u00fasicas no idioma",
            "leitura-escrita": "Livros de gram\u00e1tica e exerc\u00edcios escritos",
            "cinestesico": "Conversar com nativos e praticar em situa\u00e7\u00f5es reais",
        },
    },
]


def calculate_style(answers: list[str]) -> dict:
    """
    Calcula o estilo de aprendizado com base nas respostas do quiz.

    Args:
        answers: Lista de estilos escolhidos (ex: ['visual', 'auditivo', ...]).

    Returns:
        Dict com 'style' (str), 'scores' (dict), 'tied' (bool),
        'tied_styles' (list[str] se empate).
    """
    counts = Counter(answers)
    max_count = max(counts.values())
    winners = [style for style, count in counts.items() if count == max_count]

    return {
        "style": winners[0],
        "scores": dict(counts),
        "tied": len(winners) > 1,
        "tied_styles": winners if len(winners) > 1 else [],
    }


def get_quiz_questions() -> list[dict]:
    """Retorna as perguntas do quiz VARK formatadas para exibição."""
    questions = []
    for i, q in enumerate(VARK_QUIZ):
        options = []
        for style_key, text in q["opcoes"].items():
            style_info = LEARNING_STYLES[style_key]
            options.append({
                "key": style_key,
                "text": text,
                "emoji": style_info["emoji"],
            })
        questions.append({
            "number": i + 1,
            "question": q["pergunta"],
            "options": options,
        })
    return questions


def get_style_display(style_key: str) -> str:
    """Retorna display formatado do estilo (emoji + nome)."""
    info = LEARNING_STYLES.get(style_key, {})
    return f"{info.get('emoji', '')} {info.get('nome', style_key)}"
