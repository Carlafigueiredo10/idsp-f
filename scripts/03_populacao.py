"""03 — População residente por UF (IBGE) e malha geográfica.

População: API SIDRA, tabela 6579, nível UF, último período. Fallback: data/raw/pop_uf.csv
(colunas: cod_ibge ou sigla, populacao, ano).
Malha: API de malhas do IBGE (GeoJSON, qualidade mínima), coordenadas arredondadas,
propriedades sigla/nome adicionadas; versionada em data/geo/uf.geojson e copiada ao site.

Saídas: data/interim/pop_uf.csv, data/geo/uf.geojson, site/data/uf.geojson
"""
from __future__ import annotations

import argparse
import json
import shutil

import pandas as pd
import requests

from common import COD_TO_SIGLA, GEO, INTERIM, RAW, SITE_DATA, UFS, log, norm_uf, write_json

SIDRA = "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/all/p/{periodo}"
MALHA = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
         "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF")
MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def populacao_sidra(periodo: str = "last") -> pd.DataFrame:
    r = requests.get(SIDRA.format(periodo=periodo), timeout=60)
    r.raise_for_status()
    dados = r.json()[1:]
    rows = [dict(cod_ibge=d["D1C"], populacao=int(d["V"]), ano_ref_pop=int(d["D3C"])) for d in dados]
    return pd.DataFrame(rows)


