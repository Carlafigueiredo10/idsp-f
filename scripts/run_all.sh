#!/usr/bin/env bash
# Executa o pipeline completo 01–05 e os testes.
# Uso:  bash scripts/run_all.sh                 (dados reais em data/raw/)
#       FICTICIO=1 bash scripts/run_all.sh      (gera e usa dados fictícios)
# A camada de instrumentos (06) publica só os cartões conferidos; se não houver
# nenhum, ela grava uma lista vazia e o site simplesmente não mostra a seção.
# Falha se a cobertura do crosswalk na lente núcleo ficar abaixo de config/parametros.yaml.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python}

# 03 vem primeiro: baixa o gazetteer de municípios, que a ingestão do cadastro usa
# para recuperar a UF dos vínculos em que o campo vem como -1.
$PY scripts/03_populacao.py ${SEM_REDE:+--sem-rede} ${ANO_POP:+--ano "$ANO_POP"}

FLAG=""
if [[ "${FICTICIO:-0}" == "1" ]]; then
  $PY scripts/00_dados_ficticios.py
  F1=$(ls data/raw/ficticio/*_Cadastro.csv | tail -1)
  F2=$(ls data/raw/ficticio/*bono*.csv | tail -1)
  FLAG="--ficticio"
fi
$PY scripts/01_ingest_cadastro.py ${F1:+--arquivo "$F1"}
$PY scripts/02_ingest_abono.py ${F2:+--arquivo "$F2"}
$PY scripts/04_crosswalk.py
$PY scripts/05_indice.py $FLAG
$PY scripts/06_instrumentos.py

$PY - <<'PYEOF'
import json, yaml
cob = json.load(open("data/interim/cobertura.json"))["nucleo"]
lim = yaml.safe_load(open("config/parametros.yaml"))["cobertura_minima_nucleo"]
print(f"cobertura crosswalk (núcleo) = {cob:.1%}; mínimo = {lim:.0%}")
raise SystemExit(0 if cob >= lim else f"FALHA: cobertura {cob:.1%} < {lim:.0%}. Preencha config/crosswalk_overrides.yaml (ver data/interim/crosswalk_pendentes.csv).")
PYEOF

$PY -m pytest -q tests
echo "run_all: OK"
