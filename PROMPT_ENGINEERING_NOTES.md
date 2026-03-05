# Notas de Engenharia de Prompt

Documentacao das decisoes, tecnicas e resultados observados na engenharia de prompt do EduPrompt Platform.

## 1. Tecnicas Aplicadas

### 1.1 Persona Prompting

**Definicao**: Atribuir um papel especifico ao modelo para guiar o tom, vocabulario e abordagem da resposta.

**v1 (Basica)**:
```
Voce e um professor experiente em Pedagogia.
```

**v2 (Otimizada)**:
```
Voce e um professor especializado em educacao personalizada,
com expertise em pedagogia adaptativa e ensino para o estilo visual.
Use linguagem acessivel mas respeitosa -- sem infantilizar.
Conecte os conceitos ao mundo do adolescente (tecnologia, redes sociais, vestibular).
Seja um mentor que inspira curiosidade.
Seu objetivo e garantir compreensao profunda, nao apenas transmissao de informacao.
```

**Decisao**: A v2 calibra a persona por faixa etaria (<=12, 13-17, 18-25, 26+), ajustando tom, vocabulario e tipo de analogia. Isso produz respostas significativamente mais adequadas ao publico-alvo.

**Evidencia**: Ao comparar v1 vs v2 para um aluno de 10 anos sobre "DNA", a v1 usa termos como "nucleotideos" e "dupla helice" sem contextualizacao, enquanto a v2 compara DNA a "uma receita de bolo que fica dentro de cada celula do seu corpo".

### 1.2 Context Setting

**Definicao**: Injetar dados relevantes do contexto no prompt para personalizar a resposta.

**v1 (Basica)**:
```
O aluno se chama Ana, tem 16 anos, esta no nivel intermediario
e tem estilo de aprendizado visual. O topico de estudo e: Fotossintese.
```

**v2 (Otimizada)**:
```
PERFIL DO ALUNO:
- Nome: Ana
- Idade: 16 anos
- Nivel: intermediario -- ja tem nocoes basicas e precisa aprofundar,
  conectar conceitos e ver aplicacoes
- Estilo de aprendizado: visual
- Topico: Fotossintese
- Contexto: estudante de biologia preparando vestibular

Adapte TODO o conteudo para este perfil especifico.
Use exemplos do cotidiano adequados a idade e contexto do aluno.
```

**Decisao**: A v2 usa formato estruturado (lista), inclui descricao semantica do nivel (nao apenas o label), e adiciona contexto extra quando disponivel. Tambem instrui explicitamente o modelo a adaptar.

**Resultado observado**: A v2 produz respostas que mencionam o contexto do aluno (ex: "pensando no vestibular, esse e um topico muito cobrado na prova") enquanto a v1 ignora esses detalhes.

### 1.3 Chain-of-Thought (CoT)

**Definicao**: Instruir o modelo a raciocinar passo a passo antes de apresentar a resposta final.

**v1 (Basica)**:
```
Pense passo a passo e explique o conceito de 'Fotossintese'
de forma clara e adequada ao nivel do aluno.
```

**v2 (Otimizada)**:
```
ABORDAGEM (Chain-of-Thought com scaffolding):
1. Comece com uma pergunta ou situacao concreta do cotidiano que conecte o aluno ao tema
   -> Use algo que alguem da idade do aluno vivencia de verdade
2. Apresente o conceito fundamental de forma acessivel, conectando com o que o aluno ja sabe
3. Desenvolva passo a passo, construindo cada ideia sobre a anterior — use analogias concretas
   (compare com objetos, situacoes ou processos que o aluno conhece, nunca use analogias abstratas)
4. Inclua um checkpoint de compreensao: 'Ate aqui, ficou claro que [resumo do que foi explicado]?'
5. Aprofunde com conexoes entre o topico e outros assuntos que o aluno estuda ou conhece
6. Finalize com:
   - Um resumo-sintese de 2-3 frases
   - Uma reflexao meta-cognitiva: 'O conceito-chave para lembrar e...'
   - Uma pergunta motivadora para despertar curiosidade sobre o proximo passo

FORMATO (use Markdown):
- Use titulos ## para cada secao
- Use **negrito** para termos-chave
- Inclua analogias concretas e vividas adequadas a idade
- Se aplicavel, inclua curiosidade ou fato interessante
```

**Decisao**: A v2 aplica **scaffolding pedagogico** -- uma progressao estruturada que guia o modelo a construir conhecimento camada por camada. Inclui:
- **Ancora contextual**: conecta ao mundo do aluno antes de apresentar o conceito
- **Analogias concretas obrigatorias**: nunca abstratas, sempre comparando com objetos e situacoes reais
- **Checkpoints de compreensao**: pausas para verificar entendimento
- **Meta-cognicao**: reflexao sobre o proprio processo de aprendizado
- **Pergunta motivadora**: estimula curiosidade para continuar estudando
- **Formatacao Markdown explicita**: garante saida bem estruturada na web e CLI

