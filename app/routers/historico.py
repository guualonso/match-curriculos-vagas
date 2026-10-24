from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import MatchHistory, get_db
from app.routers.curriculos import buscar_curriculo_ou_404
from app.schemas import MatchHistoryResponse

router = APIRouter(prefix="/history", tags=["Histórico"])


@router.get("/resume/{resume_id}", response_model=List[MatchHistoryResponse], summary="Histórico de matches")
def get_history_by_resume(resume_id: int, database: Session = Depends(get_db)):
    return buscar_curriculo_ou_404(database, resume_id).matches


@router.get("/recent", response_model=List[MatchHistoryResponse], summary="Histórico recente")
def historico_recente(
    limit: int = Query(10, ge=1, le=100),
    database: Session = Depends(get_db),
):
    return (
        database.query(MatchHistory)
        .order_by(MatchHistory.created_at.desc())
        .limit(limit)
        .all()
    )
