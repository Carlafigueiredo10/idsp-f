# Metodologia — IDSP-F v1.0

Índice de Deserto de Serviço Público Federal · recorte por unidade da federação.
Versão congelada da implementação publicada. Alterações posteriores entram como v1.1 e
ficam registradas no histórico do repositório e em `metadata.json`.

---

## 1. Pergunta

Onde a presença do Estado federal no território é mais rarefeita **e** mais próxima de
diminuir ainda mais?

A pergunta tem duas metades, e nenhuma delas responde sozinha. Um estado com poucos
servidores por habitante pode estar estável. Um estado bem servido pode estar prestes a
perder metade do seu quadro. O risco de descontinuidade está no cruzamento.

## 2. Universo

**Incluídos:** servidores civis ativos do Poder Executivo Federal com cargo efetivo em
exercício, conforme o Cadastro de Servidores do Portal da Transparência (fonte SIAPE).

**Excluídos do universo:** contratos temporários, professores substitutos, visitantes e
temporários, nomeados para cargo em comissão sem vínculo efetivo, estagiários, aposentados,
pensionistas e instituidores de pensão. Os padrões exatos estão em
`config/parametros.yaml → filtro_f1` e são copiados para `metadata.regras_de_filtro`.

**Fora do escopo do índice** (declarado no produto): militares, Banco Central, Judiciário,
Legislativo, estatais, servidores estaduais e municipais.

> O IDSP-F mede presença **federal**, não capacidade estatal total do território. Um estado
> pode ter serviço público forte e presença federal fraca.

### Duas lentes

| Lente | Universo |
|---|---|
| **Núcleo de serviços** | INSS, Fazenda (Receita Federal), Institutos Federais (e CEFETs e Colégio Pedro II), universidades federais e IBGE |
| **Executivo Federal total** | todos os órgãos do universo acima |

O núcleo reúne os serviços federais que a população encontra fisicamente no território:
a agência do INSS, o campus do instituto federal, o hospital universitário, a unidade da
Receita, a agência de coleta do IBGE. A classificação é por expressão regular sobre o nome
do órgão de exercício e do órgão superior, em `config/nucleo.yaml`.

> **Decisão registrada — a Receita Federal não é separável.** A Receita não é um órgão
> próprio no cadastro de servidores: seu pessoal aparece sob `MINISTERIO DA FAZENDA`, e as
> unidades organizacionais têm nomes funcionais (`EQUIPE DE FISCALIZACAO`,
> `EQUIPE DE ATENDIMENTO AO CONTRIBUINTE`, `SECAO DE ADMINISTRACAO ADUANEIRA`) que não
> mencionam a Receita. Buscar "Receita Federal" no cadastro encontra menos de 2 mil
> vínculos, contra mais de 24 mil no guarda-chuva do ministério.
>
> Pior: na base de abono **as unidades da Receita se identificam pelo nome**. Definir o
> grupo pela unidade organizacional produziria um numerador que reconhece a Receita e um
> denominador que não a reconhece — uma fragilidade acima de 100 %.
>
> Por isso o grupo é o **Ministério da Fazenda inteiro**, rotulado "Fazenda (Receita
> Federal)", do qual a Receita é a maior parte. Inclui Tesouro, PGFN e demais unidades
> fazendárias. Comissão de Valores Mobiliários e Susep são órgãos distintos e ficam fora.

> **Decisão registrada — grafias divergentes entre as bases.** O cadastro escreve
> `INSTITUTO NACIONAL DO SEGURO SOCIAL` e o abono escreve `INSTITUTO NACIONAL DE SEGURO
> SOCIAL`. Com o padrão colado a uma das grafias, o INSS desaparecia inteiro do eixo B.
> Todo padrão do núcleo precisa casar nas duas bases; é o que a regra de ouro no topo de
> `config/nucleo.yaml` exige.

## 3. Fontes