**Resultado observado**: A v2 consistentemente produz explicacoes mais longas, mais estruturadas e com melhor fluxo logico. Os checkpoints ("Ate aqui...") criam um ritmo pedagogico que facilita a compreensao. As analogias concretas tornam conceitos abstratos tangiveis.

### 1.4 Output Formatting

**Definicao**: Especificar o formato desejado da saida para controlar estrutura e qualidade.

**v1 (Basica)**:
```
Organize a resposta em paragrafos.
```

**v2 (Otimizada)**:
```
FORMATO (use Markdown):
- Use titulos ## para cada secao da explicacao
- Use **negrito** para termos-chave e conceitos centrais
- Use listas e bullet points para organizar informacao
- Inclua analogias concretas e vividas adequadas a idade (16 anos)
- Extensao: proporcional ao nivel (intermediario)
- Se aplicavel, inclua curiosidade ou fato interessante
```

**Decisao**: A v2 especifica constraints concretos (negrito para termos-chave, analogias por idade, extensao por nivel). Para cada tipo de conteudo, o formato e diferente:

| Tipo | Formato v2 |
|---|---|
| Explicacao conceitual | Secoes ## Markdown, analogias concretas, checkpoints, resumo + pergunta motivadora |
| Exemplos praticos | Numerados ##, progressivos, variacoes, "Por que importa", desafio com criterio de sucesso |
| Perguntas de reflexao | Taxonomia de Bloom com cenarios, blockquotes para provocacoes, dicas em italico |
| Resumo visual | Mapa mental Mermaid (web) ou ASCII com emojis (CLI), tabela-resumo, mnemonico, conexoes |

## 2. Adaptacao por Estilo de Aprendizado

Cada estilo VARK recebe instrucoes especificas no prompt:

| Estilo | Instrucao v2 (resumo) |
|---|---|
| **Visual** | Diagramas ASCII, esquemas, emojis como icones, hierarquia clara, tabelas |
| **Auditivo** | Linguagem conversacional, pausas naturais, repeticao estrategica, dialogo |
| **Leitura-escrita** | Secoes numeradas, definicoes formais, glossario, texto academico acessivel |
| **Cinestesico** | Atividades praticas, simulacoes mentais, desafios progressivos, analogias fisicas |

**Exemplo concreto** -- mesmo topico ("Celula Animal") com estilos diferentes:

- **Visual**: "Imagine a celula como uma cidade vista de cima. O nucleo e a prefeitura..."
- **Cinestesico**: "Pegue uma bola de isopor e um canudo. Vamos construir um modelo..."
- **Auditivo**: "Agora, preste atencao nisto: a celula funciona como uma fabrica..."
- **Leitura-escrita**: "1. Definicao: A celula animal e a unidade funcional dos organismos..."

## 3. Sistema de Versoes (v1 vs v2)

### Proposito

O sistema de versoes existe para demonstrar quantitativamente o impacto da engenharia de prompt. A v1 aplica as tecnicas de forma literal e minima; a v2 aplica de forma refinada e moderna.

### Diferencas quantitativas observadas

| Metrica | v1 | v2 | Melhoria |
|---|---|---|---|
| Extensao media | ~200 palavras | ~500 palavras | +150% |
| Uso de estrutura (titulos, listas) | Raro | Consistente | Significativa |
| Analogias contextualizadas | Genericas | Adequadas a idade | Qualitativa |
| Checkpoints de compreensao | Ausentes | Presentes | Pedagogicamente superior |
| Desafios praticos | Ausentes | Presentes | Engajamento |

### Por que v2 e o padrao

A v2 e usada como padrao em toda a aplicacao (sessao, multi-API). A v1 so aparece no modo de comparacao de versoes, servindo como baseline para demonstrar a evolucao.

## 4. Quiz (/quiz_me)

O `/quiz_me` inverte o fluxo pedagogico: em vez de a IA ensinar, ela avalia o aluno.

### Geracao da pergunta

```
TAREFA: Gere UMA pergunta para testar o conhecimento do aluno sobre 'Fotossintese'.

DIRETRIZES:
- A pergunta deve ser adequada ao nivel intermediario
- Deve ser respondivel em texto livre (nao multipla escolha)
- Deve avaliar compreensao, nao memorizacao
- Inclua contexto suficiente para a pergunta fazer sentido
```

