"""00 — Gera F1 e F2 FICTÍCIOS com o layout real dos arquivos, em data/raw/ficticio/.

Serve para desenvolver e testar o pipeline e o site antes de baixar as bases
verdadeiras. Nenhum número aqui tem significado. Os arquivos gerados contêm
colunas NOME/CPF/MATRICULA preenchidas com lixo justamente para provar que o
pipeline nunca as carrega.
"""
from __future__ import annotations

import argparse
import random

from common import RAW, UFS, log

CAB_F1 = ["Id_SERVIDOR_PORTAL", "NOME", "CPF", "MATRICULA", "DESCRICAO_CARGO", "CLASSE_CARGO",
          "REFERENCIA_CARGO", "PADRAO_CARGO", "NIVEL_CARGO", "SIGLA_FUNCAO", "NIVEL_FUNCAO",
          "FUNCAO", "CODIGO_ATIVIDADE", "ATIVIDADE", "OPCAO_PARCIAL", "COD_UORG_LOTACAO",
          "UORG_LOTACAO", "COD_ORG_LOTACAO", "ORG_LOTACAO", "COD_ORGSUP_LOTACAO", "ORGSUP_LOTACAO",
          "COD_UORG_EXERCICIO", "UORG_EXERCICIO", "COD_ORG_EXERCICIO", "ORG_EXERCICIO",
          "COD_ORGSUP_EXERCICIO", "ORGSUP_EXERCICIO", "COD_TIPO_VINCULO", "TIPO_VINCULO",
          "SITUACAO_VINCULO", "DATA_INICIO_AFASTAMENTO", "DATA_TERMINO_AFASTAMENTO",
          "REGIME_JURIDICO", "JORNADA_DE_TRABALHO", "DATA_INGRESSO_CARGOFUNCAO",
          "DATA_NOMEACAO_CARGOFUNCAO", "DATA_INGRESSO_ORGAO", "DOCUMENTO_INGRESSO_SERVICOPUBLICO",
          "DATA_DIPLOMA_INGRESSO_SERVICOPUBLICO", "DIPLOMA_INGRESSO_CARGOFUNCAO",
          "DIPLOMA_INGRESSO_ORGAO", "DIPLOMA_INGRESSO_SERVICOPUBLICO", "UF_EXERCICIO"]

CAB_F2 = ["Descrição do cargo", "Nível de escolaridade", "Denominação do órgão de atuação",
          "UF da UPAG de vinculação", "Denominação da unidade organizacional", "UF da residência",
          "Cidade da residência", "Situação do servidor", "Anos de serviço público",
          "Meses de serviço público", "Ano/mês inicial do abono", "Valor"]

# (org, orgsup, cod, grupo, peso relativo)
ORGAOS = [
    ("INSTITUTO NACIONAL DO SEGURO SOCIAL", "MINISTERIO DA PREVIDENCIA SOCIAL", "57202", "INSS", 18),
    ("MINISTERIO DA FAZENDA", "MINISTERIO DA FAZENDA", "25000", "RFB", 12),
    ("INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATISTICA", "MINISTERIO DO PLANEJAMENTO E ORCAMENTO", "20105", "IBGE", 3),
    ("UNIVERSIDADE FEDERAL DE {UF}", "MINISTERIO DA EDUCACAO", "264{i:02d}", "UNIV", 25),
    ("INSTITUTO FEDERAL DE EDUCACAO, CIENCIA E TECNOLOGIA DE {UF}", "MINISTERIO DA EDUCACAO", "265{i:02d}", "IF", 15),
    ("MINISTERIO DA SAUDE", "MINISTERIO DA SAUDE", "36000", "", 8),
    ("DEPARTAMENTO DE POLICIA FEDERAL", "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA", "30108", "", 5),
    ("MINISTERIO DA AGRICULTURA E PECUARIA", "MINISTERIO DA AGRICULTURA E PECUARIA", "22000", "", 4),
    ("FUNDACAO NACIONAL DOS POVOS INDIGENAS", "MINISTERIO DOS POVOS INDIGENAS", "30202", "", 2),
    ("DEPARTAMENTO NACIONAL DE INFRAESTRUTURA DE TRANSPORTES", "MINISTERIO DOS TRANSPORTES", "39252", "", 3),
]
SITUACOES = [("ATIVO PERMANENTE", 88), ("CEDIDO", 2), ("CONT.TEMP.", 4), ("NOMEADO CARGO COMIS.", 3),
             ("REQUISITADO", 1), ("EXERC.DESCENT.CARREI", 2)]
