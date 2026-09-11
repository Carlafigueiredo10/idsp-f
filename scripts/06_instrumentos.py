"""06 — Instrumentos disponíveis por situação diagnosticada.

Valida config/instrumentos.yaml e publica **apenas** os cartões marcados como
conferidos. Um cartão sem base normativa com URL, ou com `conferido: false`, não
chega ao site: é preferível não dizer nada a apontar uma norma errada.

    python scripts/06_instrumentos.py                    # valida e publica
    python scripts/06_instrumentos.py --conferir-links   # + testa as URLs na rede

O teste de links confirma que a URL responde. Ele **não** confirma que a norma está
vigente nem que ela diz o que o cartão afirma — norma revogada responde 200 igual.
Essa conferência é humana, e é ela que autoriza marcar `conferido: true`.

Saídas: data/processed/instrumentos.json, site/data/instrumentos.json
"""
from __future__ import annotations

import argparse

from common import PROCESSED, SITE_DATA, Lentes, Nucleo, load_yaml, log, write_json

QUADRANTES = {"deserto_critico", "deserto_estavel", "presenca_em_risco",
              "presenca_consolidada"}
OBRIGATORIOS = ("id", "titulo", "quadrantes", "grupos", "descricao", "base_normativa",
                "quem_decide")


def validar(itens, grupos_validos) -> list[str]:
    """Erros de estrutura. Vazio significa que o arquivo está bem formado — não que
    o conteúdo esteja certo, o que nenhum script consegue afirmar."""
    erros, vistos = [], set()
    for i, it in enumerate(itens):
        onde = f"instrumento #{i + 1} ({it.get('id', 'sem id')})"
        for campo in OBRIGATORIOS:
            if not it.get(campo):
                erros.append(f"{onde}: falta `{campo}`")
        if it.get("id") in vistos:
            erros.append(f"{onde}: id repetido")
        vistos.add(it.get("id"))
        q = it.get("quadrantes")
        if q != "todos" and isinstance(q, list) and not set(q) <= QUADRANTES:
            erros.append(f"{onde}: quadrante inexistente {set(q) - QUADRANTES}")
        g = it.get("grupos")
        if g != "todos" and isinstance(g, list) and not set(g) <= grupos_validos:
            erros.append(f"{onde}: grupo inexistente {set(g) - grupos_validos}")
        for b in it.get("base_normativa") or []:
            if not b.get("url"):
                erros.append(f"{onde}: base normativa '{b.get('titulo', '?')}' sem URL")
    return erros


def conferir_links(itens) -> list[str]:
    import requests

    problemas = []
    for it in itens:
        for b in it.get("base_normativa") or []:
            url = b.get("url") or ""
            if not url:
                continue
            try:
                r = requests.get(url, timeout=30, allow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
                estado = "ok" if r.status_code < 400 else f"HTTP {r.status_code}"
            except Exception as e:  # noqa: BLE001
                estado = f"falhou ({type(e).__name__})"
            log(f"  [{estado:>16}] {it['id']} · {url[:70]}")
            if estado != "ok":
                problemas.append(f"{it['id']}: {url} -> {estado}")
    return problemas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conferir-links", action="store_true",
                    help="testa se as URLs da base normativa respondem")
    ap.add_argument("--estrito", action="store_true",
                    help="falha se houver erro de estrutura ou link quebrado")
    args = ap.parse_args()

    itens = load_yaml("instrumentos.yaml").get("instrumentos") or []
    grupos_validos = set(Nucleo().ids)
    erros = validar(itens, grupos_validos)
    for e in erros:
        log(f"AVISO: {e}")

    if args.conferir_links:
        problemas = conferir_links(itens)
        erros += problemas

    publicados = [it for it in itens
                  if it.get("conferido") and all((b.get("url") for b in it["base_normativa"]))]
    nao_conferidos = [it["id"] for it in itens if not it.get("conferido")]

    saida = dict(
        aviso=("Instrumentos já existentes no ordenamento, com a norma que os cria e a "
               "instância com competência para acioná-los. Não são recomendações: o "
               "IDSP-F não decide lotação, concurso ou cooperação, e não fala por "
               "nenhum órgão."),
        instrumentos=[dict(id=it["id"], titulo=it["titulo"],
                           quadrantes=it["quadrantes"], grupos=it["grupos"],
                           descricao=" ".join(str(it["descricao"]).split()),
                           base_normativa=it["base_normativa"],
                           quem_decide=it["quem_decide"]) for it in publicados],
        total_no_config=len(itens), nao_conferidos=nao_conferidos)

    write_json(PROCESSED / "instrumentos.json", saida)
    write_json(SITE_DATA / "instrumentos.json", saida)
    log(f"Instrumentos: {len(publicados)} publicados de {len(itens)} no config"
        + (f"; aguardando conferência: {', '.join(nao_conferidos)}" if nao_conferidos else ""))
    if erros and args.estrito:
        raise SystemExit(f"{len(erros)} problema(s) e --estrito ligado")


if __name__ == "__main__":
    main()
