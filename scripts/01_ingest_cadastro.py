"""01 — Cadastro de Servidores (Portal da Transparência, fonte SIAPE).

Lê AAAAMM_Cadastro.csv com usecols (colunas de identificação jamais entram em
memória), filtra o universo (cargo efetivo em exercício), deduplica por
ID_SERVIDOR_PORTAL e agrega por UF de exercício x órgão x grupo do núcleo.

Saídas: data/interim/presenca_uf_org.csv, data/interim/diag_f1.txt, data/interim/meta_f1.json
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np
import pandas as pd

from common import (INTERIM, Nucleo, Territorializador, any_match, cabecalho_alinhado,
                    compile_list, detectar_sep_encoding, encontrar_arquivo, log,
                    mes_ref_de_nome, norm, parametros, sha256_file, write_json)

CAMPOS = {
    "ID_SERVIDOR_PORTAL": "id",
    "COD_ORG_EXERCICIO": "cod_org", "ORG_EXERCICIO": "org",
    "COD_ORGSUP_EXERCICIO": "cod_orgsup", "ORGSUP_EXERCICIO": "orgsup",
    "COD_UORG_EXERCICIO": "cod_uorg", "UORG_EXERCICIO": "uorg",
    "UF_EXERCICIO": "uf",
    "TIPO_VINCULO": "tipo", "SITUACAO_VINCULO": "situacao",
    "REGIME_JURIDICO": "regime", "DESCRICAO_CARGO": "cargo",
}
PROIBIDOS = {"NOME", "CPF", "MATRICULA"}


def mapear_cabecalho(path, sep, enc):
    header, extras = cabecalho_alinhado(path, sep, enc)
    mapa = {}
    for col in header:
        n = norm(col).replace(" ", "_")
        if n in PROIBIDOS:
            continue
        if n in CAMPOS:
            mapa[col] = CAMPOS[n]
    faltando = set(CAMPOS.values()) - set(mapa.values())
    return mapa, faltando, list(header), extras


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arquivo", help="caminho do AAAAMM_Cadastro.csv")
    ap.add_argument("--chunksize", type=int, default=200_000)
    args = ap.parse_args()

    path = encontrar_arquivo(["*Cadastro*.csv", "*cadastro*.csv"], args.arquivo)
    sep, enc = detectar_sep_encoding(path)
    mapa, faltando, header, extras = mapear_cabecalho(path, sep, enc)
    log(f"F1: {path.name} sep={sep!r} enc={enc} colunas lidas={len(mapa)} faltando={sorted(faltando)}")
    if "uf" in faltando and "uorg" in faltando:
        raise SystemExit("Sem UF_EXERCICIO nem UORG_EXERCICIO: impossível territorializar.")
    if "id" in faltando:
        log("AVISO: ID_SERVIDOR_PORTAL ausente; sem deduplicação.")

    p = parametros()
    f = p["filtro_f1"]
    sit_in = compile_list(f.get("situacao_incluir"))
    sit_out = compile_list(f.get("situacao_excluir"))
    tipo_out = compile_list(f.get("tipo_vinculo_excluir"))
    reg_out = compile_list(f.get("regime_excluir"))
    cargo_out = compile_list(f.get("cargo_excluir"))
    org_out = compile_list(p.get("orgaos_excluir"))
    nucleo = Nucleo()
    terr = Territorializador()
    if not terr.gaz:
        log("AVISO: gazetteer de municípios ausente; rode 03_populacao.py antes para melhor cobertura")

    vistos: set = set()
    diag = {k: Counter() for k in ("situacao", "tipo", "regime", "uf_metodo", "grupo")}
    tot_lidos = tot_filtro = tot_dup = 0
    agg = Counter()

    reader = pd.read_csv(path, sep=sep, encoding=enc, header=0, names=header,
                         index_col=False, usecols=list(mapa), dtype=str,
                         chunksize=args.chunksize, na_filter=False)
    for chunk in reader:
        chunk = chunk.rename(columns=mapa)
        tot_lidos += len(chunk)
        for c in ("situacao", "tipo", "regime", "cargo", "org", "orgsup", "uorg", "uf",
                  "cod_org", "cod_orgsup"):
            if c not in chunk:
                chunk[c] = ""
        for c in ("situacao", "tipo", "regime", "cargo"):
            chunk[c] = chunk[c].map(norm)
        diag["situacao"].update(chunk["situacao"].value_counts().to_dict())
        diag["tipo"].update(chunk["tipo"].value_counts().to_dict())
        diag["regime"].update(chunk["regime"].value_counts().to_dict())

        keep = chunk["situacao"].map(lambda s: any_match(sit_in, s) and not any_match(sit_out, s))
        keep &= ~chunk["tipo"].map(lambda s: any_match(tipo_out, s))
        keep &= ~chunk["regime"].map(lambda s: any_match(reg_out, s))
        keep &= ~chunk["cargo"].map(lambda s: any_match(cargo_out, s))
        if org_out:
            keep &= ~chunk["org"].map(lambda s: any_match(org_out, norm(s)))
            keep &= ~chunk["orgsup"].map(lambda s: any_match(org_out, norm(s)))
        chunk = chunk[keep]
        tot_filtro += len(chunk)

        if "id" in chunk:
            novo = []
            for i in chunk["id"].tolist():
                if i in vistos:
                    novo.append(False)
                else:
                    vistos.add(i)
                    novo.append(True)
            tot_dup += len(novo) - sum(novo)
            # máscara como array booleano, não lista: `df[[]]` seleciona zero COLUNAS,
            # e um bloco inteiramente filtrado deixaria o DataFrame sem coluna alguma
            chunk = chunk[np.asarray(novo, dtype=bool)]

        resolvido = [terr.resolver(u, uo, o) for u, uo, o in
                     zip(chunk["uf"], chunk["uorg"], chunk["org"])]
        ufs = [r[0] for r in resolvido]
        diag["uf_metodo"].update(r[1] for r in resolvido)
        grupo = [nucleo.classificar(o, s, u) for o, s, u in
                 zip(chunk["org"], chunk["orgsup"], chunk["uorg"])]
        diag["grupo"].update(Counter(g or "(fora do núcleo)" for g in grupo))

        keys = zip(ufs, chunk["cod_org"], chunk["org"].map(norm), chunk["cod_orgsup"],
                   chunk["orgsup"].map(norm), grupo)
        agg.update(keys)
        log(f"  lidos={tot_lidos:,} mantidos={tot_filtro:,} dup={tot_dup:,}")

    vistos.clear()  # ids descartados após agregar (regra 2)
    rows = [dict(uf=k[0], cod_org=k[1], org=k[2], cod_orgsup=k[3], orgsup=k[4],
                 grupo_nucleo=k[5], n_ativos=n) for k, n in agg.items()]
    df = pd.DataFrame(rows).sort_values(["uf", "org"])
    mes_ref = mes_ref_de_nome(path.name)
    df["mes_ref"] = mes_ref
    df.to_csv(INTERIM / "presenca_uf_org.csv", index=False, encoding="utf-8")

    sem_uf = int(df.loc[df.uf == "", "n_ativos"].sum())
    cobertura_uf = 1 - sem_uf / max(int(df.n_ativos.sum()), 1)
    with open(INTERIM / "diag_f1.txt", "w", encoding="utf-8") as fh:
        fh.write(f"F1 — {path.name} — mes_ref={mes_ref}\n")
        fh.write(f"cabeçalho original ({len(header)} colunas): {header}\n")
        fh.write(f"colunas carregadas: {sorted(mapa.values())}\n")
        fh.write(f"linhas lidas={tot_lidos}  após filtro={tot_filtro}  duplicatas removidas={tot_dup}  "
                 f"ativos finais={int(df.n_ativos.sum())}  sem_uf={sem_uf}\n\n")
        for k, c in diag.items():
            fh.write(f"== value_counts {k} (antes do filtro para situacao/tipo/regime) ==\n")
            for v, n in c.most_common(60):
                fh.write(f"{n:>9}  {v}\n")
            fh.write("\n")
    write_json(INTERIM / "meta_f1.json", dict(
        arquivo=path.name, sha256=sha256_file(path), mes_ref=mes_ref, sep=sep, encoding=enc,
        linhas_lidas=tot_lidos, linhas_apos_filtro=tot_filtro, duplicatas=tot_dup,
        ativos=int(df.n_ativos.sum()), sem_uf=sem_uf,
        uf_metodo=dict(diag["uf_metodo"]), cobertura_uf=round(cobertura_uf, 4),
        orgaos_excluidos=p.get("orgaos_excluir"),
        regras_de_filtro=f,
        colunas_faltando=sorted(faltando)))
    log(f"F1 ok: {len(df)} linhas agregadas, {int(df.n_ativos.sum()):,} ativos, "
        f"sem_uf={sem_uf} (cobertura territorial {cobertura_uf:.1%})")


if __name__ == "__main__":
    main()