| | Base | Órgão | Papel |
|---|---|---|---|
| F1 | Cadastro de Servidores, arquivo mensal `AAAAMM_Cadastro.csv` | CGU (Portal da Transparência), origem SIAPE | numerador da presença, denominador da fragilidade |
| F2 | Abono de Permanência, recurso mensal | MGI, dados.gov.br | numerador da fragilidade |
| F3 | Estimativas da população residente por UF | IBGE (SIDRA, tabela 6579) | denominador da presença |
| F4 | Malha territorial das UFs | IBGE (API de malhas v3) | mapa |

Mês de referência, SHA-256 e contagens de cada arquivo usado ficam registrados em
`data/processed/metadata.json` e são exibidos na tela "Fontes" do site.

> **Decisão registrada — os dois meses são iguais, e é o abono que manda.** A fragilidade
> é uma razão entre F1 e F2; comparar um numerador de um mês com um denominador de outro
> mede a passagem do tempo, não a fragilidade. Por isso as duas bases são lidas no mesmo
> mês de referência.
>
> O mês possível é o do abono. O cadastro de servidores é publicado mensalmente e está em
> dia; o conjunto de Abono de Permanência no dados.gov.br **está desatualizado** — o portal
> o marca como tal, e o recurso mais recente é de dezembro de 2025. O índice usa dezembro
> de 2025 nas duas bases e a estimativa de população do IBGE do mesmo ano. Publicar o
> cadastro mais recente ao lado de um abono nove meses mais velho daria a impressão de
> atualidade que o dado não tem.

> **Onde o arquivo do abono precisa de cuidado.** O recurso publicado tem 14 nomes no
> cabeçalho e 15 campos por linha, por causa de um separador sobrando no fim de cada
> registro. Lido de forma ingênua, o pandas promove a primeira coluna a índice e desloca
> todos os valores: a UF de residência passa a receber o nome da cidade, sem erro nenhum na
> tela. O pipeline conta os campos da primeira linha de dados, nomeia os excedentes e
> registra quantos eram em `metadata`.

### Por que o abono de permanência

O abono de permanência é pago ao servidor que **já cumpriu todos os requisitos para se
aposentar voluntariamente e optou por permanecer na ativa**. Ele é, portanto, um marcador
direto e verificável de elegibilidade — sem necessidade de estimar idade, tempo de
contribuição ou regra de transição a partir de microdados pessoais.

O conjunto no dados.gov.br declara como política pública associada o *planejamento e
dimensionamento da força de trabalho no serviço público federal*. O IDSP-F é o reúso que
devolve o dado à finalidade que ele mesmo declara.

**O que o abono não é:** não é previsão de saída. Quem recebe abono decidiu ficar. O
indicador mede *exposição* — a parcela do quadro que pode sair a qualquer momento sem
qualquer impedimento legal — e não uma projeção de aposentadorias.

## 4. Territorialização

### O problema no eixo A

O campo `UF_EXERCICIO` do cadastro **não vem vazio quando falta: vem preenchido com `-1`**.
Cerca de 30 % das linhas do arquivo bruto trazem esse valor. Lido sem cuidado, `-1` é um
valor como outro qualquer e o vínculo simplesmente desaparece do mapa.

Por isso a UF é resolvida por uma cadeia de regras, da mais forte para a mais fraca, e o
método usado em cada vínculo é contado e publicado em
`metadata.fontes.f1.territorializacao`:

| Ordem | Regra | Exemplo |
|---|---|---|
| 1 | `UF_EXERCICIO`, quando diferente de `-1` | `SP` |
| 2 | sigla de UF no nome da unidade organizacional | `DELEGACIA EM MANAUS/AM` → AM |
| 3 | **nome do estado no nome do órgão** | `UNIVERSIDADE FEDERAL DO CEARA` → CE |
| 4 | nome de município no nome da unidade | `APS A TAUBATE` → SP |
| 5 | nome de município no nome do órgão | `FUNDACAO UNIVERSIDADE DE BRASILIA` → DF |

A regra 3 é a que mais recupera vínculos, porque universidades e institutos federais
carregam o estado no próprio nome e são justamente os órgãos com mais `-1`.

