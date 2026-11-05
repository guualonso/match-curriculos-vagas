import argparse
import os
import sys

import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

_raiz = os.path.dirname(os.path.abspath(__file__))
while _raiz != os.path.dirname(_raiz):
    if os.path.isdir(os.path.join(_raiz, "src")):
        break
    _raiz = os.path.dirname(_raiz)
sys.path.insert(0, _raiz)

DIR = os.path.join("data", "processado")
AMOSTRA  = os.path.join(DIR, "amostra_anotacao.xlsx")
GABARITO = os.path.join(DIR, "gabarito_final.xlsx")
SAIDA    = os.path.join(DIR, "resultados_por_par.csv")
LIMIAR   = 0.40


def carregar(caminho_amostra, caminho_gabarito):
    amo = pd.read_excel(caminho_amostra).reset_index(drop=True)
    gab = pd.read_excel(caminho_gabarito).sort_values("Par").reset_index(drop=True)
    assert len(amo) == len(gab), "amostra e gabarito têm tamanhos diferentes"
    pendentes = gab.loc[gab["Compativel"].isna(), "Par"].tolist()
    if pendentes:
        sys.exit(f"Gabarito incompleto: preencha a coluna Compativel dos pares {pendentes}.")
    df = pd.DataFrame({
        "id_par": amo["id_par"],
        "id_curriculo": amo["id_par"].astype(str).str.split("__").str[0],
        "cv": amo["texto_curriculo"].astype(str),
        "vaga": amo["texto_vaga"].astype(str),
        "label": gab["Compativel"].astype(int),
    })
    return df


def escorar(df, sbert_base=False):
    from src.matching.matcher import matcher as matcher_tfidf
    from src.matching.semantic_matcher import MatcherSemantico, matcher_semantico
    if sbert_base:
        matcher_semantico = MatcherSemantico(usar_ajustado=False)

    s_tfidf, s_sbert = [], []
    for _, r in df.iterrows():
        s_tfidf.append(matcher_tfidf.comparar_um(r["cv"], r["vaga"]).score_final)
        s_sbert.append(matcher_semantico.comparar_um(r["cv"], r["vaga"]).score_final)
    df["score_tfidf"] = s_tfidf
    df["score_sbert"] = s_sbert
    return df


def metricas(nome, y, scores, limiar=LIMIAR):
    predicao = (scores >= limiar).astype(int)
    verdadeiro_negativo, falso_positivo, falso_negativo, verdadeiro_positivo = confusion_matrix(y, predicao, labels=[0, 1]).ravel()
    resultado = {
        "auc": roc_auc_score(y, scores),
        "acuracia": accuracy_score(y, predicao),
        "precisao": precision_score(y, predicao, zero_division=0),
        "revocacao": recall_score(y, predicao, zero_division=0),
        "f1": f1_score(y, predicao, zero_division=0),
    }
    print(f"\n### {nome}")
    print(f"  AUC-ROC   : {resultado['auc']:.3f}")
    print(f"  Acurácia  : {resultado['acuracia']:.3f}   (limiar {limiar:.2f})")
    print(f"  Precisão  : {resultado['precisao']:.3f}")
    print(f"  Revocação : {resultado['revocacao']:.3f}")
    print(f"  F1-score  : {resultado['f1']:.3f}")
    print(f"  VP {verdadeiro_positivo} | FP {falso_positivo} | FN {falso_negativo} | VN {verdadeiro_negativo} "
          f"| indicados como compatíveis: {verdadeiro_positivo + falso_positivo}")
    print(f"  Score médio: compatíveis {scores[y == 1].mean():.3f} | não compatíveis {scores[y == 0].mean():.3f}")
    return resultado


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--amostra", default=AMOSTRA, help="Planilha com id_par, texto_curriculo e texto_vaga.")
    parser.add_argument("--gabarito", default=GABARITO, help="Planilha com as colunas Par e Compativel.")
    parser.add_argument("--saida", default=SAIDA, help="CSV com o score de cada par.")
    parser.add_argument("--limiar", type=float, default=LIMIAR, help="Score mínimo para considerar o par compatível.")
    parser.add_argument("--sbert-base", action="store_true",
                        help="Usa o SBERT original, sem ajuste fino, para medir o efeito do fine-tuning.")
    args = parser.parse_args()

    df = carregar(args.amostra, args.gabarito)
    total = len(df); compativeis = int(df["label"].sum())
    print(f"Pares: {total} | compatíveis: {compativeis} ({compativeis/total:.1%}) | não compatíveis: {total-compativeis}")
    print(f"Currículos distintos: {df['id_curriculo'].nunique()}")
    print(f"Referência 'tudo não compatível': acurácia {(total-compativeis)/total:.3f} | "
          f"precisão de um classificador aleatório: {compativeis/total:.3f}")

    df = escorar(df, sbert_base=args.sbert_base)
    df.to_csv(args.saida, index=False, encoding="utf-8")
    print(f"\nEscores salvos em {args.saida}")

    y = df["label"].values
    metricas("TF-IDF (score final do sistema)", y, df["score_tfidf"].values, args.limiar)
    metricas("Sentence-BERT (" + ("sem ajuste fino" if args.sbert_base else "ajustado") + ")",
             y, df["score_sbert"].values, args.limiar)


if __name__ == "__main__":
    main()
