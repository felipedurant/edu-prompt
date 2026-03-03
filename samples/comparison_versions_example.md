# Comparacao v1 vs v2: Equacoes de Segundo Grau
**Perfil:** Pedro (14 anos, iniciante, cinestesico)
**API:** gemini (gemini-2.5-flash)
**Tempo total:** 6.2s

## Explicacao Conceitual

### v1 (Basico) [api]
Equacoes de segundo grau sao equacoes no formato ax^2 + bx + c = 0, onde a, b e c sao numeros e a diferente de zero.

Pense passo a passo:
1. Primeiro, identifique os coeficientes a, b e c
2. Depois, calcule o discriminante: delta = b^2 - 4ac
3. Se delta > 0, tem duas raizes reais
4. Se delta = 0, tem uma raiz real
5. Se delta < 0, nao tem raiz real

As raizes sao calculadas pela formula de Bhaskara: x = (-b +/- raiz(delta)) / 2a

### v2 (Otimizado) [api]
# Equacoes de Segundo Grau: Desvendando o Misterio do x^2

## Imagine a seguinte situacao...

Voce esta jogando futebol e chuta a bola para o alto. A trajetoria da bola faz uma **curva** -- sobe, atinge o ponto mais alto, e desce. Essa curva e descrita por uma **equacao de segundo grau**!

## O que e?

Uma equacao de segundo grau tem a forma:

**ax^2 + bx + c = 0**

Onde:
- **a** = quanto a curva "abre" (nao pode ser zero!)
- **b** = para onde a curva se desloca
- **c** = onde a curva cruza o eixo y

### Construindo Passo a Passo

**Passo 1 - Identifique os ingredientes**
Em 2x^2 + 3x - 5 = 0: a=2, b=3, c=-5

**Passo 2 - Calcule o Delta (discriminante)**
Delta = b^2 - 4.a.c = 9 - 4(2)(-5) = 9 + 40 = 49

**Passo 3 - Interprete o Delta**
- Delta > 0 (49 > 0): Duas solucoes! A bola cruza o chao em 2 pontos

**Passo 4 - Encontre as raizes (Formula de Bhaskara)**
x = (-3 +/- raiz(49)) / (2.2) = (-3 +/- 7) / 4
x1 = 1 e x2 = -2.5

> Ate aqui, ficou claro que delta e como um "detector" que revela quantas solucoes existem?

## Atividade Pratica

Pegue uma bola e jogue para cima. Observe: ela sobe, para, e desce. Cada ponto dessa trajetoria pode ser calculado com uma equacao de segundo grau!

**Conceito-chave**: Equacao de segundo grau modela qualquer situacao com formato de parabola -- trajetorias, areas, lucros.

## Exemplos Praticos

### v1 (Basico) [api]
Exemplos de equacoes de segundo grau:

1. x^2 - 5x + 6 = 0 -> a=1, b=-5, c=6 -> delta=25-24=1 -> x1=3, x2=2
2. x^2 + 4x + 4 = 0 -> a=1, b=4, c=4 -> delta=16-16=0 -> x=-2
3. 2x^2 - 8 = 0 -> a=2, b=0, c=-8 -> delta=0+64=64 -> x1=2, x2=-2

### v2 (Otimizado) [api]
# Exemplos Praticos: Equacoes de Segundo Grau no Dia a Dia

## Exemplo 1: A Quadra de Futebol
Voce quer construir uma quadra retangular com 60m^2 de area. O comprimento e 7m a mais que a largura. Quais as dimensoes?

**Montando**: largura = x, comprimento = x+7
Area: x(x+7) = 60 -> x^2 + 7x - 60 = 0
Delta = 49 + 240 = 289 -> raiz(289) = 17
x = (-7+17)/2 = 5m (largura), comprimento = 12m

**Conceito aplicado**: Problemas de area frequentemente geram equacoes de segundo grau!

## Exemplo 2: O Pulo do Skatista
Um skatista salta de uma rampa. Sua altura h (em metros) em funcao do tempo t e:
h = -5t^2 + 10t

Quando ele volta ao chao? h = 0:
-5t^2 + 10t = 0 -> t(-5t + 10) = 0
t = 0 (saida) ou t = 2s (aterrissagem)

## Desafio
Uma piscina retangular tem perimetro de 30m e area de 50m^2. Quais sao as dimensoes?

## Perguntas de Reflexao

### v1 (Basico) [api]
1. O que acontece quando delta e negativo?
2. Por que o coeficiente 'a' nao pode ser zero?
3. Cite uma situacao real onde se usa equacao de segundo grau.
4. Qual a diferenca entre equacao de primeiro e segundo grau?

### v2 (Otimizado) [api]
Perguntas organizadas pela Taxonomia de Bloom, com dicas e nivel de dificuldade progressivo. Inclui perguntas de compreensao, aplicacao, analise e criacao.

## Resumo Visual

### v1 (Basico) [api]
Formula: ax^2 + bx + c = 0
Delta = b^2 - 4ac
Bhaskara: x = (-b +/- sqrt(delta)) / 2a

### v2 (Otimizado) [api]
Mapa mental ASCII completo com ramificacoes, tabela-resumo com conceitos e exemplos, regra rapida mnemonica e conexoes interdisciplinares.

---
**Cache:** 0 hits / 8 misses (0% economia)

---
*Gerado por EduPrompt Platform*