As regras 4 e 5 usam a lista de municípios do IBGE restrita aos **nomes inequívocos** —
os que existem em uma única unidade da federação — e com pelo menos seis caracteres, para
não casar por acidente dentro de nomes de unidade. A busca é por n-gramas de palavras, do
maior para o menor, de modo que `PRESIDENTE PRUDENTE` vence `PRUDENTE`.

O que sobra sem UF são, em sua maioria, unidades da administração central de ministérios,
que não têm território definido no dado. Esses vínculos **ficam fora do índice** e o total
é publicado no site e em `metadata.fontes.f1.cobertura_uf`. Nenhum deles é atribuído ao
Distrito Federal por conveniência.

**Eixo B (fragilidade)** usa a **UF da residência**, não a UF da UPAG de vinculação.

> **Decisão registrada.** A UPAG é a unidade pagadora e concentra-se nas sedes
> administrativas — o Distrito Federal apareceria inflado e os estados com órgãos
> descentralizados, esvaziados. A UF da residência acompanha o local de exercício em órgãos
> capilarizados. A divergência entre as duas territorializações é calculada e publicada
> como indicador de qualidade em `metadata.divergencia_upag_residencia`.

## 5. Casamento entre as bases

F1 e F2 não compartilham identificador de órgão. O casamento é feito **apenas por nome de
órgão**, em três etapas: correspondência exata sobre os nomes normalizados (sem acento,
maiúsculas, espaços colapsados); correspondência aproximada por `token_set_ratio` acima do
limiar configurado (92 por padrão); e, por fim, os casamentos manuais declarados em
`config/crosswalk_overrides.yaml`.

A **cobertura** — parcela dos servidores ativos que está em órgãos com casamento — é
calculada por lente e publicada. O pipeline recusa-se a gerar o índice se a cobertura na
lente núcleo cair abaixo de 80 %.

> Não há *record linkage* entre as bases. Nenhum registro individual de F1 é associado a
> nenhum registro individual de F2. A ligação é agregada, por órgão × UF.

### O eixo B é restrito; o eixo A não

O eixo A mede presença e usa **todos** os servidores do universo. O eixo B é uma razão
entre duas bases diferentes e só é honesto onde as duas bases falam da mesma população.
Dois filtros garantem isso, e ambos nasceram de resultados impossíveis nos dados reais:

1. **Só órgãos presentes nas duas bases.** A base de abono traz órgãos que o cadastro de
   servidores civis não tem — comandos militares, por exemplo. Sem o filtro, o numerador
   cobre gente que o denominador não conta.
2. **Só órgãos bem territorializados no cadastro** (cobertura de UF igual ou superior ao
   parâmetro `cobertura_uf_minima_org`, hoje 80 %). O abono tem UF de residência preenchida
   em 99,9 % dos registros; o cadastro tem buracos concentrados na administração central.
   Sem o filtro, o numerador é completo e o denominador não, e a fragilidade estoura.

Sem essas duas restrições, Rondônia aparecia com **110 % dos servidores já elegíveis** e o
Amapá com 141 % — o tipo de resultado que denuncia um erro de construção, não um achado.
O denominador efetivo do eixo B é publicado ao lado de cada percentual, na coluna
`n_ativos_base_b`, e o teste `test_fragilidade_entre_0_e_1` impede que o índice volte a ser
publicado com razões impossíveis.

> **Decisão registrada — governos de ex-territórios fora do universo.** Amapá, Roraima e
> Rondônia têm quadros de ex-território: pessoal pago pela União que serve funções
> estaduais. Eles aparecem na base de abono (mais de 6 mil registros) e praticamente não
> aparecem no cadastro de servidores civis, porque seu vínculo não é cargo efetivo do
> Executivo Federal. São excluídos das **duas** bases, por `orgaos_excluir` em
> `config/parametros.yaml`. Incluí-los faria os três estados parecerem ter presença federal
> muito acima da real.

## 6. Cálculo

Para cada UF *t* e cada lente *L*:

```
A(t) = ativos_L(t) / populacao(t) × 10.000
B(t) = abono_L(t) / ativos_L(t)
```

