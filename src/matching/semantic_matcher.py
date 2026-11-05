from __future__ import annotations


import os
from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np

from src.extraction.skills_extractor import extrator as extrator_skills
from src.matching.matcher import ResultadoMatch

MODELO_BASE = "paraphrase-multilingual-MiniLM-L12-v2"

CAMINHO_MODELO_AJUSTADO = os.path.join("models", "sbert_finetuned")

PALAVRAS_POR_JANELA = 150
SOBREPOSICAO_PALAVRAS = 30


def dividir_em_janelas(texto: str, tamanho: int = PALAVRAS_POR_JANELA,
                       sobreposicao: int = SOBREPOSICAO_PALAVRAS) -> List[str]:
    palavras = texto.split()
    if len(palavras) <= tamanho:
        return [texto]
    passo = tamanho - sobreposicao
    janelas = []
    for inicio in range(0, len(palavras), passo):
        janelas.append(" ".join(palavras[inicio:inicio + tamanho]))
        if inicio + tamanho >= len(palavras):
            break
    return janelas


@lru_cache(maxsize=2)
def _carregar_modelo(caminho_ou_nome: str):
    from sentence_transformers import SentenceTransformer

    modelo = SentenceTransformer(caminho_ou_nome)
    modelo.max_seq_length = 256
    return modelo


def _resolver_modelo(preferir_ajustado: bool = True) -> str:
    if preferir_ajustado and os.path.isdir(CAMINHO_MODELO_AJUSTADO):
        return CAMINHO_MODELO_AJUSTADO
    return MODELO_BASE


class MatcherSemantico:
    def __init__(self, modelo: Optional[str] = None, usar_ajustado: bool = True,
                 usar_janelas: bool = False):
        self.nome_modelo = modelo or _resolver_modelo(usar_ajustado)
        self.usar_janelas = usar_janelas
        self._cache_embeddings: Dict[str, np.ndarray] = {}
        self._modelo = None

    @property
    def modelo(self):
        if self._modelo is None:
            self._modelo = _carregar_modelo(self.nome_modelo)
        return self._modelo

    def _preparar(self, texto: str) -> str:
        return " ".join((texto or "").split())

    def _embeddings(self, textos: List[str]):
        if not self.usar_janelas:
            faltando = [t for t in dict.fromkeys(textos) if t not in self._cache_embeddings]
            if faltando:
                novos = self.modelo.encode(
                    faltando,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                self._cache_embeddings.update(zip(faltando, novos))
            return np.stack([self._cache_embeddings[t] for t in textos])

        janelas, dono = [], []
        for indice, texto in enumerate(textos):
            for janela in dividir_em_janelas(texto):
                janelas.append(janela)
                dono.append(indice)

        emb_janelas = self.modelo.encode(
            janelas,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        dono = np.asarray(dono)
        emb = np.zeros((len(textos), emb_janelas.shape[1]), dtype=emb_janelas.dtype)
        np.add.at(emb, dono, emb_janelas)
        emb /= np.linalg.norm(emb, axis=1, keepdims=True)
        return emb

    @staticmethod
    def _score(emb_a, emb_b) -> float:
        return float((emb_a * emb_b).sum())

    def _montar_resultado(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        score_semantico: float,
        id_vaga: str,
        titulo_vaga: str,
    ) -> ResultadoMatch:
        comparacao = extrator_skills.comparar(texto_curriculo, texto_vaga)
        score = max(0.0, min(score_semantico, 1.0))

        return ResultadoMatch(
            id_vaga=id_vaga,
            titulo_vaga=titulo_vaga,
            score_final=score,
            score_tfidf=0.0,
            score_skills=0.0,
            skills_comum=comparacao["em_comum"],
            skills_ausentes=comparacao["ausentes"],
            skills_extras=comparacao["extras"],
            aviso="",
        )

    def comparar_um(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        id_vaga: str = "vaga_1",
        titulo_vaga: str = "Vaga",
    ) -> ResultadoMatch:
        emb = self._embeddings(
            [self._preparar(texto_curriculo), self._preparar(texto_vaga)]
        )
        score = self._score(emb[0], emb[1])
        return self._montar_resultado(
            texto_curriculo, texto_vaga, score, id_vaga, titulo_vaga
        )

    def comparar_varios(
        self,
        texto_curriculo: str,
        vagas: List[Dict[str, str]],
        top_n: Optional[int] = None,
    ) -> List[ResultadoMatch]:
        if not vagas:
            return []

        textos = [self._preparar(texto_curriculo)] + [
            self._preparar(v["description"]) for v in vagas
        ]
        emb = self._embeddings(textos)
        emb_cv, emb_vagas = emb[0], emb[1:]

        resultados = [
            self._montar_resultado(
                texto_curriculo,
                vaga["description"],
                self._score(emb_cv, emb_vagas[i]),
                vaga.get("id", str(i)),
                vaga.get("title", "Sem título"),
            )
            for i, vaga in enumerate(vagas)
        ]

        resultados.sort(key=lambda r: r.score_final, reverse=True)
        return resultados[:top_n] if top_n else resultados

    def match_one(self, resume_text, job_text, job_id="job_1", job_title="Vaga"):
        return self.comparar_um(resume_text, job_text, job_id, job_title)

    def match_many(self, resume_text, jobs, top_n=None):
        return self.comparar_varios(resume_text, jobs, top_n)


matcher_semantico = MatcherSemantico()
