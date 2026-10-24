"""
avaliar_comparativo.py — Avaliação comparativa TF-IDF x Sentence-BERT.

Roda os dois métodos sobre os mesmos pares (currículo, vaga) do gabarito humano e
compara o desempenho com métricas de classificação e de ranqueamento.

Entradas (em data/processado/):
  amostra_anotacao.xlsx  -> colunas: id_par, texto_curriculo, texto_vaga
  gabarito_final.xlsx    -> colunas: Par (1..N), Compativel (0/1)
(alinhados por ordem de linha: Par i == linha i-1 da amostra)

Saídas:
  data/processado/resultados_por_par.csv   -> score de cada método por par
  impressão das métricas no terminal

Métricas:
  - Independentes de limiar: AUC-ROC e AP (área sob a curva precisão-revocação).
  - Classificação: Precisão, Revocação e F1 no limiar de melhor F1 (reportado).
  - Ranqueamento: NDCG médio por currículo.
  - Spearman entre os escores dos dois métodos.
  - Wilcoxon pareado sobre o NDCG por currículo (significância da diferença).
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             precision_recall_fscore_support, ndcg_score)

# raiz do projeto (pasta que contém 'src'), rode de onde rodar
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


def carregar():
    amo = pd.read_excel(AMOSTRA).reset_index(drop=True)
    gab = pd.read_excel(GABARITO).sort_values("Par").reset_index(drop=True)
    assert len(amo) == len(gab), "amostra e gabarito têm tamanhos diferentes"
    df = pd.DataFrame({
        "id_par": amo["id_par"],
        "id_curriculo": amo["id_par"].astype(str).str.split("__").str[0],
        "cv": amo["texto_curriculo"].astype(str),
        "vaga": amo["texto_vaga"].astype(str),
        "label": gab["Compativel"].astype(int),
    })
    return df


def escorar(df):
    """Roda os dois matchers por par e devolve os escores."""
    from src.matching.matcher import matcher as matcher_tfidf
    from src.matching.semantic_matcher import matcher_semantico

    s_tfidf, s_sbert = [], []
    for _, r in df.iterrows():
        s_tfidf.append(matcher_tfidf.comparar_um(r["cv"], r["vaga"]).score_final)
        s_sbert.append(matcher_semantico.comparar_um(r["cv"], r["vaga"]).score_final)
    df["score_tfidf"] = s_tfidf
    df["score_sbert"] = s_sbert
    return df


def melhor_f1(y, scores):
    """Varre limiares e devolve (limiar, precisão, revocação, f1) de melhor F1."""
    melhores = (0.5, 0.0, 0.0, 0.0)
    for t in sorted(set(scores)):
        pred = (np.asarray(scores) >= t).astype(int)
        p, r, f, _ = precision_recall_fscore_support(
            y, pred, average="binary", zero_division=0)
        if f > melhores[3]:
            melhores = (float(t), p, r, f)
    return melhores


def ndcg_por_curriculo(df, col_score):
    """NDCG por currículo (grupos com >=2 pares e ao menos 1 positivo)."""
    valores = {}
    for cid, g in df.groupby("id_curriculo"):
        if len(g) < 2 or g["label"].sum() == 0:
            continue
        valores[cid] = ndcg_score([g["label"].values], [g[col_score].values])
    return valores


def metricas(nome, y, scores):
    auc = roc_auc_score(y, scores) if len(set(y)) > 1 else float("nan")
    ap  = average_precision_score(y, scores)
    t, p, r, f = melhor_f1(y, scores)
    print(f"\n### {nome}")
    print(f"  AUC-ROC            : {auc:.3f}")
    print(f"  AP (PR-AUC)        : {ap:.3f}")
    print(f"  Melhor F1          : {f:.3f}  (limiar={t:.3f})")
    print(f"  Precisão / Revoc.  : {p:.3f} / {r:.3f}")
    return {"auc": auc, "ap": ap, "f1": f, "limiar": t, "precisao": p, "revocacao": r}


def bootstrap_diff_auc(y, s_a, s_b, n=5000, seed=0):
    """Diferença de AUC (B - A) com IC95% e p bilateral, por reamostragem dos pares."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y); s_a = np.asarray(s_a); s_b = np.asarray(s_b)
    idx = np.arange(len(y))
    difs = []
    for _ in range(n):
        b = rng.choice(idx, len(idx), replace=True)
        if len(set(y[b])) < 2:
            continue
        difs.append(roc_auc_score(y[b], s_b[b]) - roc_auc_score(y[b], s_a[b]))
    difs = np.array(difs)
    obs = roc_auc_score(y, s_b) - roc_auc_score(y, s_a)
    lo, hi = np.percentile(difs, [2.5, 97.5])
    p = 2 * min((difs <= 0).mean(), (difs >= 0).mean())
    return obs, lo, hi, p


