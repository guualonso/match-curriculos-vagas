import math

import numpy as np

from app.database import Job, SessionLocal
from app.services.matching_service import curriculos_distintos, montar_payload_vagas
from avaliar_comparativo import AMOSTRA, GABARITO, LIMIAR, carregar, metricas
from src.matching.matcher import MatcherCurriculoVaga

matcher = MatcherCurriculoVaga()
LIMIAR_COBERTURA = 8


def cobertura_tecnica(resultado):
    habilidades_curriculo = len(resultado.skills_comum) + len(resultado.skills_extras)
    habilidades_vaga = len(resultado.skills_comum) + len(resultado.skills_ausentes)
    return min((habilidades_curriculo + habilidades_vaga) / LIMIAR_COBERTURA, 1.0)


def fator_confianca(cobertura):
    sigmoide = 1.0 / (1.0 + math.exp(-10 * (cobertura - 0.4)))
    minimo = 1.0 / (1.0 + math.exp(4))
    return max(0.55, min(1.0, 0.55 + 0.45 * (sigmoide - minimo) / (1.0 - minimo)))


def score_com_fator(resultado):
    cosseno_ajustado = resultado.score_tfidf * fator_confianca(cobertura_tecnica(resultado))
    return min(matcher.peso_tfidf * cosseno_ajustado + matcher.peso_skills * resultado.score_skills, 1.0)


def comparar(nome, resultados):
    scores_com = np.array([score_com_fator(resultado) for resultado in resultados])
    scores_sem = np.array([resultado.score_final for resultado in resultados])
    cobertura = np.array([cobertura_tecnica(resultado) for resultado in resultados])
    diferenca = scores_sem - scores_com
    mudam = (scores_com >= LIMIAR) != (scores_sem >= LIMIAR)

    print(f"\n=== {nome}: {len(resultados)} pares ===")
    print(f"Pares com cobertura abaixo do máximo: {(cobertura < 1).sum()} ({(cobertura < 1).mean():.1%})")
    print(f"Diferença no score final: média {diferenca.mean():.4f}, máxima {diferenca.max():.4f}")
    print(f"Pares que mudam de decisão no limiar {LIMIAR}: {mudam.sum()}")
    for indice in np.flatnonzero(mudam)[:10]:
        resultado = resultados[indice]
        print(f"  {resultado.titulo_vaga[:50]:50s} cobertura {cobertura[indice]:.3f} | "
              f"com fator {scores_com[indice]:.3f} -> sem fator {scores_sem[indice]:.3f}")
    print(f"Pares com aviso de poucas habilidades (cobertura < 0,25): {(cobertura < 0.25).sum()}")
    return scores_com, scores_sem


def main():
    pares = carregar(AMOSTRA, GABARITO)
    resultados_gabarito = [matcher.comparar_um(cv, vaga) for cv, vaga in zip(pares["cv"], pares["vaga"])]
    scores_com, scores_sem = comparar("Gabarito", resultados_gabarito)
    metricas("TF-IDF com fator de confiança", pares["label"].values, scores_com)
    metricas("TF-IDF sem fator de confiança", pares["label"].values, scores_sem)

    with SessionLocal() as sessao:
        vagas = montar_payload_vagas(sessao.query(Job).all())
        curriculos = [curriculo.raw_text for curriculo in curriculos_distintos(sessao)]
    print(f"\nComparando {len(curriculos)} currículos com {len(vagas)} vagas do banco…")
    resultados_banco = [resultado for texto in curriculos for resultado in matcher.comparar_varios(texto, vagas)]
    comparar("Banco (todos os currículos x todas as vagas)", resultados_banco)


if __name__ == "__main__":
    main()
