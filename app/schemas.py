from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, examples=["Desenvolvedor Python Sênior"])
    company: Optional[str] = Field(None, max_length=255, examples=["Tech Corp"])
    description: str = Field(..., min_length=10, examples=["Buscamos desenvolvedor com experiência em Python, FastAPI..."])
    source: Optional[str] = Field(None, max_length=100, examples=["linkedin"])


class JobResponse(BaseModel):
    id: int
    title: str
    company: Optional[str]
    description: str
    extracted_skills: Optional[Dict[str, List[str]]]
    source: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class JobList(BaseModel):
    total: int
    jobs: List[JobResponse]



class ResumeResponse(BaseModel):
    id: int
    filename: str
    extracted_skills: Optional[Dict[str, List[str]]]
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchResultSchema(BaseModel):
    tfidf_score: float = 0.0
    skills_score: float = 0.0
    skill_coverage: float = 0.0
    warning: str = ""
    job_id: str
    job_title: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    similarity_percent: float
    compatibility_level: str
    matching_skills: List[str]
    missing_skills: List[str]
    extra_skills: List[str]


class MatchResponse(BaseModel):
    resume_id: Optional[int] = None
    resume_filename: Optional[str] = None
    total_jobs_analyzed: int
    results: List[MatchResultSchema]


class QuickMatchRequest(BaseModel):
    """Para matching rápido sem upload de arquivo (texto direto)."""
    resume_text: str = Field(..., min_length=10)
    job_description: str = Field(..., min_length=10)
    job_title: Optional[str] = "Vaga"


class QuickMatchResponse(BaseModel):
    result: MatchResultSchema


class MatchHistoryResponse(BaseModel):
    id: int
    resume_id: int
    job_id: int
    similarity_score: float
    similarity_percent: float
    compatibility_level: str
    matching_skills: List[str]
    missing_skills: List[str]
    extra_skills: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    version: str
    model_language: str
