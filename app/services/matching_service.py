"""Lógica compartilhada pelos routers: upload, persistência e escolha do motor de matching."""

from __future__ import annotations

import io

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import Job, MatchHistory, Resume
from src.preprocessamento.limpador_texto import limpar_texto as clean_text
from src.extraction.skills_extractor import extrator as skills_extractor
from src.utils.leitor_arquivo import leitor as file_reader
from src.matching.matcher import MatcherCurriculoVaga as ResumeJobMatcher
from src.matching.semantic_matcher import matcher_semantico

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

matcher_tfidf = ResumeJobMatcher()


def normalizar_metodo(metodo: str | None) -> str:
    return "sbert" if (metodo or "").lower() == "sbert" else "tfidf"


def obter_motor(metodo: str):
    return matcher_semantico if metodo == "sbert" else matcher_tfidf


async def processar_upload(arquivo: UploadFile) -> dict:
    """Valida o arquivo, extrai e limpa o texto e extrai as skills."""
    nome_arquivo = arquivo.filename or "curriculo"

    if not file_reader.formato_suportado(nome_arquivo):
        raise HTTPException(status_code=400, detail="Formato não suportado. Use PDF, DOCX ou TXT.")

    conteudo = await arquivo.read()

    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    if len(conteudo) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo permitido: 10MB.")

    try:
        texto_bruto = file_reader.ler(io.BytesIO(conteudo), nome_arquivo=nome_arquivo)
    except IOError as erro:
        raise HTTPException(status_code=422, detail=f"Erro ao processar arquivo: {erro}")
    except Exception as erro:
        raise HTTPException(status_code=500, detail=f"Erro inesperado ao processar arquivo: {erro}")

    if not texto_bruto.strip():
        raise HTTPException(status_code=422, detail="Não foi possível extrair texto do arquivo.")

    return {
        "nome_arquivo": nome_arquivo,
        "raw_text": texto_bruto,
        "cleaned_text": clean_text(texto_bruto),
        "skills": skills_extractor.extrair(texto_bruto),
    }


def salvar_curriculo(database: Session, dados_upload: dict) -> Resume:
    curriculo = Resume(
        filename=dados_upload["nome_arquivo"],
        raw_text=dados_upload["raw_text"],
        cleaned_text=dados_upload["cleaned_text"],
        extracted_skills=dados_upload["skills"],
    )
    database.add(curriculo)
    database.commit()
    database.refresh(curriculo)
    return curriculo


def montar_payload_vagas(vagas: list[Job]) -> list[dict]:
    """Inclui o texto limpo e as habilidades calculados no cadastro, para não reprocessar as vagas."""
    return [
        {
            "id": str(vaga.id),
            "title": vaga.title,
            "description": vaga.description,
            "texto_limpo": vaga.cleaned_text,
            "skills": (
                [skill for skills in vaga.extracted_skills.values() for skill in skills]
                if vaga.extracted_skills is not None else None
            ),
        }
        for vaga in vagas
    ]


def salvar_historico(database: Session, id_curriculo: int, resultado, metodo: str = "tfidf") -> None:
    """Adiciona um ResultadoMatch ao histórico (o commit fica a cargo de quem chama)."""
    dados = resultado.para_dict()
    database.add(MatchHistory(
        resume_id=id_curriculo,
        job_id=int(resultado.id_vaga),
        metodo=metodo,
        similarity_score=resultado.score_final,
        similarity_percent=resultado.score_percentual,
        compatibility_level=resultado.nivel_compatibilidade(),
        score_tfidf=dados.get("tfidf_score", 0.0),
        score_skills=dados.get("skills_score", 0.0),
        matching_skills=resultado.skills_comum,
        missing_skills=resultado.skills_ausentes,
        extra_skills=resultado.skills_extras,
    ))
