"""Funções compartilhadas do pipeline IDSP-F. Nenhuma função aqui persiste dado individual."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml
from unidecode import unidecode

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
GEO = ROOT / "data" / "geo"
SITE_DATA = ROOT / "site" / "data"
CONFIG = ROOT / "config"

for _d in (INTERIM, PROCESSED, GEO, SITE_DATA):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- UFs
UFS = [
    ("11", "RO", "Rondônia", "Norte"), ("12", "AC", "Acre", "Norte"),
    ("13", "AM", "Amazonas", "Norte"), ("14", "RR", "Roraima", "Norte"),
    ("15", "PA", "Pará", "Norte"), ("16", "AP", "Amapá", "Norte"),
    ("17", "TO", "Tocantins", "Norte"),
    ("21", "MA", "Maranhão", "Nordeste"), ("22", "PI", "Piauí", "Nordeste"),
    ("23", "CE", "Ceará", "Nordeste"), ("24", "RN", "Rio Grande do Norte", "Nordeste"),
    ("25", "PB", "Paraíba", "Nordeste"), ("26", "PE", "Pernambuco", "Nordeste"),
    ("27", "AL", "Alagoas", "Nordeste"), ("28", "SE", "Sergipe", "Nordeste"),
    ("29", "BA", "Bahia", "Nordeste"),
    ("31", "MG", "Minas Gerais", "Sudeste"), ("32", "ES", "Espírito Santo", "Sudeste"),
    ("33", "RJ", "Rio de Janeiro", "Sudeste"), ("35", "SP", "São Paulo", "Sudeste"),
    ("41", "PR", "Paraná", "Sul"), ("42", "SC", "Santa Catarina", "Sul"),
    ("43", "RS", "Rio Grande do Sul", "Sul"),
    ("50", "MS", "Mato Grosso do Sul", "Centro-Oeste"), ("51", "MT", "Mato Grosso", "Centro-Oeste"),
    ("52", "GO", "Goiás", "Centro-Oeste"), ("53", "DF", "Distrito Federal", "Centro-Oeste"),
]
SIGLAS = {u[1] for u in UFS}
COD_TO_SIGLA = {u[0]: u[1] for u in UFS}
NOME_TO_SIGLA = {unidecode(u[2]).upper(): u[1] for u in UFS}


def norm(s) -> str:
    """Normaliza texto: sem acento, maiúsculas, espaços colapsados."""
    if s is None:
        return ""
    s = unidecode(str(s)).upper().strip()
    return re.sub(r"\s+", " ", s)


def norm_uf(v) -> str:
    """Aceita sigla, nome ou código IBGE; devolve sigla ou '' se não reconhecido."""
    s = norm(v)
    if s in SIGLAS:
        return s
    if s in NOME_TO_SIGLA:
        return NOME_TO_SIGLA[s]
    if s in COD_TO_SIGLA:
        return COD_TO_SIGLA[s]
    return ""


_UF_UORG_PATTERNS = [
    re.compile(r"[/\-]\s*([A-Z]{2})\s*$"),      # "... EM MANAUS/AM", "...-AP"
    re.compile(r"\bEM\s+[A-Z .]+?[/\-]\s*([A-Z]{2})\b"),
    re.compile(r"\b([A-Z]{2})\s*$"),
]
# nomes de estado, do mais longo para o mais curto (evita "PARA" casar dentro de "PARAIBA")
_NOMES_UF_ORD = sorted(NOME_TO_SIGLA.items(), key=lambda kv: -len(kv[0]))


def uf_de_uorg(nome_uorg) -> str:
    """Fallback: extrai sigla de UF do nome da unidade organizacional."""
    s = norm(nome_uorg)
    for pat in _UF_UORG_PATTERNS:
        m = pat.search(s)
        if m and m.group(1) in SIGLAS:
            return m.group(1)
    return uf_de_nome_estado(s)


def uf_de_nome_estado(texto) -> str:
    """UF a partir do nome do estado escrito por extenso no texto.

    Vale sobretudo para o nome do órgão: "UNIVERSIDADE FEDERAL DO CEARA",
    "INSTITUTO FEDERAL DE SAO PAULO". É a regra que mais recupera vínculos cuja
    UF de exercício vem como "-1" no cadastro.
    """
    s = norm(texto)
    for nome, sigla in _NOMES_UF_ORD:
        if re.search(rf"\b{re.escape(nome)}\b", s):
            return sigla
    return ""


class Gazetteer:
    """Municípios do IBGE para inferir UF a partir de nomes de cidade em textos.

    Só entram nomes **inequívocos** (que existem em uma única UF) e com pelo menos
    6 caracteres, para não casar por acidente dentro de nomes de unidade. A busca
    é por n-gramas de palavras, do maior para o menor, então "PRESIDENTE PRUDENTE"
    vence "PRUDENTE" quando ambos existem.
    """

    def __init__(self, caminho: Path | None = None):
        self.mapa: dict[str, str] = {}
        self.max_palavras = 1
        caminho = caminho or (GEO / "municipios.csv")
        if not caminho.exists():
            return
        import csv as _csv

        with open(caminho, encoding="utf-8", newline="") as f:
            for linha in _csv.DictReader(f):
                self.mapa[linha["nome_norm"]] = linha["uf"]
        if self.mapa:
            self.max_palavras = max(len(k.split()) for k in self.mapa)

    def __bool__(self) -> bool:
        return bool(self.mapa)

    def uf(self, texto) -> str:
        if not self.mapa:
            return ""
        tokens = re.findall(r"[A-Z]+", norm(texto))
        for n in range(min(self.max_palavras, len(tokens)), 0, -1):
            for i in range(len(tokens) - n + 1):
                sigla = self.mapa.get(" ".join(tokens[i:i + n]))
                if sigla:
                    return sigla
        return ""


# valores do cadastro que significam "não informado" no campo de UF
UF_NAO_INFORMADA = {"", "-1", "NAO INFORMADO", "NAO SE APLICA", "N/A", "0"}


class Territorializador:
    """Resolve a UF de um vínculo por uma cadeia de regras, da mais forte à mais fraca.

    Devolve (sigla, método). O método é publicado em metadata.json para que o leitor
    saiba qual parcela do índice vem do campo oficial e qual vem de inferência.
    """

    ORDEM = ("UF_EXERCICIO", "UF_na_UORG", "estado_no_ORG", "municipio_na_UORG",
             "municipio_no_ORG", "sem_uf")

    def __init__(self, gazetteer: "Gazetteer | None" = None):
        self.gaz = gazetteer if gazetteer is not None else Gazetteer()

    def resolver(self, uf_campo="", uorg="", org="") -> tuple[str, str]:
        s = norm(uf_campo)
        if s not in UF_NAO_INFORMADA:
            sigla = norm_uf(s)
            if sigla:
                return sigla, "UF_EXERCICIO"
        sigla = uf_de_uorg(uorg)
        if sigla:
            return sigla, "UF_na_UORG"
        sigla = uf_de_nome_estado(org)
        if sigla:
            return sigla, "estado_no_ORG"
        if self.gaz:
            sigla = self.gaz.uf(uorg)
            if sigla:
                return sigla, "municipio_na_UORG"
            sigla = self.gaz.uf(org)
            if sigla:
                return sigla, "municipio_no_ORG"
        return "", "sem_uf"


# ---------------------------------------------------------------- config
def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parametros() -> dict:
    return load_yaml("parametros.yaml")


class Nucleo:
    """Classificador de grupo do núcleo de serviços por regex."""

    def __init__(self):
        cfg = load_yaml("nucleo.yaml")
        self.grupos = cfg["grupos"]
        self._compiled = [
            (g["id"], bool(g.get("uorg", False)), [re.compile(p) for p in g["padroes"]])
            for g in self.grupos
        ]
        self.ids = [g["id"] for g in self.grupos]
        self.nomes = {g["id"]: g["nome"] for g in self.grupos}

    def classificar(self, org="", orgsup="", uorg="") -> str:
        o, s, u = norm(org), norm(orgsup), norm(uorg)
        for gid, usa_uorg, pats in self._compiled:
            for p in pats:
                if p.search(o) or p.search(s) or (usa_uorg and p.search(u)):
                    return gid
        return ""


def tokens_para_casamento(texto) -> list[str]:
    """Quebra o nome de um órgão em palavras, tratando as abreviações do abono.

    O recurso de abono trunca os nomes em 40 caracteres e abrevia sem espaço depois
    do ponto: `UNIVERSIDADE FED.DO TRIANGULO MINEIRO`. Sem quebrar no ponto, `FED.DO`
    vira uma palavra que não casa com nada.
    """
    s = norm(texto).replace("-", " ").replace(".", ". ")
    return [t for t in re.split(r"[^A-Z0-9.]+", s) if t]


def construir_vocabulario(nomes) -> dict[str, str]:
    """Vocabulário de palavras inteiras, indexado por si mesmas, a partir de nomes
    não abreviados (o cadastro). Serve para expandir as abreviações do abono."""
    from collections import Counter

    freq: Counter = Counter()
    for nome in nomes:
        for t in tokens_para_casamento(nome):
            if not t.endswith(".") and len(t) > 2:
                freq[t] += 1
    return freq


def expandir_abreviacoes(texto, vocabulario) -> str:
    """`FUND. INST. BRASIL. GEOG. E ESTATISTICA` -> `FUNDACAO INSTITUTO BRASILEIRO
    GEOGRAFIA E ESTATISTICA`.

    Cada token terminado em ponto é prefixo da palavra inteira. Em vez de manter um
    dicionário de abreviações à mão, a expansão procura no vocabulário da outra base
    a palavra mais frequente que começa com aquele prefixo. Prefixos ambíguos ficam
    com a palavra mais comum, e o casamento aproximado ainda precisa passar do limiar.
    """
    saida = []
    for t in tokens_para_casamento(texto):
        if t.endswith(".") and len(t) >= 3:
            pref = t[:-1]
            cands = [(n, w) for w, n in vocabulario.items() if w.startswith(pref)]
            saida.append(max(cands)[1] if cands else pref)
        else:
            saida.append(t.rstrip("."))
    return " ".join(saida)


class Lentes:
    """Recortes do índice, definidos em config/lentes.yaml.

    Cada lente é um subconjunto de grupos do núcleo (ou `todos`). Separar as lentes
    é o que impede o índice de somar serviço exclusivo com serviço concorrente e
    chamar o resultado de deserto — ver o cabeçalho do arquivo de configuração.
    """

    def __init__(self):
        cfg = load_yaml("lentes.yaml")
        self.itens = cfg["lentes"]
        if not self.itens:
            raise SystemExit("config/lentes.yaml não define nenhuma lente")
        ids = [x["id"] for x in self.itens]
        if len(set(ids)) != len(ids):
            raise SystemExit(f"ids de lente repetidos em lentes.yaml: {ids}")
        padroes = [x["id"] for x in self.itens if x.get("padrao")]
        if len(padroes) > 1:
            raise SystemExit(f"mais de uma lente marcada como padrão: {padroes}")
        self.padrao = padroes[0] if padroes else ids[0]
        validos = set(Nucleo().ids)
        for x in self.itens:
            g = x.get("grupos")
            if g != "todos" and not set(g) <= validos:
                raise SystemExit(f"lente {x['id']} cita grupos inexistentes: {set(g) - validos}")

    @property
    def ids(self) -> list[str]:
        return [x["id"] for x in self.itens]

    def grupos(self, lente_id: str):
        x = next(i for i in self.itens if i["id"] == lente_id)
        return x["grupos"]

    def publico(self) -> list[dict]:
        """Definições como vão para metadata.json, para o site montar os botões."""
        return [dict(id=x["id"], nome=x["nome"],
                     frase=x.get("frase", ""),
                     descricao=" ".join((x.get("descricao") or "").split()),
                     grupos=(x["grupos"] if x["grupos"] != "todos" else "todos"),
                     padrao=bool(x.get("padrao"))) for x in self.itens]


def compile_list(patterns) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in (patterns or [])]


def any_match(pats: list[re.Pattern], value: str) -> bool:
    return any(p.search(value) for p in pats)


# ---------------------------------------------------------------- utilidades
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mes_ref_de_nome(nome: str) -> str:
    """Extrai o mês de referência do nome do arquivo.

    Aceita AAAAMM (202512_Cadastro.csv) e MMAAAA (ABONOP_122025.csv), que é o
    padrão do recurso de Abono no repositório do dados.gov.br.
    """
    m = re.search(r"(20\d{2})[-_]?(0[1-9]|1[0-2])(?!\d)", nome)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"(?<!\d)(0[1-9]|1[0-2])[-_]?(20\d{2})(?!\d)", nome)
    return f"{m.group(2)}-{m.group(1)}" if m else ""


def cabecalho_alinhado(path: Path, sep: str, enc: str) -> tuple[list[str], int]:
    """Nomes de coluna alinhados ao número real de campos das linhas de dados.

    O recurso de Abono publicado no dados.gov.br termina cada linha de dados com
    um separador sobrando: 14 nomes no cabeçalho e 15 campos por linha. Lido de
    forma ingênua, o pandas promove a primeira coluna a índice e desloca todos os
    valores — a UF de residência passa a receber o nome da cidade, silenciosamente.
    Aqui os campos excedentes ganham nomes sintéticos e nada se desloca.

    Devolve (nomes, quantidade de colunas extras).
    """
    import csv as _csv

    with open(path, encoding=enc, newline="") as f:
        leitor = _csv.reader(f, delimiter=sep)
        try:
            nomes = next(leitor)
        except StopIteration:
            return [], 0
        try:
            n_dados = len(next(leitor))
        except StopIteration:
            n_dados = len(nomes)
    extras = max(0, n_dados - len(nomes))
    nomes = list(nomes) + [f"_extra_{i}" for i in range(extras)]
    return nomes, extras


def detectar_sep_encoding(path: Path) -> tuple[str, str]:
    for enc in ("utf-8-sig", "ISO-8859-1"):
        try:
            with open(path, encoding=enc) as f:
                head = f.readline()
            sep = ";" if head.count(";") >= head.count(",") else ","
            return sep, enc
        except UnicodeDecodeError:
            continue
    return ";", "ISO-8859-1"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def encontrar_arquivo(padroes: list[str], arg: str | None = None) -> Path:
    """Localiza o arquivo bruto mais recente que casa com os padrões.

    Ignora `data/raw/ficticio/` — os arquivos sintéticos têm o mesmo formato de nome
    dos reais e chegaram a ser escolhidos no lugar deles, publicando números falsos
    sem qualquer aviso. Para usá-los, passe o caminho em --arquivo.
    """
    if arg:
        p = Path(arg)
        if not p.exists():
            raise SystemExit(f"Arquivo não encontrado: {p}")
        return p
    cands: list[Path] = []
    for pat in padroes:
        cands += list(RAW.rglob(pat))
    cands = [c for c in cands if c.is_file() and "ficticio" not in {p.name for p in c.parents}]
    cands = sorted(set(cands), key=lambda c: (mes_ref_de_nome(c.name), c.name))
    if not cands:
        raise SystemExit(f"Nenhum arquivo em data/raw casando {padroes}. Use --arquivo.")
    escolhido = cands[-1]
    if len(cands) > 1:
        log(f"  {len(cands)} candidatos; usando o mês mais recente: {escolhido.name}")
    return escolhido  # ordenado pelo mês de referência, não pelo nome cru
