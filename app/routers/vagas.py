from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import Job, get_db
from app.schemas import JobCreate, JobList, JobResponse
from src.preprocessamento.limpador_texto import limpar_texto as clean_text
from src.extraction.skills_extractor import extrator as skills_extractor

router = APIRouter(prefix="/jobs", tags=["Vagas"])


def buscar_vaga_ou_404(database: Session, id_vaga: int) -> Job:
    vaga = database.query(Job).filter(Job.id == id_vaga).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")
    return vaga


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED, summary="Cadastrar vaga")
def create_job(payload: JobCreate, database: Session = Depends(get_db)):
    vaga = Job(
        title=payload.title,
        company=payload.company,
        description=payload.description,
        cleaned_text=clean_text(payload.description),
        extracted_skills=skills_extractor.extrair(payload.description),
        source=payload.source,
    )
    database.add(vaga)
    database.commit()
    database.refresh(vaga)
    return vaga


@router.get("", response_model=JobList, summary="Listar vagas")
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    database: Session = Depends(get_db),
):
    total = database.query(Job).count()
    vagas = database.query(Job).offset(skip).limit(limit).all()
    return JobList(total=total, jobs=vagas)


@router.get("/{job_id}", response_model=JobResponse, summary="Detalhar vaga")
def get_job(job_id: int, database: Session = Depends(get_db)):
    return buscar_vaga_ou_404(database, job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover vaga")
def delete_job(job_id: int, database: Session = Depends(get_db)):
    vaga = buscar_vaga_ou_404(database, job_id)
    database.delete(vaga)
    database.commit()
