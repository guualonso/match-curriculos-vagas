"""
preparar_amostra_dificil.py — Gera uma amostra de avaliação DIRIGIDA.

Objetivo: testar os métodos no regime onde o SBERT deve ter vantagem — pares de
MESMA área (TI) porém com VOCABULÁRIO diferente (baixa sobreposição lexical).

Construção (transparente e sem viés a favor de nenhum método):
  1. Mantém apenas currículos do split de TESTE (sem vazamento do treino).
  2. Mantém só pares "de TI dos dois lados": currículo com >= MIN_SKILLS_CV
     habilidades técnicas detectadas e vaga com >= MIN_SKILLS_VAGA — isso remove
     os cruzamentos de áreas distintas (os pares "fáceis" da 1a amostra).
  3. Para cada currículo, sorteia algumas vagas de TI e calcula a similaridade do
     cosseno TF-IDF (medida de sobreposição lexical) de cada par.
  4. Estratifica por faixa de sobreposição lexical (baixa/média/alta) e amostra
     dando MAIS peso à faixa baixa — o cenário difícil. A faixa NÃO é mostrada
     aos anotadores.

Entradas (data/processado/): curriculos_processados.json, vagas_processadas.json,
split_curriculos.json
Saída: data/processado/amostra_dificil.xlsx  (para anotação manual, mesmo formato)
"""

import json
import os
import random
import sys
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DIR = os.path.join("data", "processado")
MIN_SKILLS_CV   = 3     # currículo precisa ter perfil técnico de TI
MIN_SKILLS_VAGA = 3     # vaga precisa ter requisitos de TI
VAGAS_POR_CV    = 8     # vagas de TI sorteadas por currículo para formar pares
N_ALVO          = 60    # total de pares na amostra
PESOS_FAIXA     = {"baixa": 0.5, "media": 0.3, "alta": 0.2}  # oversample "baixa"


def cos_tfidf(a, b):
    v = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    try:
        m = v.fit_transform([a, b])
        return float(cosine_similarity(m[0:1], m[1:2])[0][0])
    except ValueError:
        return 0.0


def faixa(cos):
    if cos < 0.05:
        return "baixa"
    if cos < 0.15:
        return "media"
    return "alta"


def main():
    rng = random.Random(42)
    curr = json.load(open(os.path.join(DIR, "curriculos_processados.json"), encoding="utf-8"))
    vagas = json.load(open(os.path.join(DIR, "vagas_processadas.json"), encoding="utf-8"))
    split = json.load(open(os.path.join(DIR, "split_curriculos.json"), encoding="utf-8"))

    # currículos de TI do split de teste
    cv_teste = [c for c in curr
                if split.get(str(c["id"])) == "teste"
                and len(c.get("skills_lista", [])) >= MIN_SKILLS_CV]
    # vagas de TI
    vagas_ti = [v for v in vagas if len(v.get("skills_extraidas", [])) >= MIN_SKILLS_VAGA]
    print(f"Currículos de TI no teste: {len(cv_teste)} | vagas de TI: {len(vagas_ti)}")
    if not cv_teste or not vagas_ti:
        print("Dados insuficientes — verifique os JSONs e o split."); return

    # forma pares e classifica por faixa de sobreposição lexical
    por_faixa = defaultdict(list)
    for c in cv_teste:
        texto_cv = c.get("texto_bruto", "")
        for v in rng.sample(vagas_ti, min(VAGAS_POR_CV, len(vagas_ti))):
            cos = cos_tfidf(texto_cv, v["descricao"])
            por_faixa[faixa(cos)].append({
                "id_par": f"{c['id']}__{v['id']}",
                "texto_curriculo": texto_cv[:3000],
                "texto_vaga": v["descricao"][:3000],
                "_cos": round(cos, 3),
            })

    # amostra estratificada com oversample da faixa baixa
    selecionados = []
    for nome, peso in PESOS_FAIXA.items():
        pool = por_faixa.get(nome, [])
        rng.shuffle(pool)
        selecionados += pool[: round(N_ALVO * peso)]
    rng.shuffle(selecionados)
    selecionados = selecionados[:N_ALVO]

    import pandas as pd
    df = pd.DataFrame([{
        "id_par": s["id_par"],
        "texto_curriculo": s["texto_curriculo"],
        "texto_vaga": s["texto_vaga"],
        "anotador_pedro (1/0)": "",
        "anotador_gustavo (1/0)": "",
    } for s in selecionados])
    saida = os.path.join(DIR, "amostra_dificil.xlsx")
    df.to_excel(saida, index=False)

    dist = {n: sum(1 for s in selecionados if faixa(s["_cos"]) == n)
            for n in ("baixa", "media", "alta")}
    print(f"{len(df)} pares -> {saida}")
    print(f"Distribuição por sobreposição lexical: {dist}")


if __name__ == "__main__":
    main()
