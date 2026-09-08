# Textos prontos para o cadastro do reúso e para o formulário

Copiar e colar. Antes de enviar, **conferir as URLs exatas dos conjuntos no dados.gov.br no
dia do cadastro** — o portal migrou de `dados.gov.br/dataset/...` para
`dados.gov.br/dados/conjuntos-dados/...` e os slugs podem ter mudado.

---

## Nome

IDSP-F — Índice de Deserto de Serviço Público Federal

## Tagline

Onde o Estado federal está mais ausente — e mais perto de sumir.

## URL do reúso

`https://<usuario>.github.io/idsp-f/`

Esta é a URL definitiva. O produto continua evoluindo na mesma URL até o julgamento.

## Descrição (≈ 600 caracteres)

> O IDSP-F cruza duas bases abertas do Executivo Federal — o cadastro de servidores do
> Portal da Transparência e o conjunto de Abono de Permanência do dados.gov.br — com a
> população do IBGE para classificar cada UF em uma matriz de presença × fragilidade.
> Presença: servidores federais por 10 mil habitantes. Fragilidade: parcela dos ativos que
> já cumpre requisitos de aposentadoria. O quadrante "deserto crítico" indica onde serviços
> como INSS, Institutos Federais, universidades, Receita e IBGE correm maior risco de
> descontinuidade — insumo direto para planejamento e dimensionamento da força de trabalho.
> Código e dados abertos; agregação por órgão e UF, sem dados individuais.

## Descrição curta (≈ 200 caracteres)

> Índice que cruza presença de servidores federais por habitante com a parcela já elegível
> à aposentadoria, por UF, para mostrar onde os serviços federais correm risco de
> descontinuidade.

## Datasets a citar

1. **Gestão de Pessoas (Executivo Federal) — Abono Permanência** — MGI — dados.gov.br
   `https://dados.gov.br/dados/conjuntos-dados/gastos-pessoal-abono-permanencia`
2. **Servidores do Executivo Federal / Portal da Transparência — Cadastro** — CGU e MGI
   `https://dados.gov.br/dados/conjuntos-dados/servidores-do-executivo-federal`
   e `https://portaldatransparencia.gov.br/download-de-dados/servidores`
3. **Estimativas da população residente 2026** — IBGE — `https://sidra.ibge.gov.br/tabela/6579`
   (e a entrada correspondente no dados.gov.br, se houver)

## Versão declarada

v1.0 — recorte por UF. Recorte municipal para o núcleo de serviços em desenvolvimento na
mesma URL.

---

## Texto de apresentação (formulário)

### O problema

O planejamento da força de trabalho federal é discutido em agregados nacionais: quantos
servidores o Estado tem, quantos vão se aposentar, quantas vagas autorizar. O agregado
nacional esconde a pergunta que importa para quem depende do serviço: **em qual território
o Estado federal já está ausente e vai ficar mais?**

Um estado pode ter presença federal razoável e um quadro prestes a se esvaziar. Outro pode
ter presença baixa e estável. As duas situações exigem decisões diferentes de concurso,
lotação e remoção — e hoje não há um instrumento público que as distinga por território.

### A solução

O IDSP-F transplanta para a capacidade estatal federal o conceito de "deserto" já
consolidado em outras políticas (desertos alimentares, desertos de notícias) e o torna
bidimensional. Para cada UF, cruza:

- **Presença** — servidores civis ativos do Executivo Federal por 10 mil habitantes;
- **Fragilidade** — parcela desses servidores que já cumpre os requisitos de aposentadoria
  e permanece na ativa recebendo abono de permanência.

O cruzamento produz quatro classes. A que interessa é o **deserto crítico**: pouca presença
hoje e muita gente que pode sair amanhã. O produto tem ainda uma lente de "núcleo de
serviços" — INSS, Receita Federal, Institutos Federais, universidades federais e IBGE — que
isola os serviços que a população encontra fisicamente no território.

### Por que este reúso devolve o dado à sua finalidade

O conjunto "Abono de Permanência" declara no dados.gov.br, como política pública associada,
o *planejamento e dimensionamento da força de trabalho no serviço público federal*. O dado
está publicado há anos e é pouco reusado, porque isolado ele responde apenas "quanto se
gasta com abono". Cruzado com o cadastro de servidores e com a população, ele responde
"onde o serviço público federal pode parar". O IDSP-F é exatamente esse reúso.

### Impacto e benefício à sociedade

Um gestor de pessoas identifica em trinta segundos, no celular, quais unidades da federação
concentram simultaneamente carência de pessoal e exposição à aposentadoria — insumo direto
para dimensionar concursos, priorizar lotação e desenhar política de remoção e de sucessão.

Um cidadão, uma entidade de classe, um jornalista ou um vereador do interior consegue
perguntar, com número rastreável à fonte: a agência do INSS, o campus do instituto federal
e o hospital universitário do meu estado correm risco de ficar sem gente?

### Inovação

Três decisões tornam o índice diferente de um painel de pessoal: o transplante do conceito
de deserto para capacidade estatal federal; a bidimensionalidade — presença cruzada com
risco de evasão, e não um ranking simples de servidores por habitante; e a lente do núcleo
de serviços, que separa o Estado que atende o cidadão no território do Estado que
administra a si mesmo.

### Replicabilidade

Código sob licença MIT, dados derivados sob CC BY 4.0, pipeline reprodutível em cinco
comandos. Todo julgamento metodológico — recorte do universo, definição do núcleo, corte da
matriz, limiar de supressão — está em arquivos de configuração versionados, não no código.
Um estado ou município replica o índice sobre o seu próprio regime próprio de previdência
trocando as duas bases de entrada e ajustando a definição de núcleo.

### Privacidade

Nome, CPF e matrícula nunca são carregados. Não há ligação de registros entre as bases: o
cruzamento é por órgão e UF, em forma de contagem. Nenhuma célula com menos de cinco
pessoas é publicada, e razões derivadas de células suprimidas são omitidas para impedir
reconstrução. Nada abaixo de UF é publicado. O site não usa cookies, login nem analytics.

---

## Frase-síntese para redes sociais

> Quantos servidores federais existem por 10 mil habitantes no seu estado — e quantos deles
> já podem se aposentar hoje? O IDSP-F cruza duas bases abertas e mostra onde o serviço
> público federal corre risco de descontinuidade. Código e dados abertos.
