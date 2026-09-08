# IDSP-F — Índice de Deserto de Serviço Público Federal

**Onde o Estado federal está mais ausente — e mais perto de sumir.**

O IDSP-F cruza duas bases abertas do Executivo Federal com a população do IBGE para
classificar cada unidade da federação em uma matriz de **presença × fragilidade**:

- **Presença (A)** — servidores civis ativos do Executivo Federal por 10 mil habitantes.
- **Fragilidade (B)** — parcela desses servidores que já cumpre os requisitos de
  aposentadoria e segue na ativa recebendo abono de permanência.

O quadrante **deserto crítico** (pouca presença + muita gente já elegível) indica onde
serviços como INSS, Institutos Federais, universidades federais, Receita Federal e IBGE
correm o maior risco de descontinuidade. É insumo direto para **planejamento e
dimensionamento da força de trabalho** — a política pública que o próprio conjunto
"Abono de Permanência" declara como finalidade no dados.gov.br.

Site: `https://<usuario>.github.io/idsp-f/` · Versão v1.0, recorte por UF.

---

## Como rodar em 5 comandos

```bash
pip install -r requirements.txt
# baixe os dois arquivos brutos para data/raw/ (ver "Fontes" abaixo)
bash scripts/run_all.sh
python -m pytest -q tests
python -m http.server 8000 --directory site
```

O pipeline não baixa F1 e F2 automaticamente: os portais exigem navegação. Coloque os
arquivos em `data/raw/` e o `run_all.sh` encontra o mês mais recente pelo nome. População
e malha territorial são baixadas da API do IBGE (com cache local).

Para ver o produto funcionando **sem** as bases reais, gere dados sintéticos:

```bash
FICTICIO=1 bash scripts/run_all.sh
```

O site passa a exibir uma tarja de aviso e `metadata.json` marca `"ficticio": true`.

### Variáveis úteis

| Variável | Efeito |
|---|---|
| `FICTICIO=1` | gera e usa bases sintéticas (`scripts/00_dados_ficticios.py`) |
| `F1=caminho.csv` `F2=caminho.csv` | aponta arquivos brutos específicos |
| `SEM_REDE=1` | não chama a API do IBGE; usa `data/raw/pop_uf.csv` e a malha em cache |
| `PYTHON=python3` | interpretador a usar |

## Fontes

| | Base | Origem | Onde baixar |
|---|---|---|---|
| **F1** | Cadastro de Servidores (`AAAAMM_Cadastro.csv`, fonte SIAPE) | CGU — Portal da Transparência; espelho MGI | [portaldatransparencia.gov.br](https://portaldatransparencia.gov.br/download-de-dados/servidores) · [dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/servidores-do-executivo-federal) |
| **F2** | Abono de Permanência (recurso mensal) | MGI — Gestão de Pessoas (Executivo Federal) | [dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/gastos-pessoal-abono-permanencia) |
| **F3** | Estimativas da população residente por UF | IBGE | API SIDRA, tabela 6579 (automático) |
| **F4** | Malha territorial das UFs | IBGE | API de malhas v3 (automático) |

Registre cada download em [`data/raw/MANIFEST.md`](data/raw/MANIFEST.md) com URL, data e
SHA-256. Os arquivos brutos não vão para o repositório.

## Pipeline

| Script | O que faz | Saída |
|---|---|---|
| `01_ingest_cadastro.py` | lê F1 com `usecols` e em blocos, filtra o universo, deduplica, agrega por UF × órgão | `presenca_uf_org.csv`, `diag_f1.txt` |
| `02_ingest_abono.py` | lê F2, reconhece cabeçalhos por regex, agrega por UF de residência × órgão | `abono_uf_org.csv`, `diag_f2.txt` |
| `03_populacao.py` | população do SIDRA; malha do IBGE reorientada para o d3 | `pop_uf.csv`, `data/geo/uf.geojson` |
| `04_crosswalk.py` | casa nomes de órgão entre F1 e F2 (exato → fuzzy → manual) e publica a cobertura | `crosswalk.csv`, `cobertura.json` |
| `05_indice.py` | calcula A, B, percentis, quadrantes, gravidade; aplica supressão | `idspf_uf.{csv,json}`, `metadata.json` |

`run_all.sh` **falha** se a cobertura do crosswalk na lente núcleo ficar abaixo de
`cobertura_minima_nucleo` (`config/parametros.yaml`). Quando isso acontecer, veja
`data/interim/crosswalk_pendentes.csv` — ele lista os órgãos sem casamento com os três
melhores candidatos — e preencha `config/crosswalk_overrides.yaml`.

Os diagnósticos `diag_f1.txt` e `diag_f2.txt` trazem os `value_counts` das colunas de
situação, vínculo e regime. São eles que sustentam as decisões de recorte do universo.

## Replicabilidade

Todo parâmetro de julgamento está em `config/`, não no código:

- `parametros.yaml` — corte da matriz (mediana ou tercil), limiar de supressão, regras de
  filtro do universo, limiar do casamento fuzzy.
- `nucleo.yaml` — quais órgãos compõem o "núcleo de serviços", por expressão regular.
- `crosswalk_overrides.yaml` — casamentos manuais de nomes de órgão.

Um estado ou município que queira replicar o índice sobre o seu próprio RPPS troca F1 e F2
pelas bases locais de servidores ativos e de abono/elegibilidade, ajusta `nucleo.yaml` para
os seus serviços finalísticos e roda o mesmo pipeline.

## Privacidade

Nome, CPF e matrícula **nunca são carregados** — a leitura usa `usecols` com uma lista
fechada de colunas. Não há ligação de registros entre as bases: o cruzamento é por
**órgão × UF**. Nenhuma célula com menos de 5 pessoas é publicada. Nada abaixo de UF é
publicado nesta versão. Detalhes em [PRIVACIDADE.md](PRIVACIDADE.md).

## Estrutura

```
config/     parâmetros, definição do núcleo, overrides do crosswalk
scripts/    00 (dados fictícios) · 01–05 (pipeline) · common.py · run_all.sh
tests/      invariantes do índice, da supressão e da malha
data/       raw (ignorado) · interim · processed · geo
site/       index.html · app.js · styles.css · data/ — publicado pelo GitHub Pages
docs/       textos de cadastro e checklist do edital
```

## Publicação

GitHub Pages servindo a pasta `/site` do branch `main`
(Settings → Pages → Source: Deploy from a branch → `main` / `/site`).

## Licenças

- **Código**: MIT ([LICENSE](LICENSE)).
- **Dados derivados e textos**: CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)).
- As bases originais seguem as licenças dos órgãos publicadores.

## Como citar

> IDSP-F — Índice de Deserto de Serviço Público Federal, v1.0.
> Disponível em `https://<usuario>.github.io/idsp-f/`.

## Limitações

O índice mede presença **federal**, não capacidade estatal total do território. Ficam fora
militares, Banco Central, Judiciário, Legislativo, estatais e servidores estaduais e
municipais. O abono de permanência é uma *proxy* de elegibilidade, não uma previsão de
saída: quem recebe abono decidiu ficar. As limitações completas e as decisões metodológicas
estão em [METODOLOGIA.md](METODOLOGIA.md) e reproduzidas na própria página.
