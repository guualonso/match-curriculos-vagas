from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import Job, get_db
from app.routers.curriculos import buscar_curriculo_ou_404
from app.schemas import MatchResponse, MatchResultSchema, QuickMatchRequest, QuickMatchResponse
from app.services.matching_service import (
    matcher_tfidf,
    montar_payload_vagas,
    normalizar_metodo,
    obter_motor,
    processar_upload,
    salvar_curriculo,
    salvar_historico,
)
from src.matching.semantic_matcher import matcher_semantico

router = APIRouter(prefix="/match", tags=["Matching"])

SALVAR_NO_HISTORICO = 10  # melhores resultados de cada método gravados no comparativo
LIMITE_RESPOSTA_COMPARATIVO = 50


def montar_resposta(curriculo, total_vagas: int, resultados) -> MatchResponse:
    return MatchResponse(
        resume_id=curriculo.id,
        resume_nome_arquivo=curriculo.filename,
        total_jobs_analyzed=total_vagas,
        results=[MatchResultSchema(**resultado.para_dict()) for resultado in resultados],
    )


@router.post("/resume/{resume_id}", response_model=MatchResponse, summary="Matchear currículo com vagas")
def match_resume_with_jobs(
    resume_id: int,
    top_n: Optional[int] = Query(10, ge=1, le=50),
    database: Session = Depends(get_db),
):
    curriculo = buscar_curriculo_ou_404(database, resume_id)

    vagas = database.query(Job).all()
    if not vagas:
        raise HTTPException(status_code=404, detail="Nenhuma vaga cadastrada.")

    resultados = matcher_tfidf.match_many(curriculo.raw_text, montar_payload_vagas(vagas), top_n=top_n)

    for resultado in resultados:
        salvar_historico(database, curriculo.id, resultado, "tfidf")
    database.commit()

    return montar_resposta(curriculo, len(vagas), resultados)


@router.post("/quick", response_model=QuickMatchResponse, summary="Match rápido")
def quick_match(payload: QuickMatchRequest):
    """Matching rápido sem upload. `metodo`: 'tfidf' (padrão) ou 'sbert'."""
    resultado = obter_motor(normalizar_metodo(payload.metodo)).match_one(
        resume_text=payload.resume_text,
        job_text=payload.job_description,
        job_id="quick",
        job_title=payload.job_title or "Vaga",
    )
    return QuickMatchResponse(result=MatchResultSchema(**resultado.para_dict()))


@router.post("/upload-and-match", response_model=MatchResponse, summary="Upload + Match")
async def upload_and_match(
    file: UploadFile = File(...),
    top_n: int = Form(10),
    metodo: str = Form("tfidf"),
    database: Session = Depends(get_db),
):
    """Upload do currículo e matching numa única chamada. `metodo`: 'tfidf' (padrão) ou 'sbert'."""
    dados_upload = await processar_upload(file)
    curriculo = salvar_curriculo(database, dados_upload)

    vagas = database.query(Job).all()
    if not vagas:
        return montar_resposta(curriculo, 0, [])

    metodo = normalizar_metodo(metodo)
    resultados = obter_motor(metodo).match_many(
        dados_upload["raw_text"], montar_payload_vagas(vagas), top_n=top_n
    )

    for resultado in resultados:
        salvar_historico(database, curriculo.id, resultado, metodo)
    database.commit()

    return montar_resposta(curriculo, len(vagas), resultados)


@router.post("/compare", summary="Comparar TF-IDF vs SBERT")
async def compare_methods(
    file: UploadFile = File(...),
    top_n: int = Form(5),
    database: Session = Depends(get_db),
):
    """Roda os dois matchers sobre o mesmo currículo e as mesmas vagas."""
    dados_upload = await processar_upload(file)

    vagas = database.query(Job).all()
    if not vagas:
        return {"tfidf": [], "sbert": []}

    curriculo = salvar_curriculo(database, dados_upload)
    payload_vagas = montar_payload_vagas(vagas)

    resultados_tfidf = matcher_tfidf.match_many(dados_upload["raw_text"], payload_vagas, top_n=None)
    resultados_sbert = matcher_semantico.match_many(dados_upload["raw_text"], payload_vagas, top_n=None)

    for resultado in resultados_tfidf[:SALVAR_NO_HISTORICO]:
        salvar_historico(database, curriculo.id, resultado, "tfidf")
    for resultado in resultados_sbert[:SALVAR_NO_HISTORICO]:
        salvar_historico(database, curriculo.id, resultado, "sbert")
    database.commit()

    return {
        "tfidf": [resultado.para_dict() for resultado in resultados_tfidf[:LIMITE_RESPOSTA_COMPARATIVO]],
        "sbert": [resultado.para_dict() for resultado in resultados_sbert[:LIMITE_RESPOSTA_COMPARATIVO]],
    }
