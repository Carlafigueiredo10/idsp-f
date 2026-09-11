"""07 — Série histórica do eixo A (presença), 2014 a 2025.

Baixa o cadastro de dezembro de cada ano, agrega por UF e grupo do núcleo com **as
mesmas regras do índice publicado**, e descarta o arquivo bruto antes de passar ao
ano seguinte. A foto vira filme: quanto de presença federal cada estado ganhou ou
perdeu em uma década.

    python scripts/07_serie_historica.py                  # 2014..2025, dezembro
    python scripts/07_serie_historica.py --anos 2019 2025
    python scripts/07_serie_historica.py --manter-brutos  # não apaga os CSVs

Por que só o eixo A: o abono só está publicado a partir de 2017 e com lacunas, então
uma série de fragilidade teria buracos que o leitor confundiria com queda real. A
presença, essa sim, tem base comparável desde julho de 2014, quando o campo
`UF_EXERCICIO` passou a existir para civis.

As regras de filtro, os grupos e a cadeia de territorialização vêm de `config/`, os
mesmos do índice — se elas mudarem, a série inteira precisa ser regerada, ou a
tendência vira artefato de método. `metadata_serie.json` registra a versão usada.

Saídas: data/processed/serie_uf.{csv,json} e site/data/serie_uf.json
"""
from __future__ import annotations

import argparse
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd
import requests

from common import (INTERIM, PROCESSED, RAW, SITE_DATA, Nucleo, Territorializador,
                    any_match, cabecalho_alinhado, compile_list, detectar_sep_encoding,
                    log, norm, parametros, write_json)

URL = "https://portaldatransparencia.gov.br/download-de-dados/servidores/{mes}_Servidores_SIAPE"
SIDRA = "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/all/p/all"
CAMPOS = {"ID_SERVIDOR_PORTAL": "id", "ORG_EXERCICIO": "org", "ORGSUP_EXERCICIO": "orgsup",
          "UORG_EXERCICIO": "uorg", "UF_EXERCICIO": "uf", "TIPO_VINCULO": "tipo",
          "SITUACAO_VINCULO": "situacao", "REGIME_JURIDICO": "regime",
          "DESCRICAO_CARGO": "cargo"}


