# Textos prontos para o cadastro do reúso e para o formulário

Copiar e colar. Estado em 11/09/2026: site no ar, repositório público, dados reais.

---

## Identificação

| Campo | Valor |
|---|---|
| **Nome** | IDSP-F — Índice de Deserto de Serviço Público Federal |
| **Tagline** | Onde o Estado federal está mais ausente — e mais perto de sumir. |
| **URL do reúso** | https://idsp-f.vercel.app/ |
| **Código-fonte** | https://github.com/Carlafigueiredo10/idsp-f |
| **Licenças** | Código MIT · dados derivados e textos CC BY 4.0 |
| **Versão** | v1.0 — recorte por UF, referência dezembro de 2025 |

## Conjuntos de dados utilizados

1. **Gestão de Pessoas (Executivo Federal) — Abono Permanência** — MGI
   https://dados.gov.br/dados/conjuntos-dados/gestao-de-pessoas-executivo-federal---abono-permanencia
   (arquivo usado: `ABONOP_122025.csv`, em `repositorio.dados.gov.br/segrt/`)
2. **Servidores do Executivo Federal — Cadastro** — CGU / MGI
   https://dados.gov.br/dados/conjuntos-dados/servidores-do-executivo-federal
   (arquivo usado: `202512_Cadastro.csv`, do Portal da Transparência)
3. **Estimativas da população residente 2025** — IBGE
   https://sidra.ibge.gov.br/tabela/6579

Volume processado: **431.264 servidores civis ativos** e **62.909 abonos de permanência**,
ambos com referência dezembro de 2025.

## Descrição (≈ 600 caracteres)

> O IDSP-F cruza duas bases abertas do Executivo Federal — o cadastro de servidores do
> Portal da Transparência e o Abono de Permanência do dados.gov.br — com a população do
> IBGE para classificar cada UF numa matriz de presença × fragilidade. Presença:
> servidores federais por 10 mil habitantes. Fragilidade: parcela dos ativos que já cumpre
> os requisitos de aposentadoria. O quadrante "deserto crítico" mostra onde os serviços
> federais correm maior risco de descontinuidade — insumo direto para planejamento e
> dimensionamento da força de trabalho, a finalidade que a própria fonte declara. Código e
> dados abertos, sem dados individuais.

## Descrição curta (≈ 200 caracteres)

> Índice que cruza presença de servidores federais por habitante com a parcela já elegível
> à aposentadoria, por UF, mostrando onde os serviços federais correm risco de
> descontinuidade.

---

## Texto de apresentação

### O problema

O planejamento da força de trabalho federal é discutido em agregados nacionais: quantos
servidores o Estado tem, quantos vão se aposentar, quantas vagas autorizar. O agregado
nacional esconde a pergunta que importa para quem depende do serviço: **em qual território
o Estado federal já está ausente e vai ficar mais?**

Um estado pode ter presença razoável e um quadro prestes a se esvaziar; outro pode ter
presença baixa e estável. São situações que pedem decisões diferentes de concurso, lotação
e remoção, e não havia instrumento público que as distinguisse por território.

### A solução

O IDSP-F transplanta para a capacidade estatal federal o conceito de "deserto", já
consolidado em outras políticas, e o torna bidimensional. Para cada UF cruza:

- **Presença** — servidores civis ativos do Executivo Federal por 10 mil habitantes;
- **Fragilidade** — parcela desses servidores que já cumpre os requisitos de aposentadoria
  e permanece na ativa recebendo abono de permanência.

O cruzamento produz quatro classes. A que interessa é o **deserto crítico**: pouca presença
hoje e muita gente que pode sair amanhã.

### Quatro lentes, e por que isso importa

O produto não entrega um número só. São quatro recortes:

| Lente | Universo |
|---|---|
| **Serviços exclusivos** (padrão) | INSS, Fazenda/Receita, IBGE — só a União entrega |
| **Educação federal** | universidades e Institutos Federais — estados e municípios também entregam |
| **Núcleo de serviços** | as duas anteriores somadas |
| **Executivo Federal** | todos os órgãos do universo |

