import argparse
import json
import os
import random

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

DIR_PROC = os.path.join("data", "processado")
MODELOS = [("SBERT sem ajuste", "paraphrase-multilingual-MiniLM-L12-v2"),
           ("SBERT ajustado", os.path.join("models", "sbert_finetuned"))]


def cobertura(cv: set, vaga: set) -> float:
    return len(cv & vaga) / len(vaga) if vaga else 0.0


def montar_pares(limite, seed):
    positivos = [json.loads(l) for l in open(os.path.join(DIR_PROC, "pares_validacao.jsonl"), encoding="utf-8")]
    curriculos = {str(c["id"]): set(c.get("skills_lista", []))
                  for c in json.load(open(os.path.join(DIR_PROC, "curriculos_processados.json"), encoding="utf-8"))}
    vagas = [v for v in json.load(open(os.path.join(DIR_PROC, "vagas_processadas.json"), encoding="utf-8"))
             if len(v["skills_extraidas"]) >= 3]

    rng = random.Random(seed)
    rng.shuffle(positivos)
    pares = []
    for p in positivos[:limite]:
        cskills = curriculos[str(p["id_curriculo"])]
        pares.append((p["texto_curriculo"], p["texto_vaga"], 1))
        while True:
            v = rng.choice(vagas)
            if cobertura(cskills, set(v["skills_extraidas"])) < 0.30:
                pares.append((p["texto_curriculo"], v["descricao"], 0))
                break
    return pares


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None, help="Nº máximo de pares positivos.")
    ap.add_argument("--corte", type=float, default=0.40)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer

    pares = montar_pares(args.limite, args.seed)
    limpar = lambda t: " ".join((t or "").split())
    cvs = [limpar(c) for c, _, _ in pares]
    vagas = [limpar(v) for _, v, _ in pares]
    y = np.array([r for _, _, r in pares])
    print(f"{len(y)} pares de validação ({y.sum()} positivos, {len(y) - y.sum()} negativos), corte {args.corte}\n")

    for nome, caminho in MODELOS:
        modelo = SentenceTransformer(caminho)
        modelo.max_seq_length = 256
        a = modelo.encode(cvs, batch_size=64, normalize_embeddings=True, show_progress_bar=True)
        b = modelo.encode(vagas, batch_size=64, normalize_embeddings=True, show_progress_bar=True)
        s = np.clip((a * b).sum(axis=1), 0, 1)
        pred = (s >= args.corte).astype(int)
        print(f"{nome:17s} acurácia {accuracy_score(y, pred):.3f} | precisão {precision_score(y, pred, zero_division=0):.3f} "
              f"| recall {recall_score(y, pred):.3f} | F1 {f1_score(y, pred, zero_division=0):.3f} "
              f"| score médio pos {s[y == 1].mean():.3f} neg {s[y == 0].mean():.3f}")


if __name__ == "__main__":
    main()
