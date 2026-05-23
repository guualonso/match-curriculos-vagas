from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.preprocessamento.limpador_texto import limpar_texto
from src.extraction.skills_extractor import extrator as extrator_skills

LIMIAR_COBERTURA = 8

class ResultadoMatch:
    """Representa o resultado de compatibilidade entre currículo e vaga."""

    def __init__(
        self,
        id_vaga: str,
        titulo_vaga: str,
        score_final: float,
        score_tfidf: float,
        score_skills: float,
        cobertura_skills: float,
        skills_comum: List[str],
        skills_ausentes: List[str],
        skills_extras: List[str],
        aviso: str = "",
    ):
        self.id_vaga = id_vaga
        self.titulo_vaga = titulo_vaga
        self.score_final = round(score_final, 4)
        self.score_percentual = round(score_final * 100, 2)
        self.score_tfidf = round(score_tfidf, 4)
        self.score_skills = round(score_skills, 4)
        self.cobertura_skills = round(cobertura_skills, 4)
        self.skills_comum = skills_comum
        self.skills_ausentes = skills_ausentes
        self.skills_extras = skills_extras
        self.aviso = aviso

    def nivel_compatibilidade(self) -> str:
        """Classifica o nível de compatibilidade em Alto, Médio ou Baixo."""
        if self.score_final >= 0.7:
            return "Alto"
        elif self.score_final >= 0.4:
            return "Médio"
        else:
            return "Baixo"

    def para_dict(self) -> Dict:
        return {
            "job_id": self.id_vaga,
            "job_title": self.titulo_vaga,
            "similarity_score": self.score_final,
            "similarity_percent": self.score_percentual,
            "tfidf_score": self.score_tfidf,
            "skills_score": self.score_skills,
            "skill_coverage": self.cobertura_skills,
            "skills_comum": self.skills_comum,
            "skills_ausentes": self.skills_ausentes,
            "skills_extras": self.skills_extras,
            "nivel": self.nivel_compatibilidade(),
            "aviso": self.aviso,
            "matching_skills": self.skills_comum,
            "missing_skills":  self.skills_ausentes,
            "extra_skills":    self.skills_extras,
            "compatibility_level": self.nivel_compatibilidade(),
            "warning": self.aviso,
        }

    def _get_compatibility_level(self) -> str:
        return self.nivel_compatibilidade()


class MatcherCurriculoVaga:

    def __init__(
        self,
        peso_tfidf: float = 0.25,
        peso_skills: float = 0.75,
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 2),
    ):
        assert abs(peso_tfidf + peso_skills - 1.0) < 1e-6, \
            "peso_tfidf + peso_skills deve somar 1.0"

        self.peso_tfidf  = peso_tfidf
        self.peso_skills = peso_skills

        self.vetorizador = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            sublinear_tf=True,
            min_df=1,
        )


    def _pre_processar(self, texto: str) -> str:
        return limpar_texto(texto)

    def _calcular_score_skills(
        self, texto_curriculo: str, texto_vaga: str
    ) -> Tuple[float, float]:
        comparacao = extrator_skills.comparar(texto_curriculo, texto_vaga)
        total_skills_vaga = len(comparacao["em_comum"]) + len(comparacao["ausentes"])

        score = (
            len(comparacao["em_comum"]) / total_skills_vaga
            if total_skills_vaga > 0
            else 0.0
        )

        # Total de skills únicas detectadas nos dois textos juntos
        total_detectadas = (
            len(set(extrator_skills.extrair_lista(texto_curriculo)))
            + len(set(extrator_skills.extrair_lista(texto_vaga)))
        )
        # Normaliza pelo limiar, atingiu o limiar = cobertura 100%
        cobertura = min(total_detectadas / LIMIAR_COBERTURA, 1.0)

        return score, cobertura

    def _fator_confianca(self, cobertura: float) -> float:
        sigmoid = 1.0 / (1.0 + math.exp(-10 * (cobertura - 0.4)))
        lo = 1.0 / (1.0 + math.exp(4))
        fator = 0.55 + 0.45 * (sigmoid - lo) / (1.0 - lo)
        return max(0.55, min(1.0, fator))

    def _montar_resultado(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        score_tfidf_bruto: float,
        id_vaga: str,
        titulo_vaga: str,
    ) -> ResultadoMatch:
        """Constrói o ResultadoMatch combinando todos os scores."""
        score_skills, cobertura = self._calcular_score_skills(texto_curriculo, texto_vaga)
        confianca = self._fator_confianca(cobertura)

        score_tfidf_ajustado = score_tfidf_bruto * confianca
        score_final = min(
            self.peso_tfidf * score_tfidf_ajustado + self.peso_skills * score_skills,
            1.0,
        )

        comparacao = extrator_skills.comparar(texto_curriculo, texto_vaga)

        aviso = (
            "Poucas skills técnicas detectadas. "
            "O score pode não refletir com precisão a compatibilidade real."
            if cobertura < 0.25
            else ""
        )

        return ResultadoMatch(
            id_vaga=id_vaga,
            titulo_vaga=titulo_vaga,
            score_final=score_final,
            score_tfidf=score_tfidf_ajustado,
            score_skills=score_skills,
            cobertura_skills=cobertura,
            skills_comum=comparacao["em_comum"],
            skills_ausentes=comparacao["ausentes"],
            skills_extras=comparacao["extras"],
            aviso=aviso,
        )


    def comparar_um(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        id_vaga: str = "vaga_1",
        titulo_vaga: str = "Vaga",
    ) -> ResultadoMatch:
        """Compara um currículo com uma única vaga."""
        curriculo_limpo = self._pre_processar(texto_curriculo)
        vaga_limpa = self._pre_processar(texto_vaga)

        matriz = self.vetorizador.fit_transform([curriculo_limpo, vaga_limpa])
        tfidf_bruto = float(cosine_similarity(matriz[0:1], matriz[1:2])[0][0])

        return self._montar_resultado(
            texto_curriculo, texto_vaga, tfidf_bruto, id_vaga, titulo_vaga
        )

    def comparar_varios(
        self,
        texto_curriculo: str,
        vagas: List[Dict[str, str]],
        top_n: Optional[int] = None,
    ) -> List[ResultadoMatch]:
        if not vagas:
            return []

        curriculo_limpo = self._pre_processar(texto_curriculo)
        vagas_limpas = [self._pre_processar(v["description"]) for v in vagas]

        todos_docs = [curriculo_limpo] + vagas_limpas
        matriz = self.vetorizador.fit_transform(todos_docs)
        scores_tfidf = cosine_similarity(matriz[0:1], matriz[1:])[0]

        resultados = [
            self._montar_resultado(
                texto_curriculo,
                vaga["description"],
                float(scores_tfidf[i]),
                vaga.get("id", str(i)),
                vaga.get("title", "Sem título"),
            )
            for i, vaga in enumerate(vagas)
        ]

        resultados.sort(key=lambda r: r.score_final, reverse=True)
        return resultados[:top_n] if top_n else resultados

    # Aliases para compatibilidade com routes.py
    def match_one(self, resume_text, job_text, job_id="job_1", job_title="Vaga"):
        return self.comparar_um(resume_text, job_text, job_id, job_title)

    def match_many(self, resume_text, jobs, top_n=None):
        return self.comparar_varios(resume_text, jobs, top_n)


matcher = MatcherCurriculoVaga(peso_tfidf=0.25, peso_skills=0.75)