"""02 — Abono de Permanência (MGI, dados.gov.br).

Lê o recurso mensal, reconhece cabeçalhos por regex (o layout publicado varia),
carrega só as colunas necessárias (nome/CPF/matrícula/valor nunca entram),
filtra situações ativas e agrega por UF de residência x UF da UPAG x órgão x grupo.

Saídas: data/interim/abono_uf_org.csv, data/interim/diag_f2.txt, data/interim/meta_f2.json
"""
from __future__ import annotations

import argparse
import re
from collections import Counter

import pandas as pd

from common import (INTERIM, Nucleo, any_match, cabecalho_alinhado, compile_list,
                    detectar_sep_encoding, encontrar_arquivo, log, mes_ref_de_nome, norm,
                    norm_uf, parametros, sha256_file, write_json)

# ordem importa: o primeiro padrão que casar vence
PADROES = [
    ("org_atuacao", r"ORG.*ATUA|ORGAO.*EXERC|^ORGAO$|DENOMINACAO.*ORGAO"),
    ("uf_upag", r"UF.*UPAG|UPAG.*UF"),
    ("uf_residencia", r"UF.*RESID|RESID.*UF"),
    ("cidade_residencia", r"(CIDADE|MUNIC).*RESID"),
    ("uorg", r"UNIDADE ORG|UORG|DENOMINACAO.*UNIDADE"),
    ("situacao", r"SITUA"),
    ("anomes_inicio", r"INIC"),
    ("cargo", r"CARGO"),
    ("escolaridade", r"ESCOLAR"),
    ("tempo_servico", r"ANOS|TEMPO"),
]
PROIBIDOS = re.compile(r"NOME|CPF|MATRIC|VALOR|REMUNER|SALARIO|NASC|SEXO|EMAIL")


