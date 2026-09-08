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


def uf_de_uorg(nome_uorg) -> str:
    """Fallback: extrai sigla de UF do nome da unidade organizacional."""
    s = norm(nome_uorg)
    for pat in _UF_UORG_PATTERNS:
        m = pat.search(s)
        if m and m.group(1) in SIGLAS:
            return m.group(1)
    for nome, sigla in NOME_TO_SIGLA.items():
        if re.search(rf"\b{re.escape(nome)}\b", s):
            return sigla
    return ""


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
    """Extrai AAAAMM do nome de arquivo (ex.: 202604_Cadastro.csv -> 2026-04)."""
    m = re.search(r"(20\d{2})[-_]?(\d{2})", nome)
    return f"{m.group(1)}-{m.group(2)}" if m else ""


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
    if arg:
        p = Path(arg)
        if not p.exists():
            raise SystemExit(f"Arquivo não encontrado: {p}")
        return p
    cands = []
    for pat in padroes:
        cands += list(RAW.rglob(pat))
    cands = sorted({c for c in cands if c.is_file()}, key=lambda c: c.name)
    if not cands:
        raise SystemExit(f"Nenhum arquivo em data/raw casando {padroes}. Use --arquivo.")
    return cands[-1]  # nome mais recente (AAAAMM ordena lexicograficamente)
