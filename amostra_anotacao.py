"""
amostra_anotacao.py — Gera a planilha de anotação manual (gabarito).

A partir dos currículos do split de TESTE, monta pares (currículo, vaga) e os
amostra de forma ESTRATIFICADA pela cobertura de skills (faixas alta/média/baixa),
para que o gabarito não fique concentrado em uma única classe. A cobertura NÃO é
exibida na planilha, para não enviesar os anotadores.

Cada anotador (Pedro e Gustavo) preenche a coluna correspondente com:
    1 = compatível   |   0 = não compatível

Depois, o coeficiente Kappa de Cohen entre as duas colunas mede a concordância,
as divergências são resolvidas em conjunto, e a coluna final vira o gabarito.

Saída: data/processado/amostra_anotacao.xlsx
       data/processado/amostra_anotacao_gabarito.json  (mapa id_par -> cobertura, uso interno)
"""

import argparse
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DIR_PROC = os.path.join("data", "processado")


def cobertura(cv: set, vaga: set) -> float:
    return len(cv & vaga) / len(vaga) if vaga else 0.0


def faixa(cob: float) -> str:
    if cob >= 0.70:
        return "alta"
    if cob >= 0.30:
        return "media"
    return "baixa"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--curriculos", default=os.path.join(DIR_PROC, "curriculos_processados.json"))
    p.add_argument("--vagas", default=os.path.join(DIR_PROC, "vagas_processadas.json"))
    p.add_argument("--split", default=os.path.join(DIR_PROC, "split_curriculos.json"))
    p.add_argument("--n", type=int, default=250, help="Total de pares para anotar.")
    p.add_argument("--cand-por-cv", type=int, default=6, help="Vagas candidatas sorteadas por currículo.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--saida", default=os.path.join(DIR_PROC, "amostra_anotacao.xlsx"))
    args = p.parse_args()

    # ids como string: o JSON do split converte chaves numéricas em texto
    curriculos = {str(c["id"]): c for c in json.load(open(args.curriculos, encoding="utf-8"))}
    vagas = [v for v in json.load(open(args.vagas, encoding="utf-8")) if v["skills_extraidas"]]
    split = json.load(open(args.split, encoding="utf-8"))
    ids_teste = [cid for cid, s in split.items() if s == "teste"]

    rng = random.Random(args.seed)
    estratos = defaultdict(list)  # faixa -> lista de pares

    for cid in ids_teste:
        c = curriculos.get(cid)
        if not c or not c.get("skills_lista"):
            continue
        cskills = set(c["skills_lista"])
        for v in rng.sample(vagas, min(args.cand_por_cv, len(vagas))):
            cob = cobertura(cskills, set(v["skills_extraidas"]))
            estratos[faixa(cob)].append({
                "id_par": f"{cid}__{v['id']}",
                "id_curriculo": cid,
                "id_vaga": v["id"],
                "texto_curriculo": c.get("texto_bruto", "")[:3000],
                "texto_vaga": v["descricao"][:3000],
                "cobertura": round(cob, 3),
            })

    # amostra equilibrada entre as três faixas
    por_faixa = max(1, args.n // 3)
    selecionados = []
    for nome in ("alta", "media", "baixa"):
        pool = estratos.get(nome, [])
        rng.shuffle(pool)
        selecionados += pool[:por_faixa]
    rng.shuffle(selecionados)
    selecionados = selecionados[: args.n]

    # planilha para os anotadores (sem mostrar a cobertura)
    try:
        import pandas as pd
        df = pd.DataFrame([{
            "id_par": s["id_par"],
            "texto_curriculo": s["texto_curriculo"],
            "texto_vaga": s["texto_vaga"],
            "anotador_pedro (1/0)": "",
            "anotador_gustavo (1/0)": "",
        } for s in selecionados])
        os.makedirs(os.path.dirname(args.saida), exist_ok=True)
        df.to_excel(args.saida, index=False)
        print(f"{len(df)} pares -> {args.saida}")
    except ImportError:
        # fallback CSV se o pandas/openpyxl não estiver disponível
        import csv
        caminho_csv = args.saida.replace(".xlsx", ".csv")
        with open(caminho_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id_par", "texto_curriculo", "texto_vaga", "anotador_pedro", "anotador_gustavo"])
            for s in selecionados:
                w.writerow([s["id_par"], s["texto_curriculo"], s["texto_vaga"], "", ""])
        print(f"{len(selecionados)} pares -> {caminho_csv} (pandas indisponível, gerado CSV)")

    # mapa interno (cobertura por par) — NÃO entregar aos anotadores
    mapa = {s["id_par"]: {"cobertura": s["cobertura"],
                          "id_curriculo": s["id_curriculo"],
                          "id_vaga": s["id_vaga"]} for s in selecionados}
    with open(os.path.join(DIR_PROC, "amostra_anotacao_gabarito.json"), "w", encoding="utf-8") as f:
        json.dump(mapa, f, ensure_ascii=False, indent=2)

    dist = {n: sum(1 for s in selecionados if faixa(s["cobertura"]) == n) for n in ("alta", "media", "baixa")}
    print(f"Distribuição por faixa de cobertura: {dist}")


if __name__ == "__main__":
    main()
