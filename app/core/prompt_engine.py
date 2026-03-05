"""
Motor de engenharia de prompt — CORAÇÃO DO PROJETO (40% da nota).

Técnicas obrigatórias aplicadas em TODOS os prompts:
- Persona Prompting: system prompt com papel de professor especializado
- Context Setting: dados do aluno injetados no prompt
- Chain-of-Thought: raciocínio passo a passo
- Output Formatting: formato de saída especificado por tipo

Duas versões:
- v1 (literal/simples): técnicas aplicadas de forma direta e mínima
- v2 (otimizado/avançado): engenharia de prompt moderna e refinada
"""

import re
import logging

from app.config import DEFAULT_PROMPT_VERSION

logger = logging.getLogger(__name__)


class PromptEngine:
    """Motor de engenharia de prompt com suporte a 4 tipos x 2 versões x 4 estilos."""

    # ─── Adaptações por estilo de aprendizado ────────────

    STYLE_ADAPTATIONS_V1 = {
        "visual": "Use exemplos visuais quando possível.",
        "auditivo": "Use linguagem conversacional.",
        "leitura-escrita": "Use texto estruturado.",
        "cinestesico": "Inclua atividades práticas.",
    }

    STYLE_ADAPTATIONS_V2 = {
        "visual": (
            "Priorize diagramas ASCII, esquemas visuais, analogias com imagens mentais, "
            "e use emojis como ícones para organizar informação. Estruture com bullet points "
            "visuais e hierarquia clara. Quando possível, crie representações visuais "
            "(tabelas, fluxogramas ASCII, mapas mentais)."
        ),
        "auditivo": (
            "Use linguagem conversacional como se estivesse explicando em voz alta. "
            "Inclua ritmo de explicação falada com pausas naturais ('Perceba que...', "
            "'Agora, preste atenção nisto:'). Use repetição estratégica de conceitos-chave "
            "e reformulações ('Em outras palavras...', 'Dizendo de outro modo...'). "
            "Simule um diálogo pedagógico."
        ),
        "leitura-escrita": (
            "Estruture com seções numeradas, definições formais em destaque, "
            "e referências cruzadas ('Como vimos na seção anterior...'). "
            "Use vocabulário técnico com definições claras. Inclua um glossário "
            "de termos-chave. Formate como um texto acadêmico acessível."
        ),
        "cinestesico": (
            "Proponha atividades práticas e exercícios hands-on em cada etapa. "
            "Use simulações mentais ('Imagine que você está...', 'Agora tente...'). "
            "Conecte cada conceito a uma ação concreta. Inclua desafios progressivos "
            "e experimentos que o aluno pode fazer. Use analogias com atividades físicas."
        ),
    }

    # ─── Persona por faixa etária (v2) ──────────────────

    @staticmethod
    def _get_persona_v2(profile: dict) -> str:
        age = profile["idade"]
        style_name = profile["estilo"]

        if age <= 12:
            tone = (
                "Use linguagem simples, divertida e acolhedora. "
                "Explique como se fosse um professor particular paciente e animado. "
                "Use analogias do dia a dia de uma criança (brincadeiras, escola, desenhos)."
            )
        elif age <= 17:
            tone = (
                "Use linguagem acessível mas respeitosa — sem infantilizar. "
                "Conecte os conceitos ao mundo do adolescente (tecnologia, redes sociais, vestibular). "
                "Seja um mentor que inspira curiosidade."
            )
        elif age <= 25:
            tone = (
                "Use linguagem direta e moderna. Pode usar termos técnicos com explicações breves. "
                "Conecte com aplicações profissionais e acadêmicas. "
                "Seja um tutor universitário acessível."
            )
        else:
            tone = (
                "Use linguagem profissional e respeitosa. "
                "Valorize a experiência prévia do aluno e conecte novos conceitos "
                "com conhecimentos que um adulto provavelmente já tem. "
                "Seja um facilitador de aprendizado objetivo e prático."
            )

        return (
            f"Você é um professor especializado em educação personalizada, "
            f"com expertise em pedagogia adaptativa e ensino para o estilo {style_name}. "
            f"{tone} "
            f"Seu objetivo é garantir compreensão profunda, não apenas transmissão de informação. "
            f"Responda sempre em Português do Brasil."
        )

    # ─── Contexto do aluno ───────────────────────────────

    @staticmethod
    def _build_context_v1(profile: dict, topic: str) -> str:
        return (
            f"O aluno se chama {profile['nome']}, tem {profile['idade']} anos, "
            f"está no nível {profile['nivel']} e tem estilo de aprendizado {profile['estilo']}. "
            f"O tópico de estudo é: {topic}."
        )

    @staticmethod
    def _build_context_v2(profile: dict, topic: str) -> str:
        context_extra = f" Contexto adicional: {profile['contexto']}." if profile.get("contexto") else ""
        level_desc = {
            "iniciante": "está começando a aprender sobre o assunto, precisa de explicações fundamentais e não tem pré-requisitos",
            "intermediario": "já tem noções básicas e precisa aprofundar, conectar conceitos e ver aplicações",
            "avancado": "tem boa base e busca profundidade, nuances, casos especiais e conexões interdisciplinares",
        }
        return (
            f"PERFIL DO ALUNO:\n"
            f"- Nome: {profile['nome']}\n"
            f"- Idade: {profile['idade']} anos\n"
            f"- Nível: {profile['nivel']} — {level_desc.get(profile['nivel'], '')}\n"
            f"- Estilo de aprendizado: {profile['estilo']}\n"
            f"- Tópico: {topic}\n"
            f"{context_extra}\n\n"
            f"Adapte TODO o conteúdo para este perfil específico. "
            f"Use exemplos do cotidiano adequados à idade e contexto do aluno."
        )

    # ─── Sanitização ─────────────────────────────────────

    @staticmethod
    def sanitize_topic(topic: str) -> str:
        """
        Sanitiza tópico antes de injetar no prompt.
        Remove caracteres de controle, limita tamanho, escapa padrões
        que poderiam ser interpretados como instruções pela LLM.
        """
        topic = topic.strip()
        topic = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', topic)
        if len(topic) > 500:
            logger.warning("Tópico truncado de %d para 500 caracteres", len(topic))
            topic = topic[:500]
        return topic

    # ─── Builders: Explicação Conceitual ─────────────────

    def build_conceptual_explanation(self, profile: dict, topic: str,
                                     version: str = DEFAULT_PROMPT_VERSION) -> tuple[str, str]:
        """Chain-of-thought para explicação conceitual."""
        topic = self.sanitize_topic(topic)

        if version == "v1":
            system = (
                "Você é um professor experiente em Pedagogia. Responda sempre em Português do Brasil. "
                + self.STYLE_ADAPTATIONS_V1.get(profile["estilo"], "")
            )
            user = (
                f"{self._build_context_v1(profile, topic)}\n\n"
                f"Pense passo a passo e explique o conceito de '{topic}' "
                f"de forma clara e adequada ao nível do aluno. "
                f"Organize a resposta em parágrafos."
            )
        else:
            system = (
                f"{self._get_persona_v2(profile)}\n\n"
                f"ESTILO DE ENSINO:\n{self.STYLE_ADAPTATIONS_V2.get(profile['estilo'], '')}"
            )
            user = (
                f"{self._build_context_v2(profile, topic)}\n\n"
                f"TAREFA: Crie uma explicação conceitual sobre '{topic}'.\n\n"
                f"ABORDAGEM (Chain-of-Thought com scaffolding):\n"
                f"1. Comece com uma pergunta ou situação concreta do cotidiano que conecte o aluno ao tema\n"
                f"   → Use algo que alguém de {profile['idade']} anos vivencia de verdade\n"
                f"2. Apresente o conceito fundamental de forma acessível, conectando com o que o aluno já sabe\n"
                f"3. Desenvolva passo a passo, construindo cada ideia sobre a anterior — use analogias concretas\n"
                f"   (compare com objetos, situações ou processos que o aluno conhece, nunca use analogias abstratas)\n"
                f"4. Inclua um checkpoint de compreensão: 'Até aqui, ficou claro que [resumo do que foi explicado]?'\n"
                f"5. Aprofunde com conexões entre o tópico e outros assuntos que o aluno estuda ou conhece\n"
                f"6. Finalize com:\n"
                f"   - Um resumo-síntese de 2-3 frases\n"
                f"   - Uma reflexão meta-cognitiva: 'O conceito-chave para lembrar é...'\n"
                f"   - Uma pergunta motivadora para despertar curiosidade sobre o próximo passo\n\n"
                f"FORMATO (use Markdown):\n"
                f"- Use títulos ## para cada seção da explicação\n"
                f"- Use **negrito** para termos-chave e conceitos centrais\n"
                f"- Use listas e bullet points para organizar informação\n"
                f"- Inclua analogias concretas e vívidas adequadas à idade ({profile['idade']} anos)\n"
                f"- Extensão: proporcional ao nível ({profile['nivel']})\n"
                f"- Se aplicável, inclua uma curiosidade ou fato interessante relacionado ao tema"
            )

        return system, user

    # ─── Builders: Exemplos Práticos ─────────────────────

    def build_practical_examples(self, profile: dict, topic: str,
                                  version: str = DEFAULT_PROMPT_VERSION) -> tuple[str, str]:
        """Exemplos contextualizados para idade/nível."""
        topic = self.sanitize_topic(topic)

        if version == "v1":
            system = (
                "Você é um professor experiente em Pedagogia. Responda sempre em Português do Brasil. "
                + self.STYLE_ADAPTATIONS_V1.get(profile["estilo"], "")
            )
            user = (
                f"{self._build_context_v1(profile, topic)}\n\n"
                f"Dê exemplos práticos sobre '{topic}' adequados ao nível do aluno. "
                f"Organize a resposta de forma clara."
            )
        else:
            system = (
                f"{self._get_persona_v2(profile)}\n\n"
                f"ESTILO DE ENSINO:\n{self.STYLE_ADAPTATIONS_V2.get(profile['estilo'], '')}"
            )
            user = (
                f"{self._build_context_v2(profile, topic)}\n\n"
                f"TAREFA: Crie exemplos práticos contextualizados sobre '{topic}'.\n\n"
                f"DIRETRIZES:\n"
                f"1. Crie 3-5 exemplos progressivos (do mais simples ao mais complexo)\n"
                f"2. Cada exemplo deve:\n"
                f"   - Partir de uma situação real e específica do cotidiano de alguém de {profile['idade']} anos\n"
                f"   - Mostrar o conceito em ação passo a passo, com raciocínio explícito\n"
                f"   - Incluir uma variação: 'E se mudássemos [variável]? O que aconteceria?'\n"
                f"   - Terminar com 'Por que isso importa:' explicando a relevância prática\n"
                f"3. Use transições narrativas entre exemplos ('Agora que entendemos X, vamos ver como isso se aplica a...')\n"
                f"4. Finalize com um desafio prático que o aluno pode tentar sozinho, incluindo:\n"
                f"   - Enunciado claro\n"
                f"   - Dica de como começar\n"
                f"   - Critério de sucesso ('Você acertou se...')\n\n"
                f"FORMATO (use Markdown):\n"
                f"- Use ## para títulos de cada exemplo (ex: '## Exemplo 1: [Título Descritivo]')\n"
                f"- Use **negrito** para o conceito aplicado em cada exemplo\n"
                f"- Use blocos de código se envolver cálculos, fórmulas ou processos sequenciais\n"
                f"- Se útil, inclua uma tabela comparativa entre exemplos\n"
                f"- Adeque complexidade ao nível {profile['nivel']}"
            )

        return system, user

    # ─── Builders: Perguntas de Reflexão ─────────────────

    def build_reflection_questions(self, profile: dict, topic: str,
                                    version: str = DEFAULT_PROMPT_VERSION) -> tuple[str, str]:
        """Perguntas que estimulam pensamento crítico."""
        topic = self.sanitize_topic(topic)

        if version == "v1":
            system = (
                "Você é um professor experiente em Pedagogia. Responda sempre em Português do Brasil. "
                + self.STYLE_ADAPTATIONS_V1.get(profile["estilo"], "")
            )
            user = (
                f"{self._build_context_v1(profile, topic)}\n\n"
                f"Crie perguntas de reflexão sobre '{topic}' "
                f"que estimulem o pensamento crítico do aluno. "
                f"As perguntas devem ser adequadas ao nível do aluno."
            )
        else:
            system = (
                f"{self._get_persona_v2(profile)}\n\n"
                f"ESTILO DE ENSINO:\n{self.STYLE_ADAPTATIONS_V2.get(profile['estilo'], '')}"
            )
            user = (
                f"{self._build_context_v2(profile, topic)}\n\n"
                f"TAREFA: Crie perguntas de reflexão e pensamento crítico sobre '{topic}'.\n\n"
                f"ESTRUTURA (Taxonomia de Bloom adaptada ao nível {profile['nivel']}):\n"
                f"1. COMPREENSÃO (1-2 perguntas):\n"
                f"   - Verificar se o aluno entendeu o conceito central\n"
                f"   - Formato: 'Com suas próprias palavras, explique [conceito]'\n"
                f"   - Apresente um cenário concreto antes de perguntar\n"
                f"2. APLICAÇÃO (1-2 perguntas):\n"
                f"   - Testar se o aluno consegue usar o conhecimento em situações novas\n"
                f"   - Formato: 'Imagine que [situação]. Como você usaria [conceito] para...'\n"
                f"   - Use situações realistas do dia a dia de alguém de {profile['idade']} anos\n"
                f"3. ANÁLISE (1-2 perguntas):\n"
                f"   - Exigir decomposição, comparação ou identificação de causa-efeito\n"
                f"   - Formato: 'Compare [A] e [B]. Quais são as diferenças fundamentais e por quê?'\n"
                f"   - Peça que o aluno justifique seu raciocínio\n"
                f"4. SÍNTESE/CRIAÇÃO (1 pergunta):\n"
                f"   - Pergunta aberta e desafiadora que exige pensamento original\n"
                f"   - Formato: 'Se você pudesse redesenhar/reinventar [X], como faria e por quê?'\n"
                f"   - Conecte com um problema real ou atual\n\n"
                f"DIRETRIZES:\n"
                f"- Cada pergunta deve começar com um breve cenário ou provocação antes da pergunta em si\n"
                f"- Inclua uma dica de abordagem após cada pergunta (sem dar a resposta)\n"
                f"- As perguntas devem ter progressão lógica — cada uma construindo sobre a anterior\n"
                f"- Pelo menos uma pergunta deve conectar '{topic}' ao mundo real do aluno\n\n"
                f"FORMATO (use Markdown):\n"
                f"- Use ## para cada nível da taxonomia\n"
                f"- Use > (blockquote) para destacar os cenários/provocações\n"
                f"- Use *itálico* para as dicas de abordagem\n"
                f"- Numere as perguntas sequencialmente dentro de cada nível"
            )

        return system, user

    # ─── Builders: Resumo Visual ─────────────────────────

    def build_visual_summary(self, profile: dict, topic: str,
                              version: str = DEFAULT_PROMPT_VERSION,
                              output_format: str = "ascii") -> tuple[str, str]:
        """Mapa mental/diagrama ASCII ou Mermaid, conforme output_format."""
        topic = self.sanitize_topic(topic)

        if version == "v1":
            system = (
                "Você é um professor experiente em Pedagogia. Responda sempre em Português do Brasil. "
                + self.STYLE_ADAPTATIONS_V1.get(profile["estilo"], "")
            )
            user = (
                f"{self._build_context_v1(profile, topic)}\n\n"
                f"Crie um resumo visual sobre '{topic}'. "
                f"Use diagrama ASCII ou mapa mental em texto. "
                f"Adeque ao nível do aluno."
            )
        else:
            system = (
                f"{self._get_persona_v2(profile)}\n\n"
                f"ESTILO DE ENSINO:\n{self.STYLE_ADAPTATIONS_V2.get(profile['estilo'], '')}"
            )

            if output_format == "mermaid":
                visual_instructions = (
                    f"1. MAPA MENTAL em Mermaid (OBRIGATÓRIO usar bloco ```mermaid):\n"
                    f"   - Use EXCLUSIVAMENTE a sintaxe mindmap do Mermaid.js\n"
                    f"   - O bloco deve começar com ```mermaid e terminar com ```\n"
                    f"   - Use indentação com espaços (não tabs) para definir hierarquia\n"
                    f"   - Exemplo EXATO de sintaxe válida:\n"
                    f"     ```mermaid\n"
                    f"     mindmap\n"
                    f"       root((Tema Central))\n"
                    f"         Conceito A\n"
                    f"           Sub-conceito 1\n"
                    f"           Sub-conceito 2\n"
                    f"         Conceito B\n"
                    f"           Sub-conceito 3\n"
                    f"     ```\n"
                    f"   - IMPORTANTE: não use caracteres especiais nos nós (sem parênteses, colchetes ou aspas dentro dos nomes)\n"
                    f"   - Use entre 3-6 ramificações principais com 2-3 sub-conceitos cada\n\n"
                    f"2. TABELA-RESUMO em Markdown:\n"
                    f"   | Conceito | Definição Curta | Exemplo do Dia a Dia |\n"
                    f"   |----------|-----------------|---------------------|\n"
                    f"   - 3-5 linhas com os pontos-chave do tópico\n\n"
                )
            else:
                visual_instructions = (
                    f"1. MAPA MENTAL em ASCII/texto:\n"
                    f"   - Conceito central no topo\n"
                    f"   - Ramificações hierárquicas com sub-conceitos\n"
                    f"   - Use └──, ├──, │ para criar a estrutura visual\n"
                    f"   - Use emojis como marcadores visuais (📌 conceito, 🔗 conexão, ⚡ importante)\n"
                    f"   - Exemplo:\n"
                    f"     📌 TEMA CENTRAL\n"
                    f"     ├── Conceito A\n"
                    f"     │   ├── Sub-conceito 1\n"
                    f"     │   └── Sub-conceito 2\n"
                    f"     └── Conceito B\n\n"
                    f"2. TABELA-RESUMO:\n"
                    f"   | Conceito | Definição Curta | Exemplo do Dia a Dia |\n"
                    f"   |----------|-----------------|---------------------|\n"
                    f"   - 3-5 linhas com os pontos-chave\n\n"
                )

            user = (
                f"{self._build_context_v2(profile, topic)}\n\n"
                f"TAREFA: Crie um resumo visual completo sobre '{topic}'.\n\n"
                f"INCLUA TODOS estes elementos:\n"
                f"{visual_instructions}"
                f"3. FÓRMULA/REGRA RÁPIDA (se aplicável):\n"
                f"   - Uma frase-síntese para memorização rápida\n"
                f"   - Mnemônico criativo, se possível\n"
                f"   - Destaque com emoji ⚡ ou 💡\n\n"
                f"4. CONEXÕES:\n"
                f"   - Como '{topic}' se conecta com outros assuntos que o aluno estuda\n"
                f"   - Use → para indicar relações entre tópicos\n\n"
                f"FORMATO:\n"
                f"- Use blocos visuais claros e bem delimitados com títulos ##\n"
                f"- Se usar símbolos ou abreviações, inclua uma legenda\n"
                f"- Adeque para {profile['idade']} anos, nível {profile['nivel']}\n"
                f"- O resumo deve funcionar como 'cola de estudos' — rápido de consultar e fácil de memorizar"
            )

        return system, user

    # ─── Builders: Quiz ──────────────────────────────────

    def build_quiz_question(self, profile: dict, topic: str,
                             conversation_context: str = "") -> tuple[str, str]:
        """Gera pergunta para testar conhecimento do aluno (/quiz_me)."""
        topic = self.sanitize_topic(topic)

        system = (
            f"{self._get_persona_v2(profile)}\n\n"
            f"Você está avaliando o conhecimento do aluno de forma construtiva e encorajadora. "
            f"Responda sempre em Português do Brasil."
        )

        context_hint = ""
        if conversation_context:
            context_hint = (
                f"\nCONTEXTO DA CONVERSA ATUAL:\n{conversation_context}\n"
                f"Baseie a pergunta no que já foi discutido, para testar compreensão real.\n"
            )

        user = (
            f"{self._build_context_v2(profile, topic)}\n"
            f"{context_hint}\n"
            f"TAREFA: Gere UMA pergunta para testar o conhecimento do aluno sobre '{topic}'.\n\n"
            f"DIRETRIZES:\n"
            f"- A pergunta deve ser adequada ao nível {profile['nivel']}\n"
            f"- Deve ser respondível em texto livre (não múltipla escolha)\n"
            f"- Deve avaliar compreensão, não memorização\n"
            f"- Inclua contexto suficiente para a pergunta fazer sentido\n"
            f"- Seja claro e direto\n\n"
            f"FORMATO:\n"
            f"Apresente apenas a pergunta, de forma clara e direta. "
            f"Não inclua a resposta."
        )

        return system, user

    def build_quiz_feedback(self, profile: dict, topic: str,
                             question: str, answer: str) -> tuple[str, str]:
        """Avalia resposta do aluno e dá feedback construtivo."""
        topic = self.sanitize_topic(topic)

        system = (
            f"{self._get_persona_v2(profile)}\n\n"
            f"Você está avaliando a resposta de um aluno de forma construtiva. "
            f"Seja encorajador mesmo quando a resposta estiver incorreta. "
            f"Responda sempre em Português do Brasil."
        )

        user = (
            f"{self._build_context_v2(profile, topic)}\n\n"
            f"PERGUNTA FEITA AO ALUNO:\n{question}\n\n"
            f"RESPOSTA DO ALUNO:\n{answer}\n\n"
            f"TAREFA: Avalie a resposta e dê feedback construtivo.\n\n"
            f"FORMATO OBRIGATÓRIO:\n"
            f"1. Comece com um dos indicadores:\n"
            f"   - ✅ Correto! (se acertou)\n"
            f"   - 🟡 Parcialmente correto! (se acertou parte)\n"
            f"   - ❌ Não exatamente... (se errou)\n"
            f"2. Explique o que estava certo na resposta (se algo)\n"
            f"3. Complemente com a explicação correta\n"
            f"4. Dê uma dica para lembrar o conceito\n"
            f"5. Encoraje o aluno a continuar estudando"
        )

        return system, user

    # ─── Builder genérico ────────────────────────────────

    def build_prompt(self, profile: dict, topic: str, content_type: str,
                     version: str = DEFAULT_PROMPT_VERSION,
                     output_format: str = "ascii") -> tuple[str, str]:
        """
        Builder genérico que despacha para o builder correto.

        Args:
            content_type: 'conceptual', 'practical', 'reflection', 'visual'
            output_format: 'ascii' (CLI) ou 'mermaid' (web) — afeta apenas 'visual'
        """
        builders = {
            "conceptual": self.build_conceptual_explanation,
            "practical": self.build_practical_examples,
            "reflection": self.build_reflection_questions,
            "visual": self.build_visual_summary,
        }
        builder = builders.get(content_type)
        if not builder:
            raise ValueError(f"Tipo de conteúdo inválido: {content_type}")
        if content_type == "visual":
            return builder(profile, topic, version, output_format=output_format)
        return builder(profile, topic, version)

    # ─── Prompt de conversa livre ────────────────────────

    def build_conversation_system(self, profile: dict, topic: str) -> str:
        """Monta system prompt para conversa livre na sessão."""
        return (
            f"{self._get_persona_v2(profile)}\n\n"
            f"ESTILO DE ENSINO:\n{self.STYLE_ADAPTATIONS_V2.get(profile['estilo'], '')}\n\n"
            f"{self._build_context_v2(profile, topic)}\n\n"
            f"INSTRUÇÕES PARA CONVERSA:\n"
            f"- Mantenha o foco no tópico '{topic}' mas permita explorações relacionadas\n"
            f"- Responda dúvidas com clareza e sempre adequando ao perfil do aluno\n"
            f"- Se o aluno demonstrar confusão, reformule a explicação\n"
            f"- Faça perguntas de verificação ocasionais para garantir compreensão\n"
            f"- Seja encorajador e paciente\n"
            f"- Responda sempre em Português do Brasil"
        )
