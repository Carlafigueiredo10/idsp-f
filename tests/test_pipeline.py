"""Testes do IDSP-F: unidades puras (sempre rodam) e invariantes das saídas (se existirem)."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from common import Nucleo, norm, norm_uf, uf_de_uorg  # noqa: E402

INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
SITE = ROOT / "site" / "data"


# ---------------------------------------------------------------- unidades
def test_norm():
    assert norm("  Universidade   Federal de Goiás ") == "UNIVERSIDADE FEDERAL DE GOIAS"


@pytest.mark.parametrize("v,esp", [("df", "DF"), ("Distrito Federal", "DF"), ("53", "DF"),
                                   ("São Paulo", "SP"), ("XX", ""), ("", "")])
def test_norm_uf(v, esp):
    assert norm_uf(v) == esp


@pytest.mark.parametrize("v,esp", [
    ("DELEGACIA DA RECEITA FEDERAL EM MANAUS/AM", "AM"),
    ("AGENCIA DA PREVIDENCIA SOCIAL MACAPA-AP", "AP"),
    ("CAMPUS PALMAS TO", "TO"),
    ("SUPERINTENDENCIA REGIONAL NO ESPIRITO SANTO", "ES"),
    ("COORDENACAO GERAL DE GESTAO", ""),
])
def test_uf_de_uorg(v, esp):
    assert uf_de_uorg(v) == esp


def test_nucleo_regex():
    n = Nucleo()
    assert n.classificar("INSTITUTO NACIONAL DO SEGURO SOCIAL") == "INSS"
    # a Receita não é separável no cadastro: o grupo é o guarda-chuva do ministério,
    # e precisa casar do mesmo jeito nas duas bases (ver config/nucleo.yaml)
    assert n.classificar("MINISTERIO DA FAZENDA") == "FAZ"
    assert n.classificar("COMISSAO DE VALORES MOBILIARIOS") == ""
    # o cadastro escreve "DO SEGURO", o abono escreve "DE SEGURO"
    assert n.classificar("INSTITUTO NACIONAL DE SEGURO SOCIAL") == "INSS"
    assert n.classificar("FUNDAÇÃO UNIVERSIDADE FEDERAL DO PIAUÍ") == "UNIV"
    assert n.classificar("INSTITUTO FEDERAL DE EDUCACAO, CIENCIA E TECNOLOGIA DO ACRE") == "IF"
    assert n.classificar("MINISTERIO DA SAUDE") == ""


# ---------------------------------------------------------------- saídas
needs_out = pytest.mark.skipif(not (PROCESSED / "idspf_uf.csv").exists(), reason="pipeline ainda não rodou")


@pytest.fixture(scope="module")
def uf():
    # as contagens são texto porque podem vir como "<5" (supressão)
    return pd.read_csv(PROCESSED / "idspf_uf.csv",
                       dtype={"n_ativos": str, "n_ativos_base_b": str, "n_abono": str})


@pytest.fixture(scope="module")
def meta():
    return json.load(open(PROCESSED / "metadata.json", encoding="utf-8"))


@needs_out
def test_lentes_do_config_batem_com_a_saida(uf):
    """As lentes são definidas em config/lentes.yaml; a saída não pode divergir."""
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts"))
    from common import Lentes

    L = Lentes()
    assert set(uf.lente.unique()) == set(L.ids)
    assert L.padrao in L.ids


@needs_out
def test_27_ufs_por_lente(uf):
    for lente, g in uf.groupby("lente"):
        assert len(g) == 27, lente
        assert g.uf.is_unique


@needs_out
def test_percentis_no_intervalo(uf):
    assert uf.A_pct.between(0, 100).all() and uf.B_pct.between(0, 100).all()
    for _, g in uf.groupby("lente"):
        assert g.A_pct.min() == 0 and g.A_pct.max() == 100


@needs_out
def test_quadrantes_validos(uf):
    assert set(uf.quadrante) <= {"deserto_critico", "deserto_estavel", "presenca_em_risco", "presenca_consolidada"}
    assert uf.gravidade.between(0, 100).all()


@needs_out
def test_soma_agregados_igual_total_filtrado(uf, meta):
    f1 = pd.read_csv(INTERIM / "presenca_uf_org.csv", keep_default_na=False)
    tot = uf[uf.lente == "total"]
    publicado = tot.n_ativos[~tot.n_ativos.str.startswith("<")].astype(int).sum()
    com_uf = f1[f1.uf != ""].n_ativos.sum()
    assert publicado == com_uf
    assert com_uf + meta["fontes"]["f1"]["territorializacao"].get("sem_uf", 0) == meta["fontes"]["f1"]["ativos"]


@needs_out
def test_supressao_menor_que_5(uf):
    smin = 5
    for col in ("n_ativos", "n_ativos_base_b", "n_abono"):
        vals = uf[col][~uf[col].str.startswith("<")].astype(int)
        assert ((vals == 0) | (vals >= smin)).all(), col
    gr = pd.read_csv(PROCESSED / "idspf_uf_grupo.csv", dtype=str)
    for col in ("n_ativos", "n_abono"):
        vals = gr[col][~gr[col].str.startswith("<")].astype(int)
        assert ((vals == 0) | (vals >= smin)).all(), col
    assert gr[gr.suprimido == "True"].B_raw.isna().all()


@needs_out
def test_nenhuma_coluna_de_identificacao_no_interim():
    for f in INTERIM.glob("*.csv"):
        if f.name == "pop_uf.csv":  # "nome" aqui é o nome da UF
            continue
        try:
            cols = {c.upper() for c in pd.read_csv(f, nrows=0).columns}
        except pd.errors.EmptyDataError:
            continue
        assert not cols & {"NOME", "CPF", "MATRICULA", "ID_SERVIDOR_PORTAL", "ID"}, f.name


@needs_out
def test_site_recebeu_jsons():
    for f in ("idspf_uf.json", "idspf_uf_grupo.json", "metadata.json"):
        assert (SITE / f).exists(), f
    d = json.load(open(SITE / "idspf_uf.json", encoding="utf-8"))
    meta = json.load(open(SITE / "metadata.json", encoding="utf-8"))
    ids = [l["id"] for l in meta["lentes"]]
    assert set(d) == set(ids), (set(d), set(ids))
    assert all(len(d[i]) == 27 for i in ids)
    assert meta["lente_padrao"] in ids


@pytest.mark.skipif(not (ROOT / "site" / "data" / "uf.geojson").exists(), reason="malha ausente")
def test_malha_orientada_para_d3():
    """d3-geo exige anel externo em sentido horário (área com sinal negativa);
    com a orientação do RFC 7946 cada estado é desenhado como o globo inteiro."""
    def area(anel):
        return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1])) / 2

    g = json.load(open(ROOT / "site" / "data" / "uf.geojson", encoding="utf-8"))
    assert len(g["features"]) == 27
    siglas = set()
    for f in g["features"]:
        siglas.add(f["properties"]["sigla"])
        pols = ([f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon"
                else f["geometry"]["coordinates"])
        for pol in pols:
            assert area(pol[0]) < 0, f['properties']['sigla']      # externo horário
            for buraco in pol[1:]:
                assert area(buraco) > 0, f['properties']['sigla']  # buracos anti-horários
    assert len(siglas) == 27


@needs_out
def test_fragilidade_entre_0_e_1(uf):
    """B é uma parcela dos ativos: acima de 1 significa numerador e denominador
    vindos de universos diferentes — foi o que os ex-territórios produziram."""
    ruins = uf[uf.B_raw.notna() & ((uf.B_raw < 0) | (uf.B_raw > 1))]
    assert ruins.empty, ruins[["uf", "lente", "n_ativos_base_b", "n_abono", "B_raw"]].to_string()


@needs_out
def test_denominador_de_b_nao_excede_ativos(uf):
    """O denominador do eixo B é um subconjunto dos ativos da lente."""
    d = uf[~uf.n_ativos.str.startswith("<") & ~uf.n_ativos_base_b.str.startswith("<")]
    assert (d.n_ativos_base_b.astype(int) <= d.n_ativos.astype(int)).all()


@needs_out
def test_abono_nao_excede_denominador(uf):
    d = uf[~uf.n_abono.str.startswith("<") & ~uf.n_ativos_base_b.str.startswith("<")]
    assert (d.n_abono.astype(int) <= d.n_ativos_base_b.astype(int)).all()


def test_encontrar_arquivo_ignora_ficticios(tmp_path, monkeypatch):
    """Os arquivos sintéticos têm nome no mesmo formato dos reais e chegaram a ser
    escolhidos no lugar deles. A busca automática precisa ignorá-los."""
    import common

    raw = tmp_path / "raw"
    (raw / "ficticio").mkdir(parents=True)
    real = raw / "202512_Cadastro.csv"
    real.write_text("x", encoding="utf-8")
    (raw / "ficticio" / "202604_Cadastro.csv").write_text("x", encoding="utf-8")
    monkeypatch.setattr(common, "RAW", raw)
    assert common.encontrar_arquivo(["*Cadastro*.csv"]) == real


def test_encontrar_arquivo_ordena_por_mes_de_referencia(tmp_path, monkeypatch):
    """ABONOP_012026 é mais recente que ABONOP_122025, embora ordene antes por nome."""
    import common

    raw = tmp_path / "raw"
    raw.mkdir(parents=True)
    (raw / "ABONOP_122025.csv").write_text("x", encoding="utf-8")
    novo = raw / "ABONOP_012026.csv"
    novo.write_text("x", encoding="utf-8")
    monkeypatch.setattr(common, "RAW", raw)
    assert common.encontrar_arquivo(["*BONOP*.csv"]) == novo
