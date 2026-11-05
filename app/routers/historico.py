from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import MatchHistory, get_db
from app.routers.curriculos import buscar_curriculo_ou_404
from app.schemas import HistoryPairResponse
from app.services.matching_service import LIMIAR_COMPATIVEL

router = APIRouter(prefix="/history", tags=["Histórico"])


def agrupar_por_par(registros: list[MatchHistory]) -> list[dict]:
    pares = {}
    for registro in sorted(registros, key=lambda registro: registro.created_at, reverse=True):
        par = pares.setdefault((registro.resume_id, registro.job_id), {
            "resume_id": registro.resume_id,
            "job_id": registro.job_id,
            "created_at": registro.created_at,
        })
        par.setdefault(registro.metodo or "tfidf", registro)
    for par in pares.values():
        par["metodos"] = [
            metodo for metodo in ("tfidf", "sbert")
            if metodo in par and par[metodo].similarity_score >= LIMIAR_COMPATIVEL
        ]
    return list(pares.values())


@router.get("/resume/{resume_id}", response_model=List[HistoryPairResponse], summary="Histórico de matches")
def get_history_by_resume(resume_id: int, database: Session = Depends(get_db)):
    return agrupar_por_par(buscar_curriculo_ou_404(database, resume_id).matches)


@router.get("/recent", response_model=List[HistoryPairResponse], summary="Histórico recente")
def historico_recente(
    limit: int = Query(10, ge=1, le=100),
    database: Session = Depends(get_db),
):
    registros = (
        database.query(MatchHistory)
        .order_by(MatchHistory.created_at.desc(), MatchHistory.id.desc())
        .limit(limit * 2)
        .all()
    )
    return agrupar_por_par(registros)[:limit]
