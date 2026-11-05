from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.preprocessamento.limpador_texto import limpar_texto
from src.extraction.skills_extractor import extrator as extrator_skills

MINIMO_SKILLS_DETECTADAS = 2

class ResultadoMatch:
    def __init__(
        self,
        id_vaga: str,
        titulo_vaga: str,
        score_final: float,
        score_tfidf: float,
        score_skills: float,
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
        self.skills_comum = skills_comum
        self.skills_ausentes = skills_ausentes
        self.skills_extras = skills_extras
        self.aviso = aviso

    def nivel_compatibilidade(self) -> str:
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

    def _comparar_skills(
        self, texto_curriculo: str, texto_vaga: str, skills_vaga: Optional[List[str]] = None
    ) -> Dict:
        skills_curriculo = set(extrator_skills.extrair_lista(texto_curriculo))
        skills_da_vaga = set(skills_vaga) if skills_vaga is not None else set(extrator_skills.extrair_lista(texto_vaga))
        return {
            "em_comum": sorted(skills_curriculo & skills_da_vaga),
            "ausentes": sorted(skills_da_vaga - skills_curriculo),
            "extras": sorted(skills_curriculo - skills_da_vaga),
            "total_curriculo": len(skills_curriculo),
            "total_vaga": len(skills_da_vaga),
        }

    def _calcular_score_skills(
        self, texto_curriculo: str, texto_vaga: str, comparacao: Optional[Dict] = None
    ) -> float:
        comparacao = comparacao or self._comparar_skills(texto_curriculo, texto_vaga)
        total_skills_vaga = len(comparacao["em_comum"]) + len(comparacao["ausentes"])

        return len(comparacao["em_comum"]) / total_skills_vaga if total_skills_vaga > 0 else 0.0

    def _montar_resultado(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        score_tfidf_bruto: float,
        id_vaga: str,
        titulo_vaga: str,
        skills_vaga: Optional[List[str]] = None,
    ) -> ResultadoMatch:
        comparacao = self._comparar_skills(texto_curriculo, texto_vaga, skills_vaga)
        score_skills = self._calcular_score_skills(texto_curriculo, texto_vaga, comparacao)
        score_final = min(self.peso_tfidf * score_tfidf_bruto + self.peso_skills * score_skills, 1.0)
        total_detectadas = comparacao["total_curriculo"] + comparacao["total_vaga"]

        aviso = (
            "Poucas skills técnicas detectadas. "
            "O score pode não refletir com precisão a compatibilidade real."
            if total_detectadas < MINIMO_SKILLS_DETECTADAS
            else ""
        )

        return ResultadoMatch(
            id_vaga=id_vaga,
            titulo_vaga=titulo_vaga,
            score_final=score_final,
            score_tfidf=score_tfidf_bruto,
            score_skills=score_skills,
            skills_comum=comparacao["em_comum"],
            skills_ausentes=comparacao["ausentes"],
            skills_extras=comparacao["extras"],
            aviso=aviso,
        )


    def _cosseno_par(self, curriculo_limpo: str, vaga_limpa: str) -> float:
        matriz = self.vetorizador.fit_transform([curriculo_limpo, vaga_limpa])
        return float(cosine_similarity(matriz[0:1], matriz[1:2])[0][0])

    def comparar_um(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        id_vaga: str = "vaga_1",
        titulo_vaga: str = "Vaga",
    ) -> ResultadoMatch:
        tfidf_bruto = self._cosseno_par(self._pre_processar(texto_curriculo), self._pre_processar(texto_vaga))

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
        vagas_limpas = [v.get("texto_limpo") or self._pre_processar(v["description"]) for v in vagas]

        scores_tfidf = [self._cosseno_par(curriculo_limpo, vaga_limpa) for vaga_limpa in vagas_limpas]

        resultados = [
            self._montar_resultado(
                texto_curriculo,
                vaga["description"],
                float(scores_tfidf[i]),
                vaga.get("id", str(i)),
                vaga.get("title", "Sem título"),
                vaga.get("skills"),
            )
            for i, vaga in enumerate(vagas)
        ]

        resultados.sort(key=lambda r: r.score_final, reverse=True)
        return resultados[:top_n] if top_n else resultados

    def match_one(self, resume_text, job_text, job_id="job_1", job_title="Vaga"):
        return self.comparar_um(resume_text, job_text, job_id, job_title)

    def match_many(self, resume_text, jobs, top_n=None):
        return self.comparar_varios(resume_text, jobs, top_n)


matcher = MatcherCurriculoVaga(peso_tfidf=0.25, peso_skills=0.75)