def _uf_do_municipio(m: dict) -> str | None:
    """A sigla da UF vive em dois caminhos diferentes na API de localidades:
    municípios novos podem ter microrregiao nula e só trazer regiao-imediata."""
    via = ((m.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF")
    if not via:
        via = ((m.get("regiao-imediata") or {}).get("regiao-intermediaria") or {}).get("UF")
    return via["sigla"] if via else None


def gazetteer_municipios() -> pd.DataFrame:
    """Municípios do IBGE, restritos aos nomes inequívocos (uma única UF) e com
    pelo menos 6 caracteres — base da inferência de UF por nome de cidade."""
    from collections import Counter

    from common import norm as _norm

    r = requests.get(MUNICIPIOS, timeout=120)
    r.raise_for_status()
    muns = r.json()
    freq = Counter(_norm(m["nome"]) for m in muns)
    linhas = []
    for m in muns:
        nome = _norm(m["nome"])
        uf = _uf_do_municipio(m)
        if uf and freq[nome] == 1 and len(nome) >= 6:
            linhas.append(dict(cod_ibge_mun=m["id"], nome_norm=nome, uf=uf))
    df = pd.DataFrame(linhas).drop_duplicates("nome_norm").sort_values("nome_norm")
    log(f"Gazetteer: {len(df)} nomes inequívocos de {len(muns)} municípios")
    return df


def populacao_fallback() -> pd.DataFrame:
    p = RAW / "pop_uf.csv"
    if not p.exists():
        raise SystemExit("SIDRA indisponível e data/raw/pop_uf.csv ausente.")
    df = pd.read_csv(p, dtype=str)
    col_uf = "cod_ibge" if "cod_ibge" in df else "sigla"
    df["sigla"] = df[col_uf].map(norm_uf)
    df["cod_ibge"] = df["sigla"].map({v: k for k, v in COD_TO_SIGLA.items()})
    df["populacao"] = df["populacao"].str.replace(r"\D", "", regex=True).astype(int)
    df["ano_ref_pop"] = int(df["ano"].iloc[0]) if "ano" in df else 0
    return df[["cod_ibge", "populacao", "ano_ref_pop"]]


def _rnd(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 3), round(coords[1], 3)]
    return [_rnd(c) for c in coords]


def _area_com_sinal(anel) -> float:
    """Área com sinal pela fórmula do shoelace: positiva = sentido anti-horário."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1]):
        s += x1 * y2 - x2 * y1
    return s / 2


def _rewind(poligono) -> list | None:
    """Reorienta os anéis para a convenção do d3-geo, que é o INVERSO da do RFC 7946:
    d3 trata polígonos como esféricos e exige o anel externo em sentido horário
    (buracos anti-horários). A malha do IBGE vem anti-horária, e sem esta correção
    o d3 desenha o complemento do polígono — cada estado cobre o mapa inteiro.

    Anéis que ficam com área zero após o arredondamento (ilhas menores que a
    precisão de ~100 m) são descartados; devolve None se sobrar nada."""
    saida = []
    for i, anel in enumerate(poligono):
        externo = i == 0
        a = _area_com_sinal(anel)
        if a == 0:
            if externo:
                return None
            continue
        saida.append(anel if (a < 0) == externo else anel[::-1])
    return saida or None


def normalizar_malha(g: dict) -> dict:
    for f in g["features"]:
        cod = str(f["properties"].get("codarea", f["properties"].get("cod_ibge", "")))
        sigla = COD_TO_SIGLA[cod]
        f["properties"] = dict(cod_ibge=cod, sigla=sigla,
                               nome=next(u[2] for u in UFS if u[1] == sigla))
        geom = f["geometry"]
        coords = _rnd(geom["coordinates"])
        if geom["type"] == "Polygon":
            novo = _rewind(coords)
            if novo is None:
                raise SystemExit(f"Geometria degenerada em {sigla}")
            geom["coordinates"] = novo
        elif geom["type"] == "MultiPolygon":
            partes = [p for p in (_rewind(pol) for pol in coords) if p]
            if not partes:
                raise SystemExit(f"Geometria degenerada em {sigla}")
            geom["coordinates"] = partes
        else:
            raise SystemExit(f"Geometria inesperada: {geom['type']}")
    return g


def baixar_malha() -> dict:
    r = requests.get(MALHA, timeout=120)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-rede", action="store_true", help="usa só fallbacks locais")
    ap.add_argument("--ano", default="last",
                    help="ano da estimativa de população (ex.: 2025); 'last' = mais recente")
    args = ap.parse_args()

    dim = pd.DataFrame(UFS, columns=["cod_ibge", "sigla", "nome", "regiao"])
    pop = None
    if not args.sem_rede:
        try:
            pop = populacao_sidra(args.ano)
            log(f"População: SIDRA t/6579, ano {pop.ano_ref_pop.iloc[0]}")
        except Exception as e:  # noqa: BLE001
            log(f"SIDRA falhou ({e}); usando fallback local")
    if pop is None:
        pop = populacao_fallback()
    df = dim.merge(pop, on="cod_ibge", how="left")
    if df.populacao.isna().any():
        raise SystemExit(f"População ausente para: {df[df.populacao.isna()].sigla.tolist()}")
    df["populacao"] = df["populacao"].astype(int)
    df.to_csv(INTERIM / "pop_uf.csv", index=False, encoding="utf-8")
    write_json(INTERIM / "meta_f3.json", dict(fonte="IBGE SIDRA t/6579 n3" if not args.sem_rede else "fallback",
                                              url=SIDRA, ano_ref_pop=int(df.ano_ref_pop.iloc[0])))

    gaz = GEO / "municipios.csv"
    if not gaz.exists() and not args.sem_rede:
        try:
            gazetteer_municipios().to_csv(gaz, index=False, encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            log(f"Gazetteer indisponível ({e}); a inferência de UF por município fica desligada")
    elif gaz.exists():
        log(f"Gazetteer em cache: {gaz}")

    # o download bruto fica em cache; uf.geojson é sempre reconstruído a partir dele
    geo, bruto = GEO / "uf.geojson", GEO / "uf_raw.geojson"
    if not bruto.exists() and not args.sem_rede:
        with open(bruto, "w", encoding="utf-8") as f:
            json.dump(baixar_malha(), f, ensure_ascii=False, separators=(",", ":"))
        log(f"Malha baixada: {bruto.stat().st_size / 1024:.0f} KB")
    if bruto.exists():
        with open(bruto, encoding="utf-8") as f:
            g = normalizar_malha(json.load(f))
        with open(geo, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, separators=(",", ":"))
        shutil.copy(geo, SITE_DATA / "uf.geojson")
        log(f"Malha: {geo.stat().st_size / 1024:.0f} KB, {len(g['features'])} UFs, anéis reorientados")
    else:
        log("AVISO: sem malha; mapa do site ficará vazio")
    log("F3 ok")


if __name__ == "__main__":
    main()