def main():
    df = carregar()
    n = len(df); pos = int(df["label"].sum())
    print(f"Pares: {n} | compatíveis: {pos} ({pos/n:.1%}) | incompatíveis: {n-pos}")
    print(f"Currículos distintos: {df['id_curriculo'].nunique()}")

    df = escorar(df)
    df.to_csv(SAIDA, index=False, encoding="utf-8")
    print(f"\nEscores salvos em {SAIDA}")

    y = df["label"].values
    metricas("TF-IDF (score final do sistema)", y, df["score_tfidf"].values)
    metricas("Sentence-BERT (ajustado)",        y, df["score_sbert"].values)

    # significância da diferença de desempenho (bootstrap pareado da AUC)
    obs, lo, hi, p = bootstrap_diff_auc(y, df["score_tfidf"].values, df["score_sbert"].values)
    print(f"\n### Diferença de AUC (SBERT - TF-IDF), bootstrap pareado")
    print(f"  Diferença: {obs:+.3f}  IC95% [{lo:+.3f}, {hi:+.3f}]  p={p:.4f}  "
          f"({'significativa' if p < 0.05 else 'não significativa'} a 5%)")

    # correlação entre os dois métodos
    rho, pval = spearmanr(df["score_tfidf"], df["score_sbert"])
    print(f"\n### Correlação entre os métodos")
    print(f"  Spearman (TF-IDF x SBERT): rho={rho:.3f}  (p={pval:.3g})")

    # NDCG por currículo + Wilcoxon pareado
    nd_t = ndcg_por_curriculo(df, "score_tfidf")
    nd_s = ndcg_por_curriculo(df, "score_sbert")
    comuns = sorted(set(nd_t) & set(nd_s))
    print(f"\n### Ranqueamento por currículo — NDCG (grupos avaliáveis: {len(comuns)})")
    if len(comuns) < 10:
        print("  AVISO: poucos currículos têm >=2 candidatos nesta amostra, então o")
        print("  NDCG/Wilcoxon por currículo é apenas indicativo. As métricas por par")
        print("  (AUC, AP, F1) e o bootstrap acima são a base da comparação.")
    if comuns:
        vt = [nd_t[c] for c in comuns]; vs = [nd_s[c] for c in comuns]
        print(f"  NDCG médio TF-IDF : {np.mean(vt):.3f}")
        print(f"  NDCG médio SBERT  : {np.mean(vs):.3f}")
        if len(comuns) >= 2 and any(a != b for a, b in zip(vt, vs)):
            try:
                w, pw = wilcoxon(vt, vs)
                print(f"  Wilcoxon pareado (NDCG): W={w:.1f}  p={pw:.4f}  "
                      f"({'diferença significativa' if pw < 0.05 else 'sem diferença significativa'} a 5%)")
            except ValueError as e:
                print(f"  Wilcoxon não aplicável: {e}")
        else:
            print("  Wilcoxon não aplicável (poucos grupos ou escores idênticos).")
    else:
        print("  Nenhum currículo com >=2 pares e ao menos 1 positivo — NDCG/Wilcoxon indisponíveis.")
        print("  (Aumente candidatos por currículo na amostra se quiser essa análise.)")


if __name__ == "__main__":
    main()