O prompt inclui o **contexto da conversa atual** (ultimas 6 mensagens), permitindo que a pergunta seja baseada no que ja foi discutido -- testando compreensao real.

### Feedback

O feedback usa formato estruturado com indicadores visuais:
- Correto / Parcialmente correto / Nao exatamente
- Explicacao do que estava certo
- Complemento com resposta correta
- Dica para lembrar o conceito

## 5. LLM-as-Judge

O avaliador automatico usa **DeepSeek V3.2** (via OpenRouter) exclusivamente como juiz, avaliando conteudo gerado por outros modelos.

### Criterios (1-10)

| Criterio | O que avalia |
|---|---|
| Adequacao ao nivel | Conteudo apropriado para idade e nivel |
| Clareza e coerencia | Linguagem clara, logica bem encadeada |
| Adequacao ao estilo | Respeita o estilo de aprendizado |
| Engajamento pedagogico | Motivador e pedagogicamente efetivo |

### Prompt do judge

O prompt do judge e instruido a:
1. Avaliar objetivamente cada criterio (nota 1-10)
2. Justificar com exemplos concretos do texto
3. Indicar o vencedor
4. Responder em JSON estrito para parsing automatico

**Decisao**: temperatura baixa (0.3) para consistencia nas avaliacoes.

## 6. Sanitizacao de Input

Protecao contra prompt injection:

```python
def sanitize_topic(topic: str) -> str:
    topic = topic.strip()
    topic = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', topic)  # remove controle
    if len(topic) > 500:
        topic = topic[:500]
    return topic
```

- Remove caracteres de controle Unicode
- Limita tamanho a 500 caracteres
- Loga warning para topicos truncados

## 7. Gestao de Contexto (Sliding Window)

Para sessoes longas, o sistema implementa janela deslizante:

1. Estima tokens: `total_chars / 4` (~4 chars/token em PT-BR)
2. Se exceder threshold (3000 tokens):
   - Mantem ultimas 8 mensagens integrais
   - Resumo das mensagens antigas em paragrafo curto
3. Gemini (1M contexto): threshold raramente atingido
4. Groq/DeepSeek (128K): relevante em sessoes longas

## 8. Cache Inteligente

### Composicao da chave

Hash SHA-256 de: `provider + model + system_prompt + messages_json + temperature`

### Reuso entre modos

O cache e **global e compartilhado**. Cenario real:

1. Sessao com Gemini Flash sobre "Fotossintese" -> gera `/exemplos` -> cache armazena
2. Comparacao multi-API sobre "Fotossintese" -> Gemini Flash ja esta em cache -> **economia real**
3. Comparacao v1/v2 com Gemini Flash -> o v2 de exemplos ja esta em cache

### Indicador visual

Toda resposta mostra origem:
- `Cache` -- resposta do cache (instantanea)
- `API (1.2s)` -- chamada nova a API

## 9. Renderizacao Markdown e Mermaid.js (Web)

A interface web renderiza as respostas da IA com suporte completo a:

- **Markdown**: Parsed via Marked.js, sanitizado com DOMPurify contra XSS
- **Mermaid.js**: Diagramas mindmap renderizados nativamente no navegador

### Adaptacao do output_format por interface

O `PromptEngine.build_visual_summary()` recebe um parametro `output_format`:
- `"ascii"` (CLI): instrui a LLM a gerar mapas mentais com caracteres ASCII (├──, └──, │)
- `"mermaid"` (Web): instrui a LLM a gerar blocos ```mermaid com sintaxe mindmap valida

O prompt v2 inclui exemplo de sintaxe Mermaid exato para minimizar erros de formatacao, alem de restricoes como evitar caracteres especiais nos nos.

## 10. Licoes Aprendidas

1. **Formato estruturado nos prompts** (listas, secoes numeradas) produz saidas mais organizadas que instrucoes em prosa
2. **Personas calibradas por idade** fazem diferenca significativa na adequacao do conteudo
3. **Checkpoints de compreensao** ("Ate aqui ficou claro...") criam um ritmo pedagogico natural
4. **Taxonomia de Bloom** nas perguntas de reflexao eleva a qualidade das questoes
5. **Temperatura 0.7** e um bom equilibrio entre criatividade e consistencia para conteudo educacional
6. **Cache global** compartilhado entre modos e um diferencial real -- economia mensuravel
7. **Analogias concretas** (nunca abstratas) tornam conceitos complexos tangiveis para qualquer faixa etaria
8. **Instrucoes de formatacao Markdown explicitas** nos prompts melhoram significativamente a apresentacao na web
9. **Exemplos de sintaxe no prompt** (como Mermaid mindmap) reduzem drasticamente erros de formatacao na saida
