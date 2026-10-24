"""
finetune_sbert.py — Ajuste fino (fine-tuning) do SBERT para o domínio de TI.

Usa MultipleNegativesRankingLoss: precisa apenas de pares POSITIVOS
(currículo, vaga); os negativos são gerados automaticamente dentro de cada lote,
usando as demais vagas do lote como exemplos negativos. É a loss recomendada
para tarefas de correspondência/recuperação e simplifica a preparação dos dados.

Entrada:  data/processado/pares_treino.jsonl  (campos: texto_curriculo, texto_vaga)
Saída:    models/sbert_finetuned/             (modelo pronto para o semantic_matcher)

Exemplo (GPU):
    python scripts/finetune_sbert.py --epocas 3 --batch 32 --seq 256 --fp16
"""

import argparse
import json
import os

MODELO_BASE = "paraphrase-multilingual-MiniLM-L12-v2"
CAMINHO_PARES = os.path.join("data", "processado", "pares_treino.jsonl")
CAMINHO_SAIDA = os.path.join("models", "sbert_finetuned")


def carregar_pares(caminho):
    from sentence_transformers import InputExample

    exemplos = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            par = json.loads(linha)
            cv = (par.get("texto_curriculo") or "").strip()
            vaga = (par.get("texto_vaga") or "").strip()
            if cv and vaga:
                exemplos.append(InputExample(texts=[cv, vaga]))
    return exemplos


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pares", default=CAMINHO_PARES)
    p.add_argument("--saida", default=CAMINHO_SAIDA)
    p.add_argument("--modelo-base", default=MODELO_BASE)
    p.add_argument("--epocas", type=int, default=3)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--seq", type=int, default=256, help="Comprimento máximo de tokens.")
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--fp16", action="store_true", help="Precisão mista (recomendado em GPU).")
    args = p.parse_args()

    from torch.utils.data import DataLoader
    from sentence_transformers import SentenceTransformer, losses

    exemplos = carregar_pares(args.pares)
    if not exemplos:
        raise SystemExit(f"Nenhum par encontrado em {args.pares}. Rode preparar_pares.py primeiro.")
    print(f"{len(exemplos)} pares positivos carregados.")

    modelo = SentenceTransformer(args.modelo_base)
    modelo.max_seq_length = args.seq

    loader = DataLoader(exemplos, shuffle=True, batch_size=args.batch, drop_last=True)
    loss = losses.MultipleNegativesRankingLoss(modelo)

    passos_por_epoca = max(1, len(loader))
    warmup = int(passos_por_epoca * args.epocas * 0.1)  # 10% de warmup

    print(f"Treinando: {args.epocas} épocas, batch {args.batch}, seq {args.seq}, "
          f"lr {args.lr}, fp16={args.fp16}")
    modelo.fit(
        train_objectives=[(loader, loss)],
        epochs=args.epocas,
        warmup_steps=warmup,
        optimizer_params={"lr": args.lr},
        use_amp=args.fp16,
        show_progress_bar=True,
        output_path=args.saida,
    )
    print(f"Modelo ajustado salvo em {args.saida}")
    print("O semantic_matcher passará a usá-lo automaticamente.")


if __name__ == "__main__":
    main()