A separação nasceu de um resultado que não se sustentava. Somando tudo, **São Paulo
aparecia como a menor presença federal do país** e caía em "deserto crítico". Decomposto,
o quadro se inverte: em serviços exclusivos SP tem 1,67 por 10 mil contra mediana nacional
de 1,55 — **acima da mediana**; em educação federal tem 2,82 contra 15,70. O vazio paulista
é inteiramente educação federal, e existe porque São Paulo construiu a própria rede
estadual (USP, Unicamp, Unesp, Centro Paula Souza).

Somar as duas naturezas responderia "onde a União está menos presente" fingindo responder
"onde o serviço pode faltar ao cidadão". São perguntas diferentes e agora têm lentes
diferentes.

### Do diagnóstico ao instrumento

O índice diz **onde**. A camada de **instrumentos disponíveis** diz **com que instrumento**
aquilo se trata e **em que mesa** a decisão é tomada. Cada cartão traz o instrumento já
existente no ordenamento, a norma que o cria e a instância com competência para acioná-lo,
e aparece no painel das UFs cujo quadrante e grupo de serviço ele atende.

Não são recomendações: o IDSP-F não decide lotação, concurso ou cooperação, e não fala por
nenhum órgão. Descrever instrumento e competência é informação pública verificável. Um
cartão só vai ao ar depois de conferida a vigência da norma, e um teste automatizado recusa
qualquer publicação sem base normativa com link.

### Impacto e benefício à sociedade

Um gestor de pessoas identifica em trinta segundos, no celular, quais unidades da federação
concentram carência de pessoal e exposição à aposentadoria ao mesmo tempo — insumo para
dimensionar concursos, priorizar lotação e desenhar sucessão.

Um cidadão, uma entidade de classe, um jornalista ou um vereador do interior pergunta, com
número rastreável à fonte: a agência do INSS, o campus do instituto federal e o hospital
universitário do meu estado correm risco de ficar sem gente?

### Por que este reúso devolve o dado à sua finalidade

O conjunto "Abono de Permanência" declara no dados.gov.br, como política pública associada,
o *planejamento e dimensionamento da força de trabalho no serviço público federal*. Isolado,
ele responde apenas "quanto se gasta com abono". Cruzado com o cadastro de servidores e com
a população, responde "onde o serviço público federal pode parar".

### Inovação

Transplante do conceito de deserto para capacidade estatal federal; bidimensionalidade
(presença cruzada com risco de evasão, não um ranking de servidores por habitante); a
separação entre serviço exclusivo e serviço concorrente, que impede a leitura falsa; e a
camada que liga diagnóstico a instrumento de governança.

### Rigor metodológico

Nove defeitos foram encontrados e corrigidos com dados reais, cada um com teste automatizado
que impede o retorno. Entre eles: o campo de UF do cadastro vem preenchido com `-1` em 30%
das linhas, e não vazio; o arquivo do abono tem um campo a mais por linha, o que deslocava
silenciosamente a UF de residência para receber o nome da cidade; e os governos de
ex-territórios, presentes numa base e não na outra, produziam "110% dos servidores já
elegíveis" em Rondônia. São 29 testes, incluindo invariantes que recusam publicar razão
impossível.

### Replicabilidade

Código MIT, dados derivados CC BY 4.0, pipeline reprodutível em cinco comandos. Todo
julgamento metodológico — recorte do universo, composição das lentes, corte da matriz,
limiar de supressão, instrumentos — está em arquivos de configuração versionados, não no
código. Um estado ou município replica o índice sobre o próprio RPPS trocando as duas bases
de entrada.

### Privacidade

Nome, CPF e matrícula nunca são carregados: a leitura usa lista fechada de colunas. Não há
ligação de registros entre as bases — o cruzamento é por órgão e UF, em contagem. Nenhuma
célula com menos de cinco pessoas é publicada, e razões derivadas de células suprimidas são
omitidas para impedir reconstrução. Nada abaixo de UF é publicado. O site não usa cookies,
login nem analytics.

---

## Frase para redes sociais

> Quantos servidores federais existem por 10 mil habitantes no seu estado — e quantos deles
> já podem se aposentar hoje? O IDSP-F cruza duas bases abertas e mostra onde o serviço
> público federal corre risco de descontinuidade. Código e dados abertos.
