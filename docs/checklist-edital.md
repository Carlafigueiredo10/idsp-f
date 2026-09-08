# Checklist de admissibilidade e mapeamento com o edital

Concurso de Reúso de Dados Abertos — CGU, Edital nº 46/2026.

> Conferir os números dos itens contra o PDF do edital antes de enviar. As exigências
> abaixo seguem a leitura registrada na especificação do projeto; se algum item divergir,
> vale o edital.

---

## Admissibilidade — fazer nesta ordem

- [ ] **Etapa 2 primeiro: cadastrar o caso de reúso** e enviar para homologação, com a URL
      do GitHub Pages e as URLs exatas dos conjuntos de dados usados. O caso precisa estar
      submetido antes de referenciá-lo no formulário.
- [ ] **Etapa 1: preencher o formulário de inscrição** dentro do prazo, com anexos.
- [ ] Guardar **comprovantes** de ambas as etapas: protocolo, print da tela de confirmação
      e e-mail de recebimento.
- [ ] Conferir que o site está **no ar e público** na URL declarada, e que ela não mudará.
- [ ] Conferir que o repositório está **público**, com licença e README.
- [ ] Concluir a inscrição **um dia antes do prazo** — o desempate por data de inscrição
      favorece quem enviou primeiro.

## Requisitos de dados

- [ ] Pelo menos **um conjunto catalogado no dados.gov.br** — o projeto usa dois (Abono de
      Permanência e Servidores do Executivo Federal), mais o IBGE.
- [ ] Conjuntos **identificados no produto**: a tela "Fontes e download" lista cada base com
      órgão, link, mês de referência e SHA-256 do arquivo usado.
- [ ] URLs dos conjuntos **copiadas do portal no dia do cadastro** (o padrão de URL do
      dados.gov.br mudou; slugs antigos podem redirecionar ou quebrar).

## Mapeamento com os critérios de julgamento

| Critério (peso) | Como o produto atende | Onde verificar |
|---|---|---|
| **Apresentação e usabilidade** (1) | Mapa coroplético, matriz 2×2 e painel por UF em página única; mobile-first, testado a 360 px; qualquer estado alcançável em menos de 30 s; contraste AA e nenhuma informação transmitida só por cor (cada classe tem cor **e** textura) | site, seções Mapa e Painel |
| **Inovação e originalidade** (1) | Transplante do conceito de deserto para capacidade estatal federal; índice bidimensional presença × risco de evasão; lente "núcleo de serviços" | `METODOLOGIA.md` §1–2 |
| **Relevância e impacto** (2) | Dimensionamento da força de trabalho — a finalidade declarada pela própria fonte no dados.gov.br; insumo para concurso, lotação e remoção | `docs/textos-cadastro.md` |
| **Benefício à sociedade** (2) | Mostra onde a agência do INSS, o campus do instituto federal ou a universidade correm risco de ficar sem gente; controle social com número rastreável à fonte | site, Painel da UF e Fontes |
| **Replicabilidade** (1) | Código MIT, dados CC BY 4.0, pipeline em cinco comandos, parâmetros de julgamento em `config/`, testes automatizados; adaptável a RPPS estaduais e municipais | `README.md`, `config/` |

## Definição de pronto — v1.0

- [x] `run_all.sh` roda do zero e falha se a cobertura do crosswalk cair abaixo do mínimo
- [x] 27 UFs com A, B, percentis, classe e gravidade nas duas lentes
- [x] Nenhuma célula publicada com n < 5; nenhuma coluna de identificação lida
- [x] Testes automatizados cobrindo índice, supressão, privacidade e malha
- [x] Site com mapa, matriz, painel por UF, metodologia e fontes; peso total abaixo de 400 KB
- [x] Painel de qualquer UF em até 30 s no celular; layout íntegro a 360 px
- [x] Impressão do painel gera boletim de uma página
- [x] README com fontes, mês de referência, como reproduzir e como citar
- [x] Licenças no repositório (MIT para código, CC BY 4.0 para dados e textos)
- [x] **Pipeline rodado com as bases reais** — cadastro de servidores e abono de
      permanência, ambos de dezembro de 2025, com população IBGE do mesmo ano
- [ ] Repositório público no GitHub com Pages ativo na pasta `/site`
- [ ] Caso de reúso enviado para homologação e formulário submetido, com comprovantes

## Verificações já feitas sobre os dados reais

- [x] `diag_f1.txt` lido: 51 valores distintos de situação de vínculo, universo fechado em
      cargo efetivo em exercício. Celetistas, temporários, substitutos, comissionados sem
      vínculo e sigilosos (Polícia Federal e PRF) ficaram fora
- [x] `diag_f2.txt` lido: UF de residência preenchida em 99,9 % dos registros, bem acima
      dos 90 % exigidos. Divergência entre UPAG e residência: 15.2%
- [x] Cobertura do crosswalk: 92.1% no núcleo e 85.5% no total, acima do mínimo de 80 %
- [x] Distribuições de A e B inspecionadas; a mediana separa bem os quatro quadrantes
      (9 a 10 UFs nas classes extremas), então o corte segue na mediana
- [x] `MANIFEST.md` preenchido com URL, data e SHA-256 dos dois arquivos
- [x] `metadata.json` com `"ficticio": false` e sem tarja no site
- [x] Testado a 360 px de largura: sem transbordo, 27 estados no mapa, boletim em uma página

## Antes de submeter

- [ ] Substituir `<usuario>` pela conta real do GitHub em `README.md`, `LICENSE-DATA`,
      `docs/textos-cadastro.md` e na constante `REPO` de `site/app.js`
- [ ] Testar no celular de verdade: abrir a URL, achar o próprio estado, imprimir o boletim
- [ ] Reler as decisões metodológicas em `METODOLOGIA.md` e confirmar que concorda com elas,
      em especial: grupo da Receita como Ministério da Fazenda inteiro, exclusão dos
      governos de ex-territórios e restrição do eixo B a órgãos comparáveis
- [ ] Conferir se o conjunto de Abono foi atualizado no dados.gov.br; se sim, rodar de novo
      com o mês mais recente nas duas bases
