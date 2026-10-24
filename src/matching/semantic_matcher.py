from __future__ import annotations

"""
Matcher semântico baseado em Sentence-BERT (SBERT).

Espelha a interface de ``MatcherCurriculoVaga`` (comparar_um, comparar_varios,
match_one, match_many, retornando ``ResultadoMatch``), de modo que possa ser
usado de forma intercambiável pelo restante do sistema (routers em app/routers, interface).

Diferenças em relação ao matcher TF-IDF:
  * NÃO aplica o pré-processamento agressivo (lematização, remoção de acentos e
    de stopwords). O SBERT opera melhor sobre o texto natural, pois é justamente
    a semântica que essas transformações destruiriam.
  * O score é a similaridade do cosseno entre os embeddings do currículo e da
    vaga. As habilidades ESCO são calculadas apenas para exibição na interface e
    NÃO entram no cálculo do score, conforme o desenho experimental do trabalho
    (o SBERT, por natureza semântica, não depende de enumeração de habilidades).

Se existir um modelo ajustado (fine-tuned) no diretório ``models/sbert_finetuned``,
ele é carregado automaticamente; caso contrário, usa-se o modelo base multilíngue.
"""

import os
from functools import lru_cache
from typing import Dict, List, Optional

from src.extraction.skills_extractor import extrator as extrator_skills
from src.matching.matcher import ResultadoMatch

# Modelo base multilíngue indicado no projeto (suporta português).
MODELO_BASE = "paraphrase-multilingual-MiniLM-L12-v2"

# Diretório onde o script de fine-tuning salva o modelo especializado em TI.
CAMINHO_MODELO_AJUSTADO = os.path.join("models", "sbert_finetuned")


@lru_cache(maxsize=2)
def _carregar_modelo(caminho_ou_nome: str):
    """Carrega (uma única vez) o modelo SentenceTransformer.

    O import é feito aqui dentro para que o restante do sistema não precise da
    dependência pesada (torch/sentence-transformers) quando o matcher semântico
    não estiver em uso.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(caminho_ou_nome)


def _resolver_modelo(preferir_ajustado: bool = True) -> str:
    if preferir_ajustado and os.path.isdir(CAMINHO_MODELO_AJUSTADO):
        return CAMINHO_MODELO_AJUSTADO
    return MODELO_BASE


class MatcherSemantico:
    """Matcher de compatibilidade currículo × vaga baseado em SBERT."""

    def __init__(self, modelo: Optional[str] = None, usar_ajustado: bool = True):
        # Nome do modelo base ou caminho do modelo ajustado.
        self.nome_modelo = modelo or _resolver_modelo(usar_ajustado)
        self._modelo = None  # carregado sob demanda

    @property
    def modelo(self):
        if self._modelo is None:
            self._modelo = _carregar_modelo(self.nome_modelo)
        return self._modelo

    # ------------------------------------------------------------------ #
    # Utilitários internos
    # ------------------------------------------------------------------ #
    def _preparar(self, texto: str) -> str:
        """Limpeza mínima: apenas normaliza espaços, preservando a semântica."""
        return " ".join((texto or "").split())

    def _embeddings(self, textos: List[str]):
        """Gera embeddings L2-normalizados (produto escalar = cosseno)."""
        return self.modelo.encode(
            textos,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    @staticmethod
    def _score(emb_a, emb_b) -> float:
        # Vetores já normalizados => produto escalar equivale ao cosseno.
        return float((emb_a * emb_b).sum())

    def _montar_resultado(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        score_semantico: float,
        id_vaga: str,
        titulo_vaga: str,
    ) -> ResultadoMatch:
        # Habilidades apenas para exibição na interface (não entram no score).
        comparacao = extrator_skills.comparar(texto_curriculo, texto_vaga)
        score = max(0.0, min(score_semantico, 1.0))

        return ResultadoMatch(
            id_vaga=id_vaga,
            titulo_vaga=titulo_vaga,
            score_final=score,
            score_tfidf=0.0,      # não se aplica ao método semântico
            score_skills=0.0,     # não entra no score (apenas exibição das listas)
            cobertura_skills=0.0,
            skills_comum=comparacao["em_comum"],
            skills_ausentes=comparacao["ausentes"],
            skills_extras=comparacao["extras"],
            aviso="",
        )

    # ------------------------------------------------------------------ #
    # Interface pública (espelha MatcherCurriculoVaga)
    # ------------------------------------------------------------------ #
    def comparar_um(
        self,
        texto_curriculo: str,
        texto_vaga: str,
        id_vaga: str = "vaga_1",
        titulo_vaga: str = "Vaga",
    ) -> ResultadoMatch:
        """Compara um currículo com uma única vaga."""
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
        """Compara um currículo com várias vagas, ranqueadas por score decrescente.

        Gera os embeddings de todas as vagas em uma única chamada (batch), o que
        é a principal vantagem de escala do SBERT.
        """
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

    # Aliases para compatibilidade com os routers (mesmos nomes do matcher TF-IDF)
    def match_one(self, resume_text, job_text, job_id="job_1", job_title="Vaga"):
        return self.comparar_um(resume_text, job_text, job_id, job_title)

    def match_many(self, resume_text, jobs, top_n=None):
        return self.comparar_varios(resume_text, jobs, top_n)


# Instância pronta para uso, análoga a ``matcher`` do módulo TF-IDF.
matcher_semantico = MatcherSemantico()
