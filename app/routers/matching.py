from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import Job, get_db
from app.routers.curriculos import buscar_curriculo_ou_404
from app.routers.vagas import buscar_vaga_ou_404
from app.schemas import (
    JobResumesResponse,
    MatchResponse,
    MatchResultSchema,
    QuickMatchRequest,
    QuickMatchResponse,
    ResumeMatchResult,
    UnifiedMatchResponse,
    UnifiedMatchResult,
)
from app.services.matching_service import (
    comparar_vaga_com_curriculos,
    curriculos_distintos,
    matcher_tfidf,
    metodos_compativeis,
    montar_payload_vagas,
    processar_upload,
    salvar_curriculo,
    salvar_historico,
    unificar_resultados,
)
from src.matching.semantic_matcher import matcher_semantico

router = APIRouter(prefix="/match", tags=["Matching"])


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
    argumentos = dict(
        resume_text=payload.resume_text,
        job_text=payload.job_description,
        job_id="quick",
        job_title=payload.job_title or "Vaga",
    )
    resultado_tfidf = matcher_tfidf.match_one(**argumentos)
    resultado_sbert = matcher_semantico.match_one(**argumentos)
    return QuickMatchResponse(
        metodos=metodos_compativeis(resultado_tfidf, resultado_sbert),
        tfidf=MatchResultSchema(**resultado_tfidf.para_dict()),
        sbert=MatchResultSchema(**resultado_sbert.para_dict()),
    )


@router.post("/upload-and-match", response_model=UnifiedMatchResponse, summary="Upload + Match")
async def upload_and_match(
    file: UploadFile = File(...),
    limite_vagas: int = Form(0),
    database: Session = Depends(get_db),
):
    dados_upload = await processar_upload(file)
    curriculo = salvar_curriculo(database, dados_upload)

    consulta = database.query(Job).order_by(Job.id.desc())
    vagas = consulta.limit(limite_vagas).all() if limite_vagas > 0 else consulta.all()
    if not vagas:
        return UnifiedMatchResponse(
            resume_id=curriculo.id, resume_filename=curriculo.filename, total_jobs_analyzed=0, results=[]
        )

    payload_vagas = montar_payload_vagas(vagas)
    texto = dados_upload["raw_text"]
    unificados = unificar_resultados(
        matcher_tfidf.match_many(texto, payload_vagas),
        matcher_semantico.match_many(texto, payload_vagas),
    )

    for item in (item for item in unificados if item["metodos"]):
        salvar_historico(database, curriculo.id, item["tfidf"], "tfidf")
        salvar_historico(database, curriculo.id, item["sbert"], "sbert")
    database.commit()

    return UnifiedMatchResponse(
        resume_id=curriculo.id,
        resume_filename=curriculo.filename,
        total_jobs_analyzed=len(vagas),
        results=[
            UnifiedMatchResult(
                job_id=item["tfidf"].id_vaga,
                job_title=item["tfidf"].titulo_vaga,
                metodos=item["metodos"],
                tfidf=MatchResultSchema(**item["tfidf"].para_dict()),
                sbert=MatchResultSchema(**item["sbert"].para_dict()),
            )
            for item in unificados
        ],
    )


@router.get("/job/{job_id}/resumes", response_model=JobResumesResponse, summary="Currículos para uma vaga")
def curriculos_para_vaga(job_id: int, database: Session = Depends(get_db)):
    vaga = buscar_vaga_ou_404(database, job_id)
    curriculos = curriculos_distintos(database)
    itens = comparar_vaga_com_curriculos(vaga, curriculos)
    return JobResumesResponse(
        job_id=vaga.id,
        job_title=vaga.title,
        total_resumes_analyzed=len(curriculos),
        results=[
            ResumeMatchResult(
                resume_id=item["curriculo"].id,
                resume_filename=item["curriculo"].filename,
                metodos=item["metodos"],
                tfidf=MatchResultSchema(**item["tfidf"].para_dict()),
                sbert=MatchResultSchema(**item["sbert"].para_dict()),
            )
            for item in itens
        ],
    )
