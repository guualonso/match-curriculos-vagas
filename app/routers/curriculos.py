from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import Resume, get_db
from app.schemas import ResumeResponse
from app.services.matching_service import processar_upload, salvar_curriculo

router = APIRouter(prefix="/resumes", tags=["Currículos"])


def buscar_curriculo_ou_404(database: Session, id_curriculo: int) -> Resume:
    curriculo = database.query(Resume).filter(Resume.id == id_curriculo).first()
    if not curriculo:
        raise HTTPException(status_code=404, detail="Currículo não encontrado.")
    return curriculo


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED, summary="Upload de currículo")
async def upload_resume(file: UploadFile = File(...), database: Session = Depends(get_db)):
    dados_upload = await processar_upload(file)
    return salvar_curriculo(database, dados_upload)


@router.get("/{resume_id}", response_model=ResumeResponse, summary="Detalhar currículo")
def get_resume(resume_id: int, database: Session = Depends(get_db)):
    return buscar_curriculo_ou_404(database, resume_id)