Os dois eixos são convertidos em **percentis nacionais por posição** entre as 27 unidades
(empates recebem a média das posições):

- `A_pct` — 0 é a menor presença do país, 100 a maior.
- `B_pct` — 0 é a menor fragilidade, 100 a maior.

### Classificação

Corte na **mediana nacional** de cada eixo (parâmetro `corte`, alternativa: `tercil`):

| | B baixo | B alto |
|---|---|---|
| **A baixo** | Deserto estável | **Deserto crítico** |
| **A alto** | Presença consolidada | Presença em risco |

### Gravidade

```
gravidade = ((100 − A_pct) + B_pct) / 2
```

Ordena as unidades dentro e entre quadrantes. É um **ordenador**, não uma medida com
unidade: por isso é sempre exibido ao lado dos dois números brutos que o produziram, e
nunca sozinho.

### Escolha do corte

Antes de congelar a versão, os histogramas de A e B são inspecionados. Se a distribuição
for degenerada a ponto de a mediana separar mal os grupos, o parâmetro `corte` passa a
`tercil` e a mudança é registrada aqui e em `metadata.parametros`. Os valores brutos
correspondentes aos cortes são publicados em `metadata.parametros.cortes`, de modo que
qualquer leitor possa reconstruir a classificação.

## 7. Supressão e agregação

- Nenhuma célula publicada com **n < 5** — exibida como `<5`.
- Quando a contagem de ativos ou de abonos de uma célula é suprimida, a razão derivada
  daquela célula também é omitida, para impedir reconstrução por divisão.
- Nada abaixo de UF é publicado na v1.0.
- O detalhe por grupo do núcleo (INSS, Receita, Institutos Federais, universidades, IBGE)
  segue a mesma regra e marca explicitamente as células suprimidas.

## 8. Limitações

1. **Cobertura do casamento.** Órgãos cujo nome não casa entre as bases ficam fora do eixo
   B. A cobertura é publicada; abaixo de 80 % no núcleo o índice não é gerado.
2. **Abono como proxy.** Mede elegibilidade, não intenção nem previsão de saída. Servidores
   elegíveis que não requereram o abono não aparecem — o indicador é conservador.
3. **Exercício ≠ atendimento.** A UF de exercício de um servidor não é necessariamente onde
   o serviço é entregue, sobretudo em órgãos com atendimento remoto ou itinerante.
4. **Residência ≠ exercício.** No eixo B, a residência é uma aproximação do local de
   trabalho. A divergência com a UPAG é publicada, mas nenhuma das duas é o exercício real.
5. **Presença ≠ capacidade.** O índice conta pessoas, não capacidade instalada, orçamento,
   terceirizados, produtividade ou qualidade do serviço.
6. **Recorte estadual esconde o interior.** Um estado com presença adequada na capital e
   vazia no interior aparece na média. O recorte municipal do núcleo é o próximo passo.
7. **Foto mensal.** Cada versão é um corte em um mês de referência, não uma série histórica.

## 9. Reprodutibilidade

Todo julgamento metodológico está em arquivos de configuração versionados, não no código:
recorte do universo, definição do núcleo, corte da matriz, limiar de supressão, limiar do
casamento aproximado e os casamentos manuais. Cada execução registra em `metadata.json` os
meses de referência, os SHA-256 dos arquivos brutos, as regras de filtro aplicadas, a
cobertura obtida e a versão do pipeline.

Os testes em `tests/` verificam que a soma dos agregados bate com o total filtrado, que os
percentis estão no intervalo válido, que as 27 unidades estão presentes nas duas lentes, que
nenhuma célula publicada viola a supressão, que nenhuma coluna de identificação aparece em
qualquer saída intermediária e que a malha está orientada como o d3 exige.

## 10. Roteiro

**v1.1** — recorte municipal para a lente núcleo (com supressão), calibração da conversão
entre elegibilidade e aposentadoria efetiva, terceirizados como camada de contexto,
boletins por UF em PDF e atualização mensal automatizada.
