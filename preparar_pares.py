import argparse
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DIR_PROC = os.path.join("data", "processado")


def cobertura(skills_cv: set[str], skills_vaga: set[str]) -> float:
    if not skills_vaga:
        return 0.0
    return len(skills_cv & skills_vaga) / len(skills_vaga)


def dividir_curriculos(ids, prop=(0.70, 0.15, 0.15), seed=42):
    ids = sorted(set(ids))
    random.Random(seed).shuffle(ids)
    n = len(ids)
    n_tr = int(n * prop[0])
    n_val = int(n * prop[1])
    split = {}
    for i, cid in enumerate(ids):
        if i < n_tr:
            split[cid] = "treino"
        elif i < n_tr + n_val:
            split[cid] = "validacao"
        else:
            split[cid] = "teste"
    return split


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--curriculos", default=os.path.join(DIR_PROC, "curriculos_processados.json"))
    p.add_argument("--vagas", default=os.path.join(DIR_PROC, "vagas_processadas.json"))
    p.add_argument("--limiar", type=float, default=0.70, help="Cobertura mínima para par positivo.")
    p.add_argument("--min-skills-vaga", type=int, default=3, help="Nº mínimo de skills na vaga.")
    p.add_argument("--pos-por-curriculo", type=int, default=10, help="Máx. de pares positivos por currículo.")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    curriculos = json.load(open(args.curriculos, encoding="utf-8"))
    vagas = json.load(open(args.vagas, encoding="utf-8"))

    vaga_por_skill = defaultdict(set)
    vagas_por_id = {}
    for v in vagas:
        vskills = set(v["skills_extraidas"])
        if len(vskills) < args.min_skills_vaga:
            continue
        vagas_por_id[v["id"]] = {**v, "_skills": vskills}
        for s in vskills:
            vaga_por_skill[s].add(v["id"])

    split = dividir_curriculos([c["id"] for c in curriculos], seed=args.seed)

    pares = {"treino": [], "validacao": [], "teste": []}
    rng = random.Random(args.seed)

    for c in curriculos:
        cid = c["id"]
        conjunto = split[cid]
        if conjunto == "teste":
            continue
        cskills = set(c.get("skills_lista", []))
        if not cskills:
            continue

        candidatas = set()
        for s in cskills:
            candidatas |= vaga_por_skill.get(s, set())

        positivas = []
        for vid in candidatas:
            v = vagas_por_id[vid]
            if cobertura(cskills, v["_skills"]) >= args.limiar:
                positivas.append(v)

        rng.shuffle(positivas)
        for v in positivas[: args.pos_por_curriculo]:
            pares[conjunto].append({
                "id_curriculo": cid,
                "id_vaga": v["id"],
                "texto_curriculo": c.get("texto_bruto", ""),
                "texto_vaga": v["descricao"],
                "cobertura": round(cobertura(cskills, v["_skills"]), 3),
            })

    os.makedirs(DIR_PROC, exist_ok=True)
    for nome, arquivo in [("treino", "pares_treino.jsonl"), ("validacao", "pares_validacao.jsonl")]:
        caminho = os.path.join(DIR_PROC, arquivo)
        with open(caminho, "w", encoding="utf-8") as f:
            for par in pares[nome]:
                f.write(json.dumps(par, ensure_ascii=False) + "\n")
        print(f"{len(pares[nome]):>6} pares -> {caminho}")

    with open(os.path.join(DIR_PROC, "split_curriculos.json"), "w", encoding="utf-8") as f:
        json.dump(split, f, ensure_ascii=False, indent=2)

    n = len(split)
    dist = {k: sum(1 for v in split.values() if v == k) for k in ("treino", "validacao", "teste")}
    print(f"Split por currículo (total {n}): {dist}")


if __name__ == "__main__":
    main()
