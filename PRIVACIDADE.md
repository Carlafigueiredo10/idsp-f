# Privacidade por construção — IDSP-F

O IDSP-F trata dados publicados em portais de transparência, cuja divulgação já é
determinada por lei. Ainda assim, o projeto adota como princípio que **transparência
pública não autoriza reprocessamento identificável**: o índice precisa de contagens, não de
pessoas. As regras abaixo são implementadas no pipeline e verificadas por testes
automatizados.

## 1. Colunas de identificação nunca são carregadas

A leitura dos arquivos brutos usa uma **lista fechada de colunas** (`usecols`). Nome, CPF,
matrícula, valores de remuneração e datas pessoais não são lidos — não chegam a existir na
memória do processo, muito menos em disco.

No script de ingestão do cadastro, essas colunas estão explicitamente vetadas
(`PROIBIDOS`), de modo que uma mudança futura no layout da fonte não as introduza por
acidente. No script do abono, o reconhecimento de cabeçalhos por expressão regular descarta
qualquer coluna que corresponda a nome, CPF, matrícula, valor, remuneração, data de
nascimento, sexo ou e-mail.

**Verificação:** `tests/test_pipeline.py::test_nenhuma_coluna_de_identificacao_no_interim`
percorre todas as saídas intermediárias e falha se qualquer uma contiver coluna de
identificação.

## 2. O identificador só existe em memória, para deduplicar

O campo `ID_SERVIDOR_PORTAL` — um identificador do portal, não o CPF — é usado apenas para
contar cada servidor uma vez quando ele aparece em mais de um vínculo. O conjunto de
identificadores vistos vive na memória do processo e é descartado logo após a agregação.
Nenhum identificador é escrito em qualquer arquivo de saída.

## 3. Sem ligação de registros entre as bases

Não há *record linkage* entre o cadastro de servidores e o abono de permanência. As duas
bases são agregadas separadamente e ligadas **por órgão × UF**, já em forma de contagem.
Nenhum registro individual de uma base é associado a nenhum registro individual da outra.

## 4. Supressão de células pequenas

Nenhuma célula publicada com **menos de 5 pessoas** — exibida como `<5`, incluindo o
detalhamento por grupo do núcleo de serviços.

Quando uma contagem é suprimida, **a razão derivada dela também é omitida**. Sem essa
segunda regra, publicar "3 de 10" como 30 % permitiria reconstruir o numerador suprimido.

**Verificação:** `tests/test_pipeline.py::test_supressao_menor_que_5`.

## 5. Nenhuma saída abaixo de UF

A versão 1.0 publica exclusivamente agregados por unidade da federação. O recorte municipal
previsto para a v1.1 aplicará a mesma supressão e ficará restrito à lente do núcleo de
serviços, justamente porque a granularidade fina aumenta o risco de singularização.

## 6. Dados brutos ficam fora do repositório

`data/raw/` é ignorado pelo controle de versão. O que se versiona é o **manifesto**:
URL de origem, data do download e SHA-256 de cada arquivo. Qualquer pessoa pode baixar as
mesmas bases e conferir que trabalhou sobre os mesmos bytes, sem que o projeto redistribua
microdados.

## 7. O site não coleta nada

Página estática, sem backend, sem login, sem cookies, sem analytics, sem formulários e sem
chamadas a serviços de terceiros além da biblioteca de visualização servida por CDN. Nenhum
dado de quem visita é coletado, armazenado ou transmitido.

## 8. Base legal e finalidade

O tratamento se apoia no uso de dados já publicados por determinação legal de transparência
ativa, com finalidade específica e declarada: **planejamento e dimensionamento da força de
trabalho** — a mesma finalidade que o conjunto "Abono de Permanência" declara no
dados.gov.br. O produto publica apenas estatísticas agregadas, sem qualquer decisão
automatizada sobre pessoas e sem qualquer avaliação individual de servidores.

O índice descreve **territórios e órgãos**, nunca pessoas. Nenhum resultado do IDSP-F pode
ser usado para identificar, avaliar, classificar ou tomar decisão sobre qualquer servidor
individualmente.

## Resumo das regras verificadas por teste

| Regra | Teste |
|---|---|
| Colunas de identificação ausentes de toda saída | `test_nenhuma_coluna_de_identificacao_no_interim` |
| Nenhuma célula publicada com n < 5 | `test_supressao_menor_que_5` |
| Razões derivadas de células suprimidas são omitidas | `test_supressao_menor_que_5` |
| Cobertura territorial completa e sem vazamento de granularidade | `test_27_ufs_por_lente` |
