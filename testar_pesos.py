import numpy as np
from sklearn.metrics import roc_auc_score

from avaliar_comparativo import AMOSTRA, GABARITO, LIMIAR, carregar
from src.matching.matcher import MatcherCurriculoVaga


def main():
    pares = carregar(AMOSTRA, GABARITO)
    rotulos = pares["label"].values
    matcher = MatcherCurriculoVaga()
    resultados = [matcher.comparar_um(cv, vaga) for cv, vaga in zip(pares["cv"], pares["vaga"])]
    cosseno = np.array([resultado.score_tfidf for resultado in resultados])
    habilidades = np.array([resultado.score_skills for resultado in resultados])

    print(f"AUC-ROC só do cosseno: {roc_auc_score(rotulos, cosseno):.3f} | "
          f"só das habilidades: {roc_auc_score(rotulos, habilidades):.3f}\n")
    print(f"peso TF-IDF | AUC-ROC | acurácia | precisão | revocação |  F1   | VP/FP/FN/VN  (limiar {LIMIAR})")
    for peso_tfidf in np.round(np.arange(0, 1.0001, 0.05), 2):
        scores = peso_tfidf * cosseno + (1 - peso_tfidf) * habilidades
        indicados = scores >= LIMIAR
        vp = int((indicados & (rotulos == 1)).sum())
        fp = int((indicados & (rotulos == 0)).sum())
        fn = int((~indicados & (rotulos == 1)).sum())
        vn = int((~indicados & (rotulos == 0)).sum())
        precisao = vp / (vp + fp) if vp + fp else 0.0
        revocacao = vp / (vp + fn)
        f1 = 2 * precisao * revocacao / (precisao + revocacao) if precisao + revocacao else 0.0
        marca = "  <- sistema" if peso_tfidf == 0.25 else ""
        print(f"    {peso_tfidf:.2f}    |  {roc_auc_score(rotulos, scores):.3f}  |  {(vp + vn) / len(rotulos):.3f}   |"
              f"  {precisao:.3f}   |   {revocacao:.3f}   | {f1:.3f} | {vp}/{fp}/{fn}/{vn}{marca}")


if __name__ == "__main__":
    main()
