#!/usr/bin/env bash
# Baixa as duas bases brutas para data/raw/.
#
#   bash scripts/00_baixar_fontes.sh 202512 122025
#                                    ^F1     ^F2
#
# Repare na inversão: o cadastro nomeia os arquivos como AAAAMM e o abono como MMAAAA.
# Sem argumentos, procura para trás o mês mais recente de cada base.
#
# O conjunto de abono no dados.gov.br costuma estar meses atrás do cadastro, e é ele
# que fixa o mês do índice: a fragilidade é uma razão entre as duas bases e as duas
# precisam ser do mesmo mês.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw
UA="Mozilla/5.0"
F1_URL="https://portaldatransparencia.gov.br/download-de-dados/servidores"
F2_URL="https://repositorio.dados.gov.br/segrt"

existe() { curl -sIL -m 30 -A "$UA" "$1" 2>/dev/null | grep -qE "^HTTP/[0-9.]+ 200"; }

descobrir_f1() {
  for i in $(seq 0 18); do
    m=$(date -d "-$i month" +%Y%m 2>/dev/null) || m=""
    [ -n "$m" ] && existe "$F1_URL/${m}_Servidores_SIAPE" && { echo "$m"; return; }
  done
  return 1
}
descobrir_f2() {
  for i in $(seq 0 24); do
    m=$(date -d "-$i month" +%m%Y 2>/dev/null) || m=""
    [ -n "$m" ] && existe "$F2_URL/ABONOP_${m}.csv" && { echo "$m"; return; }
  done
  return 1
}

F1=${1:-$(descobrir_f1)} || { echo "Não achei nenhum mês do cadastro"; exit 1; }
F2=${2:-$(descobrir_f2)} || { echo "Não achei nenhum mês do abono"; exit 1; }
echo "cadastro=$F1  abono=$F2"
if [ -z "${2:-}" ] && [ "${F1:0:4}${F1:4:2}" != "${F2:2:4}${F2:0:2}" ]; then
  echo "AVISO: meses diferentes. O índice deve usar o mesmo mês nas duas bases."
  echo "       Rode:  bash scripts/00_baixar_fontes.sh ${F2:2:4}${F2:0:2} $F2"
fi

if [ ! -f "data/raw/${F1}_Cadastro.csv" ]; then
  echo "baixando cadastro ${F1} (~83 MB compactado, ~440 MB depois)…"
  curl -# -L -A "$UA" -o "data/raw/${F1}_Servidores_SIAPE.zip" "$F1_URL/${F1}_Servidores_SIAPE"
  python -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extract(sys.argv[2],'data/raw/')" \
    "data/raw/${F1}_Servidores_SIAPE.zip" "${F1}_Cadastro.csv"
fi
if [ ! -f "data/raw/ABONOP_${F2}.csv" ]; then
  echo "baixando abono ${F2} (~23 MB)…"
  curl -# -L -A "$UA" -o "data/raw/ABONOP_${F2}.csv" "$F2_URL/ABONOP_${F2}.csv"
fi

echo
echo "arquivos em data/raw/:"
ls -la data/raw/*.csv
echo
echo "SHA-256 (copie para data/raw/MANIFEST.md):"
sha256sum "data/raw/${F1}_Cadastro.csv" "data/raw/ABONOP_${F2}.csv"