CARGOS = ["ANALISTA", "TECNICO", "PROFESSOR DO MAGISTERIO SUPERIOR", "PROFESSOR SUBSTITUTO",
          "AUDITOR", "ASSISTENTE EM ADMINISTRACAO", "MEDICO"]


def escolher(pesos):
    return random.choices([x[0] for x in pesos], weights=[x[1] for x in pesos])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60_000)
    ap.add_argument("--mes", default="202604")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)
    out = RAW / "ficticio"
    out.mkdir(parents=True, exist_ok=True)

    # cada UF tem intensidade própria de presença e de abono, para gerar quadrantes variados
    pres = {u[1]: random.uniform(0.3, 2.5) for u in UFS}
    frag = {u[1]: random.uniform(0.04, 0.35) for u in UFS}
    pesos_uf = [(u[1], (u[0] != "53") * pres[u[1]] * (1 + i % 4) + (u[0] == "53") * 12) for i, u in enumerate(UFS)]

    f1 = out / f"{args.mes}_Cadastro.csv"
    f2 = out / f"{args.mes}_AbonoPermanencia.csv"
    abonos = []
    with open(f1, "w", encoding="ISO-8859-1", newline="") as fh:
        fh.write(";".join(CAB_F1) + "\n")
        for i in range(args.n):
            uf = escolher(pesos_uf)
            iuf = next(k for k, u in enumerate(UFS) if u[1] == uf)
            org, orgsup, cod, grupo, _ = random.choices(ORGAOS, weights=[o[4] for o in ORGAOS])[0]
            org = org.format(UF=next(u[2] for u in UFS if u[1] == uf).upper())
            cod = cod.format(i=iuf)
            uorg = (f"DELEGACIA DA RECEITA FEDERAL EM CIDADE-{uf}" if grupo == "RFB"
                    else f"UNIDADE {random.randint(1, 30)}/{uf}")
            sit = escolher(SITUACOES)
            tipo = "Contrato Temporário" if sit == "CONT.TEMP." else "Cargo Efetivo"
            regime = "CONTRATO TEMPORARIO" if sit == "CONT.TEMP." else "REGIME JURIDICO UNICO"
            cargo = random.choice(CARGOS)
            uf_ex = "" if random.random() < 0.02 else uf   # 2% sem UF para testar fallback
            row = [str(100000 + i), f"NOME FICTICIO {i}", "***.000.000-**", f"{i:07d}", cargo, "", "", "",
                   "", "", "", "", "", "", "", "1", uorg, cod, org, "0", orgsup,
                   "1", uorg, cod, org, "0", orgsup, "1", tipo, sit, "", "", regime, "40", "", "",
                   "", "", "", "", "", "", uf_ex]
            fh.write(";".join(row) + "\n")
            # dup de 1%: mesma pessoa com dois vínculos
            if random.random() < 0.01:
                fh.write(";".join(row) + "\n")
            if sit == "ATIVO PERMANENTE" and random.random() < frag[uf]:
                uf_upag = uf if random.random() < 0.85 else "DF"
                abonos.append(["Analista", "Superior", org, uf_upag, uorg, uf if random.random() < 0.97 else "",
                               "Cidade Fictícia", "Ativo Permanente", str(random.randint(30, 40)),
                               str(random.randint(0, 11)), f"{random.randint(2015, 2026)}{random.randint(1, 12):02d}",
                               "0,00"])
    with open(f2, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(";".join(CAB_F2) + "\n")
        for a in abonos:
            fh.write(";".join(a) + "\n")
    log(f"Fictício: {f1.name} ({args.n} vínculos) e {f2.name} ({len(abonos)} abonos) em {out}")


if __name__ == "__main__":
    main()