def baixar(mes: str) -> Path | None:
    """Baixa e extrai o cadastro do mês; devolve o CSV ou None se indisponível."""
    csv = RAW / f"{mes}_Cadastro.csv"
    if csv.exists():
        return csv
    zp = RAW / f"{mes}_Servidores_SIAPE.zip"
    if not zp.exists():
        r = requests.get(URL.format(mes=mes), timeout=900, stream=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code >= 400:
            log(f"  {mes}: indisponível (HTTP {r.status_code})")
            return None
        with open(zp, "wb") as f:
            for bloco in r.iter_content(1 << 20):
                f.write(bloco)
    try:
        with zipfile.ZipFile(zp) as z:
            nome = next(n for n in z.namelist() if n.upper().endswith("CADASTRO.CSV"))
            z.extract(nome, RAW)
            extraido = RAW / nome
            if extraido != csv:
                extraido.rename(csv)
    except (zipfile.BadZipFile, StopIteration) as e:
        log(f"  {mes}: ZIP inválido ({type(e).__name__})")
        return None
    finally:
        zp.unlink(missing_ok=True)
    return csv


def agregar(path: Path, p: dict, nucleo: Nucleo, terr: Territorializador) -> pd.DataFrame:
    """Conta ativos por UF e grupo, com as regras do índice publicado."""
    f = p["filtro_f1"]
    sit_in, sit_out = compile_list(f.get("situacao_incluir")), compile_list(f.get("situacao_excluir"))
    tipo_out, reg_out = compile_list(f.get("tipo_vinculo_excluir")), compile_list(f.get("regime_excluir"))
    cargo_out, org_out = compile_list(f.get("cargo_excluir")), compile_list(p.get("orgaos_excluir"))

    sep, enc = detectar_sep_encoding(path)
    header, _ = cabecalho_alinhado(path, sep, enc)
    mapa = {c: CAMPOS[norm(c).replace(" ", "_")] for c in header
            if norm(c).replace(" ", "_") in CAMPOS}
    if "uf" not in mapa.values() and "uorg" not in mapa.values():
        raise SystemExit(f"{path.name}: sem UF_EXERCICIO nem UORG_EXERCICIO")

    vistos: set = set()
    agg: Counter = Counter()
    for ch in pd.read_csv(path, sep=sep, encoding=enc, header=0, names=header,
                          index_col=False, usecols=list(mapa), dtype=str,
                          chunksize=200_000, na_filter=False):
        ch = ch.rename(columns=mapa)
        for c in ("situacao", "tipo", "regime", "cargo", "org", "orgsup", "uorg", "uf"):
            if c not in ch:
                ch[c] = ""
        for c in ("situacao", "tipo", "regime", "cargo"):
            ch[c] = ch[c].map(norm)
        keep = ch["situacao"].map(lambda s: any_match(sit_in, s) and not any_match(sit_out, s))
        keep &= ~ch["tipo"].map(lambda s: any_match(tipo_out, s))
        keep &= ~ch["regime"].map(lambda s: any_match(reg_out, s))
        keep &= ~ch["cargo"].map(lambda s: any_match(cargo_out, s))
        if org_out:
            keep &= ~ch["org"].map(lambda s: any_match(org_out, norm(s)))
            keep &= ~ch["orgsup"].map(lambda s: any_match(org_out, norm(s)))
        ch = ch[keep]
        if "id" in ch:                       # uma pessoa conta uma vez
            novo = []
            for i in ch["id"].tolist():
                novo.append(i not in vistos)
                vistos.add(i)
            ch = ch[novo]
        for u, uo, o, s in zip(ch["uf"], ch["uorg"], ch["org"], ch["orgsup"]):
            sigla, _ = terr.resolver(u, uo, o)
            agg[(sigla, nucleo.classificar(o, s, uo))] += 1
    vistos.clear()
    return pd.DataFrame([dict(uf=k[0], grupo_nucleo=k[1], n_ativos=v) for k, v in agg.items()])


def populacao() -> pd.DataFrame:
    d = requests.get(SIDRA, timeout=120).json()[1:]
    return pd.DataFrame([dict(cod_ibge=x["D1C"], ano=int(x["D3C"]), populacao=int(x["V"]))
                         for x in d if x["V"] not in (None, "-", "...")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="*", type=int,
                    default=list(range(2014, 2026)))
    ap.add_argument("--mes", default="12", help="mês de referência de cada ano")
    ap.add_argument("--manter-brutos", action="store_true")
    args = ap.parse_args()

    p, nucleo, terr = parametros(), Nucleo(), Territorializador()
    if not terr.gaz:
        log("AVISO: gazetteer ausente; rode 03_populacao.py antes")

    partes = []
    parcial = INTERIM / "serie_parcial.csv"
    if parcial.exists():                     # retomar de onde parou
        partes.append(pd.read_csv(parcial, dtype={"uf": str, "grupo_nucleo": str}))
        feitos = set(partes[0].ano.unique())
        log(f"Retomando; anos já processados: {sorted(feitos)}")
    else:
        feitos = set()

    for ano in args.anos:
        if ano in feitos:
            continue
        mes = f"{ano}{args.mes}"
        log(f"[{mes}] baixando…")
        csv = baixar(mes)
        if csv is None:
            continue
        log(f"[{mes}] agregando {csv.stat().st_size / 1e6:.0f} MB…")
        df = agregar(csv, p, nucleo, terr)
        df["ano"] = ano
        partes.append(df)
        pd.concat(partes, ignore_index=True).to_csv(parcial, index=False, encoding="utf-8")
        if not args.manter_brutos and csv.name != "202512_Cadastro.csv":
            csv.unlink(missing_ok=True)
        log(f"[{mes}] ok: {int(df.n_ativos.sum()):,} ativos, {df.uf.nunique()} UFs")

    if not partes:
        raise SystemExit("nenhum ano processado")
    serie = pd.concat(partes, ignore_index=True)
    serie = serie[serie.uf != ""]

    pop = populacao()
    from common import COD_TO_SIGLA
    pop["uf"] = pop.cod_ibge.map(COD_TO_SIGLA)
    tot = serie.groupby(["ano", "uf"], as_index=False).n_ativos.sum()
    tot = tot.merge(pop[["ano", "uf", "populacao"]], on=["ano", "uf"], how="left")
    tot["A_raw"] = (tot.n_ativos / tot.populacao * 10_000).round(2)
    tot["lente"] = "total"

    nuc = serie[serie.grupo_nucleo != ""].groupby(["ano", "uf"], as_index=False).n_ativos.sum()
    nuc = nuc.merge(pop[["ano", "uf", "populacao"]], on=["ano", "uf"], how="left")
    nuc["A_raw"] = (nuc.n_ativos / nuc.populacao * 10_000).round(2)
    nuc["lente"] = "nucleo"

    out = pd.concat([tot, nuc], ignore_index=True).sort_values(["lente", "uf", "ano"])
    out.to_csv(PROCESSED / "serie_uf.csv", index=False, encoding="utf-8")

    por_lente: dict = {}
    for lente, g in out.groupby("lente"):
        por_lente[lente] = {uf: [dict(ano=int(r.ano), a=None if pd.isna(r.A_raw) else float(r.A_raw),
                                      n=int(r.n_ativos)) for r in gg.itertuples()]
                            for uf, gg in g.groupby("uf")}
    meta = dict(anos=sorted(out.ano.unique().tolist()), mes_referencia=args.mes,
                versao_pipeline=p.get("versao_pipeline"),
                nota=("Série do eixo A (presença). As regras de filtro, os grupos e a "
                      "territorialização são as mesmas do índice publicado; mudá-las exige "
                      "regerar a série inteira, sob pena de a tendência virar artefato."))
    write_json(PROCESSED / "serie_uf.json", dict(meta=meta, series=por_lente))
    write_json(SITE_DATA / "serie_uf.json", dict(meta=meta, series=por_lente))

    log(f"Série pronta: {out.ano.min()}–{out.ano.max()}, {out.uf.nunique()} UFs")
    for lente in por_lente:
        g = out[out.lente == lente]
        a0, a1 = g.ano.min(), g.ano.max()
        ini = g[g.ano == a0].set_index("uf").A_raw
        fim = g[g.ano == a1].set_index("uf").A_raw
        var = ((fim - ini) / ini * 100).dropna().sort_values()
        log(f"  [{lente}] {a0}->{a1} maiores quedas: " +
            ", ".join(f"{u} {v:+.0f}%" for u, v in var.head(5).items()))


if __name__ == "__main__":
    main()
