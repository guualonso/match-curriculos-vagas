"""
Rotas da API FastAPI.
Endpoints para gerenciamento de vagas, upload de currículos e matching.
"""

from __future__ import annotations

import io
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import Job, MatchHistory, Resume, get_db
from app.schemas import (
    JobCreate,
    JobList,
    JobResponse,
    MatchHistoryResponse,
    MatchResponse,
    MatchResultSchema,
    QuickMatchRequest,
    QuickMatchResponse,
    ResumeResponse,
)
from src.extraction.skills_extractor import extrator as skills_extractor
from src.matching.matcher import ResumeJobMatcher
from src.preprocessamento.text_cleaner import limpar_texto as clean_text
from src.utils.file_reader import leitor as file_reader

router = APIRouter()
matcher = ResumeJobMatcher()


# ---------------------------------------------------------------------------
# Vagas
# ---------------------------------------------------------------------------

@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar vaga",
    tags=["Vagas"],
)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    """Cadastra uma nova vaga e extrai suas habilidades técnicas automaticamente."""
    cleaned = clean_text(payload.description)
    skills = skills_extractor.extrair(payload.description)

    job = Job(
        title=payload.title,
        company=payload.company,
        description=payload.description,
        cleaned_text=cleaned,
        extracted_skills=skills,
        source=payload.source,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get(
    "/jobs",
    response_model=JobList,
    summary="Listar vagas",
    tags=["Vagas"],
)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retorna a lista de vagas cadastradas com paginação."""
    total = db.query(Job).count()
    jobs = db.query(Job).offset(skip).limit(limit).all()
    return JobList(total=total, jobs=jobs)


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Detalhar vaga",
    tags=["Vagas"],
)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Retorna os detalhes de uma vaga específica."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")
    return job


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover vaga",
    tags=["Vagas"],
)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Remove uma vaga do sistema."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")
    db.delete(job)
    db.commit()


# ---------------------------------------------------------------------------
# Currículos
# ---------------------------------------------------------------------------

@router.post(
    "/resumes/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de currículo",
    tags=["Currículos"],
)
async def upload_resume(
    file: UploadFile = File(..., description="Arquivo PDF ou DOCX do currículo"),
    db: Session = Depends(get_db),
):
    """
    Recebe upload de currículo (PDF ou DOCX),
    extrai o texto e identifica as habilidades técnicas.
    """
    filename = file.filename or "currículo"

    if not file_reader.formato_suportado(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use PDF, DOCX ou TXT.",
        )

    content = await file.read()
    try:
        raw_text = file_reader.ler(io.BytesIO(content), filename=filename)
    except IOError as e:
        raise HTTPException(status_code=422, detail=f"Erro ao processar arquivo: {e}")

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Não foi possível extrair texto do arquivo.")

    cleaned = clean_text(raw_text)
    skills = skills_extractor.extrair(raw_text)

    resume = Resume(
        filename=filename,
        raw_text=raw_text,
        cleaned_text=cleaned,
        extracted_skills=skills,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get(
    "/resumes/{resume_id}",
    response_model=ResumeResponse,
    summary="Detalhar currículo",
    tags=["Currículos"],
)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """Retorna os detalhes de um currículo processado."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Currículo não encontrado.")
    return resume


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@router.post(
    "/match/resume/{resume_id}",
    response_model=MatchResponse,
    summary="Matchear currículo com vagas",
    tags=["Matching"],
)
def match_resume_with_jobs(
    resume_id: int,
    top_n: Optional[int] = Query(10, ge=1, le=50, description="Número máximo de vagas retornadas"),
    db: Session = Depends(get_db),
):
    """
    Compara um currículo cadastrado com todas as vagas do banco
    e retorna as mais compatíveis ordenadas por score.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Currículo não encontrado.")

    jobs = db.query(Job).all()
    if not jobs:
        raise HTTPException(status_code=404, detail="Nenhuma vaga cadastrada.")

    jobs_payload = [
        {"id": str(j.id), "title": j.title, "description": j.description}
        for j in jobs
    ]

    results = matcher.match_many(resume.raw_text, jobs_payload, top_n=top_n)

    # Persiste histórico no banco
    for r in results:
        history = MatchHistory(
            resume_id=resume.id,
            job_id=int(r.job_id),
            similarity_score=r.similarity_score,
            similarity_percent=r.similarity_percent,
            compatibility_level=r._get_compatibility_level(),
            matching_skills=r.matching_skills,
            missing_skills=r.missing_skills,
            extra_skills=r.extra_skills,
        )
        db.add(history)
    db.commit()

    return MatchResponse(
        resume_id=resume.id,
        resume_filename=resume.filename,
        total_jobs_analyzed=len(jobs),
        results=[MatchResultSchema(**r.para_dict()) for r in results],
    )


@router.post(
    "/match/quick",
    response_model=QuickMatchResponse,
    summary="Match rápido (sem upload)",
    tags=["Matching"],
)
def quick_match(payload: QuickMatchRequest):
    """
    Realiza um matching pontual entre texto de currículo e descrição de vaga,
    sem necessidade de cadastro. Ideal para testes.
    """
    result = matcher.match_one(
        resume_text=payload.resume_text,
        job_text=payload.job_description,
        job_id="quick",
        job_title=payload.job_title or "Vaga",
    )
    return QuickMatchResponse(result=MatchResultSchema(**result.para_dict()))


@router.post(
    "/match/upload-and-match",
    response_model=MatchResponse,
    summary="Upload + match em uma requisição",
    tags=["Matching"],
)
async def upload_and_match(
    file: UploadFile = File(...),
    top_n: int = Form(10),
    db: Session = Depends(get_db),
):
    """
    Faz upload do currículo e já retorna os melhores matches
    em uma única chamada.
    """
    # Reutiliza lógica de upload
    filename = file.filename or "curriculo"
    if not file_reader.formato_suportado(filename):
        raise HTTPException(status_code=400, detail="Formato não suportado.")

    content = await file.read()
    try:
        raw_text = file_reader.ler(io.BytesIO(content), filename=filename)
    except IOError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Arquivo sem texto legível.")

    cleaned = clean_text(raw_text)
    skills = skills_extractor.extrair(raw_text)

    resume = Resume(
        filename=filename,
        raw_text=raw_text,
        cleaned_text=cleaned,
        extracted_skills=skills,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    jobs = db.query(Job).all()
    if not jobs:
        return MatchResponse(
            resume_id=resume.id,
            resume_filename=resume.filename,
            total_jobs_analyzed=0,
            results=[],
        )

    jobs_payload = [
        {"id": str(j.id), "title": j.title, "description": j.description}
        for j in jobs
    ]
    results = matcher.match_many(raw_text, jobs_payload, top_n=top_n)

    for r in results:
        db.add(MatchHistory(
            resume_id=resume.id,
            job_id=int(r.job_id),
            similarity_score=r.similarity_score,
            similarity_percent=r.similarity_percent,
            compatibility_level=r._get_compatibility_level(),
            matching_skills=r.matching_skills,
            missing_skills=r.missing_skills,
            extra_skills=r.extra_skills,
        ))
    db.commit()

    return MatchResponse(
        resume_id=resume.id,
        resume_filename=resume.filename,
        total_jobs_analyzed=len(jobs),
        results=[MatchResultSchema(**r.para_dict()) for r in results],
    )


# ---------------------------------------------------------------------------
# Histórico
# ---------------------------------------------------------------------------

@router.get(
    "/history/resume/{resume_id}",
    response_model=List[MatchHistoryResponse],
    summary="Histórico de matches por currículo",
    tags=["Histórico"],
)
def get_history_by_resume(resume_id: int, db: Session = Depends(get_db)):
    """Retorna o histórico de matchings de um currículo específico."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Currículo não encontrado.")
    return resume.matches
