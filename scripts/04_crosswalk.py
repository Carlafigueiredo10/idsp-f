"""04 — Crosswalk de nomes de órgão entre F1 (SIAPE/Cadastro) e F2 (Abono).

Normaliza (unidecode, maiúsculas), casa exato -> fuzzy (token_set_ratio >= limiar)
-> overrides manuais em config/crosswalk_overrides.yaml. Publica cobertura
(parcela de ativos em órgãos casados) por lente e a lista de pendentes.

Saídas: data/interim/crosswalk.csv, crosswalk_pendentes.csv, cobertura.json
"""
from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz, process

from common import INTERIM, Nucleo, load_yaml, log, norm, parametros, write_json


def main():
    p = parametros()
    limiar = float(p.get("fuzzy_limiar", 92))
    overrides = {norm(k): norm(v) for k, v in (load_yaml("crosswalk_overrides.yaml").get("overrides") or {}).items()}
    nucleo = Nucleo()

    f1 = pd.read_csv(INTERIM / "presenca_uf_org.csv", dtype=str, keep_default_na=False)
    f2 = pd.read_csv(INTERIM / "abono_uf_org.csv", dtype=str, keep_default_na=False)
    f1["n_ativos"] = f1["n_ativos"].astype(int)
    f2["n_abono"] = f2["n_abono"].astype(int)

    orgs1 = (f1.groupby(["org", "cod_org", "grupo_nucleo"], as_index=False)["n_ativos"].sum()
               .sort_values("n_ativos", ascending=False))
    orgs2 = f2.groupby("org_atuacao", as_index=False)["n_abono"].sum()
    nomes2 = [n for n in orgs2["org_atuacao"].tolist() if n]
    set2 = set(nomes2)

    rows, pend = [], []
    for _, r in orgs1.iterrows():
        nome, metodo, score, alvo = r["org"], "", 0.0, ""
        if not nome:
            continue
        if nome in overrides and overrides[nome] in set2:
            alvo, metodo, score = overrides[nome], "manual", 100.0
        elif nome in set2:
            alvo, metodo, score = nome, "exato", 100.0
        elif nomes2:
            m = process.extractOne(nome, nomes2, scorer=fuzz.token_set_ratio)
            if m and m[1] >= limiar:
                alvo, metodo, score = m[0], "fuzzy", float(m[1])
            else:
                cands = process.extract(nome, nomes2, scorer=fuzz.token_set_ratio, limit=3)
                pend.append(dict(org_siape=nome, cod_org=r["cod_org"], n_ativos=int(r["n_ativos"]),
                                 grupo_nucleo=r["grupo_nucleo"],
                                 candidatos=" | ".join(f"{c[0]} ({c[1]:.0f})" for c in cands)))
        grupo2 = nucleo.classificar(alvo) if alvo else ""
        rows.append(dict(org_siape=nome, cod_org=r["cod_org"], org_abono=alvo,
                         grupo_nucleo=r["grupo_nucleo"], grupo_abono=grupo2,
                         metodo=metodo or "sem_casamento", score=score, n_ativos=int(r["n_ativos"]),
                         grupo_consistente=(grupo2 == r["grupo_nucleo"]) if alvo else None))

    cw = pd.DataFrame(rows)
    cw.to_csv(INTERIM / "crosswalk.csv", index=False, encoding="utf-8")
    pd.DataFrame(pend, columns=["org_siape", "cod_org", "n_ativos", "grupo_nucleo", "candidatos"]).to_csv(INTERIM / "crosswalk_pendentes.csv", index=False, encoding="utf-8")

    def cobertura(mask):
        sub = cw[mask]
        tot = int(sub.n_ativos.sum())
        cas = int(sub.loc[sub.metodo != "sem_casamento", "n_ativos"].sum())
        return round(cas / tot, 4) if tot else 0.0

    cob = dict(total=cobertura(cw.org_siape != ""),
               nucleo=cobertura(cw.grupo_nucleo != ""),
               n_orgaos_f1=int(len(cw)), n_orgaos_f2=len(nomes2),
               n_casados=int((cw.metodo != "sem_casamento").sum()),
               por_metodo=cw.metodo.value_counts().to_dict(),
               grupo_inconsistente=int((cw.grupo_consistente == False).sum()),  # noqa: E712
               limiar_fuzzy=limiar)
    write_json(INTERIM / "cobertura.json", cob)
    log(f"Crosswalk: cobertura núcleo={cob['nucleo']:.1%} total={cob['total']:.1%} "
        f"({cob['n_casados']}/{cob['n_orgaos_f1']} órgãos; {len(pend)} pendentes)")


if __name__ == "__main__":
    main()
