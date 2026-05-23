from __future__ import annotations

import io
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
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
from src.preprocessamento.limpador_texto import limpar_texto as clean_text
from src.extraction.skills_extractor import extrator as skills_extractor
from src.utils.leitor_arquivo import leitor as file_reader
from src.matching.matcher import MatcherCurriculoVaga as ResumeJobMatcher

router = APIRouter()
matcher = ResumeJobMatcher()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def processar_upload(file: UploadFile):
    """
    Processa upload de currículo:
    - valida formato
    - extrai texto
    - limpa texto
    - extrai skills
    """

    nome_arquivo = file.filename or "curriculo"

    if not file_reader.formato_suportado(nome_arquivo):
        raise HTTPException(
            status_code=400,
            detail="Formato não suportado. Use PDF, DOCX ou TXT.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Arquivo vazio.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Arquivo muito grande. Máximo permitido: 10MB.",
        )

    try:
        raw_text = file_reader.ler(
            io.BytesIO(content),
            nome_arquivo=nome_arquivo,
        )

    except IOError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Erro ao processar arquivo: {e}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar arquivo: {e}",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Não foi possível extrair texto do arquivo.",
        )

    cleaned = clean_text(raw_text)
    skills = skills_extractor.extrair(raw_text)

    return {
        "nome_arquivo": nome_arquivo,
        "raw_text": raw_text,
        "cleaned_text": cleaned,
        "skills": skills,
    }


# ---------------------------------------------------------------------------
# VAGAS
# ---------------------------------------------------------------------------

@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar vaga",
    tags=["Vagas"],
)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
):
    """
    Cadastra uma nova vaga.
    """

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
    """
    Lista vagas cadastradas.
    """

    total = db.query(Job).count()

    jobs = (
        db.query(Job)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return JobList(
        total=total,
        jobs=jobs,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Detalhar vaga",
    tags=["Vagas"],
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):

    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Vaga não encontrada.",
        )

    return job


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover vaga",
    tags=["Vagas"],
)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    Remove uma vaga.
    """

    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Vaga não encontrada.",
        )

    db.delete(job)
    db.commit()


# ---------------------------------------------------------------------------
# CURRÍCULOS
# ---------------------------------------------------------------------------

@router.post(
    "/resumes/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de currículo",
    tags=["Currículos"],
)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Faz upload de currículo.
    """

    data = await processar_upload(file)

    resume = Resume(
        filename=data["nome_arquivo"],
        raw_text=data["raw_text"],
        cleaned_text=data["cleaned_text"],
        extracted_skills=data["skills"],
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
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
):
    """
    Retorna currículo específico.
    """

    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Currículo não encontrado.",
        )

    return resume


# ---------------------------------------------------------------------------
# MATCHING
# ---------------------------------------------------------------------------

@router.post(
    "/match/resume/{resume_id}",
    response_model=MatchResponse,
    summary="Matchear currículo com vagas",
    tags=["Matching"],
)
def match_resume_with_jobs(
    resume_id: int,
    top_n: Optional[int] = Query(
        10,
        ge=1,
        le=50,
    ),
    db: Session = Depends(get_db),
):
    """
    Faz matching entre currículo e vagas.
    """

    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Currículo não encontrado.",
        )

    jobs = db.query(Job).all()

    if not jobs:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma vaga cadastrada.",
        )

    jobs_payload = [
        {
            "id": str(j.id),
            "title": j.title,
            "description": j.description,
        }
        for j in jobs
    ]

    results = matcher.match_many(
        resume.raw_text,
        jobs_payload,
        top_n=top_n,
    )

    for r in results:

        history = MatchHistory(
            resume_id=resume.id,
            job_id=int(r.id_vaga),
            similarity_score=r.score_final,
            similarity_percent=r.score_percentual,
            compatibility_level=r.nivel_compatibilidade(),
            matching_skills=r.skills_comum,
            missing_skills=r.skills_ausentes,
            extra_skills=r.skills_extras,
        )

        db.add(history)

    db.commit()

    return MatchResponse(
        resume_id=resume.id,
        resume_nome_arquivo=resume.filename,
        total_jobs_analyzed=len(jobs),
        results=[
            MatchResultSchema(**r.para_dict())
            for r in results
        ],
    )


@router.post(
    "/match/quick",
    response_model=QuickMatchResponse,
    summary="Match rápido",
    tags=["Matching"],
)
def quick_match(
    payload: QuickMatchRequest,
):
    """
    Matching rápido sem upload.
    """

    result = matcher.match_one(
        resume_text=payload.resume_text,
        job_text=payload.job_description,
        job_id="quick",
        job_title=payload.job_title or "Vaga",
    )

    return QuickMatchResponse(
        result=MatchResultSchema(
            **result.para_dict()
        )
    )


@router.post(
    "/match/upload-and-match",
    response_model=MatchResponse,
    summary="Upload + Match",
    tags=["Matching"],
)
async def upload_and_match(
    file: UploadFile = File(...),
    top_n: int = Form(10),
    db: Session = Depends(get_db),
):
    """
    Faz upload do currículo e matching em uma única chamada.
    """

    data = await processar_upload(file)

    resume = Resume(
        filename=data["nome_arquivo"],
        raw_text=data["raw_text"],
        cleaned_text=data["cleaned_text"],
        extracted_skills=data["skills"],
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    jobs = db.query(Job).all()

    if not jobs:

        return MatchResponse(
            resume_id=resume.id,
            resume_nome_arquivo=resume.filename,
            total_jobs_analyzed=0,
            results=[],
        )

    jobs_payload = [
        {
            "id": str(j.id),
            "title": j.title,
            "description": j.description,
        }
        for j in jobs
    ]

    results = matcher.match_many(
        data["raw_text"],
        jobs_payload,
        top_n=top_n,
    )

    for r in results:

        history = MatchHistory(
            resume_id=resume.id,
            job_id=int(r.id_vaga),
            similarity_score=r.score_final,
            similarity_percent=r.score_percentual,
            compatibility_level=r.nivel_compatibilidade(),
            matching_skills=r.skills_comum,
            missing_skills=r.skills_ausentes,
            extra_skills=r.skills_extras,
        )

        db.add(history)

    db.commit()

    return MatchResponse(
        resume_id=resume.id,
        resume_nome_arquivo=resume.filename,
        total_jobs_analyzed=len(jobs),
        results=[
            MatchResultSchema(**r.para_dict())
            for r in results
        ],
    )


# ---------------------------------------------------------------------------
# HISTÓRICO
# ---------------------------------------------------------------------------

@router.get(
    "/history/resume/{resume_id}",
    response_model=List[MatchHistoryResponse],
    summary="Histórico de matches",
    tags=["Histórico"],
)
def get_history_by_resume(
    resume_id: int,
    db: Session = Depends(get_db),
):
    """
    Retorna histórico de matches do currículo.
    """

    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Currículo não encontrado.",
        )

    return resume.matches