def mapear_cabecalho(header):
    mapa, usados = {}, set()
    for col in header:
        n = norm(col)
        if PROIBIDOS.search(n):
            continue
        for canon, pat in PADROES:
            if canon not in usados and re.search(pat, n):
                mapa[col] = canon
                usados.add(canon)
                break
    return mapa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arquivo", help="CSV do Abono de Permanência")
    ap.add_argument("--chunksize", type=int, default=200_000)
    args = ap.parse_args()

    path = encontrar_arquivo(["*bono*.csv", "*BONO*.csv"], args.arquivo)
    sep, enc = detectar_sep_encoding(path)
    header, extras = cabecalho_alinhado(path, sep, enc)
    mapa = mapear_cabecalho(header)
    log(f"F2: {path.name} sep={sep!r} enc={enc} colunas={len(header)} extras={extras}")
    if extras:
        log(f"AVISO: {extras} campo(s) a mais por linha que no cabeçalho; nomeados _extra_*")
    if "org_atuacao" not in mapa.values():
        raise SystemExit("Coluna de órgão de atuação não reconhecida — ajuste PADROES ou o cabeçalho.")
    if "uf_residencia" not in mapa.values() and "uf_upag" not in mapa.values():
        raise SystemExit("Nenhuma coluna de UF reconhecida.")

    p = parametros()
    sit_in = compile_list(p.get("filtro_f2", {}).get("situacao_incluir"))
    org_out = compile_list(p.get("orgaos_excluir"))
    nucleo = Nucleo()
    agg = Counter()
    diag = {k: Counter() for k in ("situacao", "uf_residencia", "uf_upag", "grupo", "anomes_inicio")}
    tot = mantidos = 0
    residencia_vazia = 0

    reader = pd.read_csv(path, sep=sep, encoding=enc, header=0, names=header,
                         index_col=False, usecols=list(mapa), dtype=str,
                         chunksize=args.chunksize, na_filter=False)
    for chunk in reader:
        chunk = chunk.rename(columns=mapa)
        tot += len(chunk)
        for c in ("uf_residencia", "uf_upag", "situacao", "uorg", "anomes_inicio"):
            if c not in chunk:
                chunk[c] = ""
        chunk["situacao"] = chunk["situacao"].map(norm)
        diag["situacao"].update(chunk["situacao"].value_counts().to_dict())
        diag["anomes_inicio"].update(chunk["anomes_inicio"].map(lambda s: s[:4]).value_counts().to_dict())
        if sit_in and (chunk["situacao"] != "").any():
            chunk = chunk[chunk["situacao"].map(lambda s: s == "" or any_match(sit_in, s))]
        if org_out:
            chunk = chunk[~chunk["org_atuacao"].map(lambda s: any_match(org_out, norm(s)))]
        mantidos += len(chunk)

        uf_res = chunk["uf_residencia"].map(norm_uf)
        uf_upag = chunk["uf_upag"].map(norm_uf)
        residencia_vazia += int((uf_res == "").sum())
        diag["uf_residencia"].update(uf_res.value_counts().to_dict())
        diag["uf_upag"].update(uf_upag.value_counts().to_dict())
        grupo = [nucleo.classificar(o, "", u) for o, u in zip(chunk["org_atuacao"], chunk["uorg"])]
        diag["grupo"].update(Counter(g or "(fora do núcleo)" for g in grupo))
        agg.update(zip(uf_res, uf_upag, chunk["org_atuacao"].map(norm), grupo))
        log(f"  lidos={tot:,} mantidos={mantidos:,}")

    rows = [dict(uf_residencia=k[0], uf_upag=k[1], org_atuacao=k[2], grupo_nucleo=k[3], n_abono=n)
            for k, n in agg.items()]
    df = pd.DataFrame(rows).sort_values(["uf_residencia", "org_atuacao"])
    mes_ref = mes_ref_de_nome(path.name)
    df["mes_ref"] = mes_ref
    df.to_csv(INTERIM / "abono_uf_org.csv", index=False, encoding="utf-8")

    n_total = int(df.n_abono.sum())
    com_ambas = df[(df.uf_residencia != "") & (df.uf_upag != "")]
    diverg = int(com_ambas.loc[com_ambas.uf_residencia != com_ambas.uf_upag, "n_abono"].sum())
    base_div = int(com_ambas.n_abono.sum())
    pct_res = 1 - residencia_vazia / max(tot, 1)
    with open(INTERIM / "diag_f2.txt", "w", encoding="utf-8") as fh:
        fh.write(f"F2 — {path.name} — mes_ref={mes_ref}\n")
        fh.write(f"cabeçalho original ({len(header)} colunas): {header}\n")
        fh.write(f"mapa de colunas: {mapa}\n")
        fh.write(f"linhas lidas={tot}  mantidas={mantidos}  abonos finais={n_total}\n")
        fh.write(f"preenchimento UF residência={pct_res:.1%} (P1 exige > 90%)\n")
        fh.write(f"divergência UPAG x residência={diverg}/{base_div} "
                 f"({(diverg / base_div if base_div else 0):.1%})\n\n")
        for k, c in diag.items():
            fh.write(f"== value_counts {k} ==\n")
            for v, n in c.most_common(60):
                fh.write(f"{n:>9}  {v}\n")
            fh.write("\n")
    write_json(INTERIM / "meta_f2.json", dict(
        arquivo=path.name, sha256=sha256_file(path), mes_ref=mes_ref, sep=sep, encoding=enc,
        mapa_colunas=mapa, colunas_extras=extras, linhas_lidas=tot, linhas_mantidas=mantidos, abonos=n_total,
        preenchimento_uf_residencia=round(pct_res, 4),
        divergencia_upag_residencia=round(diverg / base_div, 4) if base_div else None))
    log(f"F2 ok: {len(df)} linhas agregadas, {n_total:,} abonos; UF residência preenchida {pct_res:.1%}")


if __name__ == "__main__":
    main()
