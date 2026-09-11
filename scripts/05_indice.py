"""05 — Cálculo do IDSP-F por UF e lente.

A(t) = ativos_L(t) / populacao(t) x 10.000   (presença; A_pct 0 = menor presença)
B(t) = abono_L(t) / ativos_L(t)               (fragilidade; B_pct 100 = maior)
Quadrante 2x2 por corte (mediana | tercil); gravidade = ((100 - A_pct) + B_pct) / 2.
Supressão de qualquer célula com n < supressao_min.

Saídas: data/processed/idspf_uf.{csv,json}, idspf_uf_grupo.{csv,json}, metadata.json
        (JSONs copiados para site/data/)
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone

import pandas as pd

from common import INTERIM, PROCESSED, SITE_DATA, Lentes, Nucleo, log, parametros, write_json

CLASSES = {
    ("baixo", "alto"): ("deserto_critico", "Deserto crítico"),
    ("baixo", "baixo"): ("deserto_estavel", "Deserto estável"),
    ("alto", "alto"): ("presenca_em_risco", "Presença em risco"),
    ("alto", "baixo"): ("presenca_consolidada", "Presença consolidada"),
}


def percentil(s: pd.Series) -> pd.Series:
    """Percentil por posição (0 = menor, 100 = maior); empates recebem a média."""
    n = s.notna().sum()
    if n <= 1:
        return s.map(lambda _: 50.0)
    return ((s.rank(method="average") - 1) / (n - 1) * 100).round(1)


def classificar(df: pd.DataFrame, corte: str) -> tuple[pd.DataFrame, dict]:
    if corte == "tercil":
        a_lim, b_lim = 100 / 3, 200 / 3
    else:
        a_lim, b_lim = 50.0, 50.0
    indefinido = df.A_pct.isna() | df.B_pct.isna()
    a_nivel = df.A_pct.map(lambda v: "baixo" if pd.notna(v) and v < a_lim else "alto")
    b_nivel = df.B_pct.map(lambda v: "alto" if pd.notna(v) and v >= b_lim else "baixo")
    df["quadrante"] = [CLASSES[(a, b)][0] for a, b in zip(a_nivel, b_nivel)]
    df["classe"] = [CLASSES[(a, b)][1] for a, b in zip(a_nivel, b_nivel)]
    df.loc[indefinido, ["quadrante", "classe"]] = ["sem_dado", "Sem dado"]
    df["gravidade"] = (((100 - df.A_pct) + df.B_pct) / 2).round(1)
    # UF sem dado na lente não recebe posição: vai para o fim, explicitamente
    df["posicao"] = (df.gravidade.rank(method="min", ascending=False)
                     .fillna(len(df) + 1).astype(int))
    return df, dict(corte=corte, A_pct_lim=round(a_lim, 1), B_pct_lim=round(b_lim, 1),
                    A_raw_lim=round(float(df.A_raw.quantile(a_lim / 100)), 2),
                    B_raw_lim=round(float(df.B_raw.quantile(b_lim / 100)), 4),
                    ufs_sem_dado=int(indefinido.sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ficticio", action="store_true", help="marca a saída como dados fictícios")
    args = ap.parse_args()

    p = parametros()
    smin = int(p.get("supressao_min", 5))
    corte = p.get("corte", "mediana")
    nucleo = Nucleo()
    lentes = Lentes()
    LENTES = lentes.ids

    pop = pd.read_csv(INTERIM / "pop_uf.csv", dtype={"cod_ibge": str})
    f1 = pd.read_csv(INTERIM / "presenca_uf_org.csv", dtype=str, keep_default_na=False)
    f2 = pd.read_csv(INTERIM / "abono_uf_org.csv", dtype=str, keep_default_na=False)
    f1["n_ativos"] = f1.n_ativos.astype(int)
    f2["n_abono"] = f2.n_abono.astype(int)
    meta_f1 = json.load(open(INTERIM / "meta_f1.json", encoding="utf-8"))
    meta_f2 = json.load(open(INTERIM / "meta_f2.json", encoding="utf-8"))
    meta_f3 = json.load(open(INTERIM / "meta_f3.json", encoding="utf-8"))
    cob = json.load(open(INTERIM / "cobertura.json", encoding="utf-8"))

    # Cobertura territorial por órgão, calculada ANTES de descartar os vínculos sem UF.
    cob_org = (f1.groupby("org")
                 .apply(lambda g: g.loc[g.uf != "", "n_ativos"].sum() / max(g.n_ativos.sum(), 1),
                        include_groups=False))

    f1 = f1[f1.uf != ""]
    f2 = f2[f2.uf_residencia != ""]

    # O eixo B só pode ser calculado sobre órgãos presentes NAS DUAS bases e bem
    # territorializados no cadastro. Sem a primeira restrição, o numerador cobre órgãos
    # que o denominador não tem (militares, ex-territórios). Sem a segunda, o numerador
    # vem de uma base territorializada em 99,9% e o denominador de outra com buracos —
    # em ambos os casos aparecem UFs com "mais de 100% dos servidores já elegíveis".
    lim_cob = float(p.get("cobertura_uf_minima_org", 0.8))
    cw = pd.read_csv(INTERIM / "crosswalk.csv", keep_default_na=False)
    casados = cw[cw.metodo != "sem_casamento"]
    casados = casados[casados.org_siape.map(lambda o: cob_org.get(o, 0.0)) >= lim_cob]
    orgs_f1 = set(casados.org_siape)
    orgs_f2 = set(casados.org_abono)
    log(f"Eixo B restrito a {len(orgs_f1)} órgãos casados com cobertura territorial "
        f">= {lim_cob:.0%}")

    saida, cortes = {}, {}
    for lente in LENTES:
        g = lentes.grupos(lente)
        if g == "todos":
            a, b = f1, f2
        else:
            a = f1[f1.grupo_nucleo.isin(g)]
            b = f2[f2.grupo_nucleo.isin(g)]
        b = b[b.org_atuacao.isin(orgs_f2)]
        den = a[a.org.isin(orgs_f1)]          # denominador do eixo B, mesmo universo de b
        df = pop[["cod_ibge", "sigla", "nome", "regiao", "populacao"]].rename(columns={"sigla": "uf"})
        df = df.merge(a.groupby("uf", as_index=False).n_ativos.sum(), on="uf", how="left")
        df = df.merge(den.groupby("uf", as_index=False).n_ativos.sum()
                         .rename(columns={"n_ativos": "n_ativos_b"}), on="uf", how="left")
        df = df.merge(b.groupby("uf_residencia", as_index=False).n_abono.sum()
                       .rename(columns={"uf_residencia": "uf"}), on="uf", how="left")
        df[["n_ativos", "n_ativos_b", "n_abono"]] = (
            df[["n_ativos", "n_ativos_b", "n_abono"]].fillna(0).astype(int))
        df["lente"] = lente
        df["A_raw"] = (df.n_ativos / df.populacao * 10_000).round(2)
        # divisão segura: UF sem ativos na lente vira NaN, não erro
        df["B_raw"] = pd.to_numeric(df.n_abono / df.n_ativos_b.replace(0, pd.NA),
                                    errors="coerce").round(4)
        df["A_pct"] = percentil(df.A_raw)
        df["B_pct"] = percentil(df.B_raw)
        df, cortes[lente] = classificar(df, corte)

        flags = []
        for _, r in df.iterrows():
            f = []
            if r.n_ativos < smin:
                f.append("ativos_suprimidos")
            if 0 < r.n_abono < smin:
                f.append("abono_suprimido")
            if r.n_abono == 0:
                f.append("sem_abono_registrado")
            if pd.isna(r.B_raw):
                f.append("B_indisponivel")
            flags.append(";".join(f))
        df["flags"] = flags
        # supressão: célula publicada com n < smin vira "<5" e razão derivada é omitida
        df["n_ativos_pub"] = df.n_ativos.map(lambda v: f"<{smin}" if v < smin else str(v))
        df["n_ativos_b_pub"] = df.n_ativos_b.map(lambda v: f"<{smin}" if v < smin else str(v))
        df["n_abono_pub"] = df.n_abono.map(lambda v: f"<{smin}" if 0 < v < smin else str(v))
        df.loc[(df.n_abono > 0) & (df.n_abono < smin), "B_raw"] = pd.NA
        df.loc[df.n_ativos < smin, "A_raw"] = pd.NA
        df.loc[df.n_ativos_b < smin, "B_raw"] = pd.NA
        saida[lente] = df.sort_values("posicao")

    uf_out = pd.concat(saida.values(), ignore_index=True)
    cols = ["uf", "nome", "regiao", "lente", "populacao", "n_ativos_pub", "n_ativos_b_pub",
            "n_abono_pub", "A_raw", "B_raw", "A_pct", "B_pct", "quadrante", "classe",
            "gravidade", "posicao", "flags"]
    csv_uf = uf_out[cols].rename(columns={"n_ativos_pub": "n_ativos",
                                          "n_ativos_b_pub": "n_ativos_base_b",
                                          "n_abono_pub": "n_abono"})
    csv_uf.to_csv(PROCESSED / "idspf_uf.csv", index=False, encoding="utf-8")

    # por grupo do núcleo
    g1 = (f1[(f1.grupo_nucleo != "") & (f1.org.isin(orgs_f1))]
          .groupby(["uf", "grupo_nucleo"], as_index=False).n_ativos.sum())
    g2 = (f2[(f2.grupo_nucleo != "") & (f2.org_atuacao.isin(orgs_f2))]
            .groupby(["uf_residencia", "grupo_nucleo"], as_index=False).n_abono.sum()
            .rename(columns={"uf_residencia": "uf"}))
    base = pd.MultiIndex.from_product([pop.sigla, nucleo.ids], names=["uf", "grupo_nucleo"]).to_frame(index=False)
    gr = base.merge(g1, how="left").merge(g2, how="left").fillna({"n_ativos": 0, "n_abono": 0})
    gr[["n_ativos", "n_abono"]] = gr[["n_ativos", "n_abono"]].astype(int)
    gr["nome_grupo"] = gr.grupo_nucleo.map(nucleo.nomes)
    gr["suprimido"] = (gr.n_ativos < smin) | ((gr.n_abono > 0) & (gr.n_abono < smin))
    gr["B_raw"] = pd.to_numeric(gr.n_abono / gr.n_ativos.replace(0, pd.NA), errors="coerce").round(4)
    gr.loc[gr.suprimido, "B_raw"] = pd.NA
    gr["n_ativos"] = [f"<{smin}" if s and int(v) < smin else str(v) for v, s in zip(gr.n_ativos, gr.suprimido)]
    gr["n_abono"] = [f"<{smin}" if s and 0 < int(v) < smin else str(v) for v, s in zip(gr.n_abono, gr.suprimido)]
    gr.to_csv(PROCESSED / "idspf_uf_grupo.csv", index=False, encoding="utf-8")

    def rec(df):
        out = []
        for r in df.to_dict("records"):
            for k, v in list(r.items()):
                if isinstance(v, float) and pd.isna(v):
                    r[k] = None
            out.append(r)
        return out

    uf_json = {l: rec(csv_uf[csv_uf.lente == l].drop(columns="lente")) for l in LENTES}
    for l in LENTES:
        for r in uf_json[l]:
            r["flags"] = [x for x in (r["flags"] or "").split(";") if x]
    metadata = dict(
        produto="IDSP-F — Índice de Deserto de Serviço Público Federal",
        versao=p.get("versao_pipeline", "1.0.0"), recorte="UF", ficticio=bool(args.ficticio),
        gerado_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        mes_ref_f1=meta_f1.get("mes_ref"), mes_ref_f2=meta_f2.get("mes_ref"),
        ano_pop=meta_f3.get("ano_ref_pop"),
        fontes=dict(
            f1=dict(nome="Cadastro de Servidores — Portal da Transparência (CGU), fonte SIAPE",
                    arquivo=meta_f1.get("arquivo"), sha256=meta_f1.get("sha256"),
                    linhas_lidas=meta_f1.get("linhas_lidas"), ativos=meta_f1.get("ativos"),
                    territorializacao=meta_f1.get("uf_metodo")),
            f2=dict(nome="Abono de Permanência — Gestão de Pessoas (Executivo Federal), MGI, dados.gov.br",
                    arquivo=meta_f2.get("arquivo"), sha256=meta_f2.get("sha256"),
                    abonos=meta_f2.get("abonos"),
                    preenchimento_uf_residencia=meta_f2.get("preenchimento_uf_residencia")),
            f3=dict(nome="Estimativas da população residente — IBGE (SIDRA t/6579)",
                    ano=meta_f3.get("ano_ref_pop")),
            f4=dict(nome="Malha de UFs — IBGE (API de malhas)")),
        cobertura_crosswalk=dict(nucleo=cob.get("nucleo"), total=cob.get("total"),
                                 por_metodo=cob.get("por_metodo"),
                                 nota=("O eixo B usa apenas órgãos presentes nas duas bases. "
                                       "n_ativos_base_b é o denominador efetivo da fragilidade.")),
        divergencia_upag_residencia=meta_f2.get("divergencia_upag_residencia"),
        regras_de_filtro=dict(f1=meta_f1.get("regras_de_filtro"), f2=p.get("filtro_f2")),
        parametros=dict(corte=corte, supressao_min=smin, cortes=cortes),
        grupos_nucleo=[dict(id=g["id"], nome=g["nome"],
                            descricao=" ".join((g.get("descricao") or "").split()))
                       for g in nucleo.grupos],
        lentes=lentes.publico(), lente_padrao=lentes.padrao,
        fora_do_escopo=["militares", "Bacen", "Judiciário", "Legislativo", "estatais",
                        "servidores estaduais e municipais"],
        licencas=dict(codigo="MIT", dados="CC BY 4.0"),
    )
    write_json(PROCESSED / "idspf_uf.json", uf_json)
    write_json(PROCESSED / "idspf_uf_grupo.json", rec(gr))
    write_json(PROCESSED / "metadata.json", metadata)
    for f in ("idspf_uf.json", "idspf_uf_grupo.json", "metadata.json", "idspf_uf.csv", "idspf_uf_grupo.csv"):
        shutil.copy(PROCESSED / f, SITE_DATA / f)
    for l in LENTES:
        top = saida[l].iloc[0]
        log(f"[{l:11}] A mediana={cortes[l]['A_raw_lim']:6.2f}  mais grave: {top.uf} "
            f"({top.classe}, gravidade {top.gravidade})")
    log("Índice ok")


if __name__ == "__main__":
    main()
