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
| `AAAAMM_Cadastro.csv` | CGU — Portal da Transparência (SIAPE) | https://portaldatransparencia.gov.br/download-de-dados/servidores | | |
| `AAAAMM_AbonoPermanencia.csv` | MGI — dados.gov.br | https://dados.gov.br/dados/conjuntos-dados/gastos-pessoal-abono-permanencia | | |
| `pop_uf.csv` (só se usar `SEM_REDE=1`) | IBGE — SIDRA tabela 6579 | https://sidra.ibge.gov.br/tabela/6579 | | |

## Observações

- O Portal da Transparência entrega o cadastro em ZIP mensal; extraia o
  `AAAAMM_Cadastro.csv` para `data/raw/`.
- Anote o **mês de referência** de cada base. O pipeline o extrai do nome do arquivo
  (padrão `AAAAMM`) e o publica no site; se o nome não seguir esse padrão, renomeie.
- Os arquivos gerados em `data/raw/ficticio/` são sintéticos, criados por
  `scripts/00_dados_ficticios.py`, e não devem constar deste manifesto.
