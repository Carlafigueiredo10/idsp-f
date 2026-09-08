# Manifesto dos arquivos brutos

Os arquivos brutos **não são versionados**. Este manifesto registra o que foi baixado, de
onde e quando, para que qualquer pessoa possa reproduzir a mesma execução sobre os mesmos
bytes.

Preencha uma linha por arquivo a cada rodada. O SHA-256 de cada arquivo efetivamente usado
também é gravado automaticamente em `data/processed/metadata.json`.

```bash
sha256sum data/raw/*.csv
```

| Arquivo | Fonte | URL | Baixado em | SHA-256 |
|---|---|---|---|---|
| `202512_Cadastro.csv` | CGU — Portal da Transparência (SIAPE), dentro de `202512_Servidores_SIAPE.zip` | https://portaldatransparencia.gov.br/download-de-dados/servidores/202512_Servidores_SIAPE | 2026-09-08 | `f98c7483a0437b04cb1ede0ac419945245ef3c138660387e3517ac22b9e05fb1` |
| `ABONOP_122025.csv` | MGI — dados.gov.br (repositório) | https://repositorio.dados.gov.br/segrt/ABONOP_122025.csv | 2026-09-08 | `f8da9059c071a53b5d65fd10da63f9b98e60e4613b6358d826ee7c2372b8a069` |
| População por UF, 2025 | IBGE — SIDRA tabela 6579 | https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/all/p/2025 | 2026-09-08 | baixado pela API a cada execução |
| Municípios (gazetteer) | IBGE — API de localidades | https://servicodados.ibge.gov.br/api/v1/localidades/municipios | 2026-09-08 | versionado em `data/geo/municipios.csv` |
| Malha das UFs | IBGE — API de malhas v3 | https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF | 2026-09-08 | versionado em `data/geo/uf_raw.geojson` |

## Observações

- O Portal da Transparência entrega o cadastro em ZIP mensal; extraia o
  `AAAAMM_Cadastro.csv` para `data/raw/`. O ZIP tem cerca de 83 MB e o CSV, 440 MB.
- O conjunto de Abono no dados.gov.br é uma casca: os arquivos ficam em
  `https://repositorio.dados.gov.br/segrt/ABONOP_MMAAAA.csv` — note que o mês vem
  **antes** do ano, ao contrário do cadastro. O portal marca o conjunto como
  desatualizado; confira sempre qual é o recurso mais recente.
- Anote o **mês de referência** de cada base. O pipeline o extrai do nome do arquivo
  (padrão `AAAAMM`) e o publica no site; se o nome não seguir esse padrão, renomeie.
- Os arquivos gerados em `data/raw/ficticio/` são sintéticos, criados por
  `scripts/00_dados_ficticios.py`, e não devem constar deste manifesto.
