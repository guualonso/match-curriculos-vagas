

from __future__ import annotations

import os
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# ---------------------------------------------------------------------------
# Configuração da conexão
# ---------------------------------------------------------------------------

def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        # Fallback: SQLite local — zero configuração, ideal para dev
        db_path = os.path.join(os.path.dirname(__file__), "..", "resume_matcher.db")
        db_path = os.path.abspath(db_path).replace("\\", "/")
        return f"sqlite:///{db_path}"
    # Garante que a URL está em ASCII puro (evita UnicodeDecodeError no Windows)
    return url.encode("utf-8").decode("ascii", errors="ignore") if url.isascii() else url


DATABASE_URL = _get_database_url()

# SQLite precisa de check_same_thread=False para funcionar com FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class Resume(Base):
    """Currículo enviado pelo usuário."""

    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text)
    extracted_skills = Column(JSON)          # Dict[str, List[str]]
    created_at = Column(DateTime, default=datetime.utcnow)

    matches = relationship("MatchHistory", back_populates="resume", cascade="all, delete")

    def __repr__(self):
        return f"<Resume id={self.id} filename={self.filename!r}>"


class Job(Base):
    """Descrição de vaga cadastrada."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255))
    description = Column(Text, nullable=False)
    cleaned_text = Column(Text)
    extracted_skills = Column(JSON)          # Dict[str, List[str]]
    source = Column(String(100))             # linkedin, indeed, manual, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    matches = relationship("MatchHistory", back_populates="job", cascade="all, delete")

    def __repr__(self):
        return f"<Job id={self.id} title={self.title!r}>"


class MatchHistory(Base):
    """Histórico de matchings realizados."""

    __tablename__ = "match_history"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    similarity_score = Column(Float, nullable=False)
    similarity_percent = Column(Float, nullable=False)
    compatibility_level = Column(String(20))  # Alto / Médio / Baixo

    matching_skills = Column(JSON)    # List[str]
    missing_skills = Column(JSON)     # List[str]
    extra_skills = Column(JSON)       # List[str]

    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="matches")
    job = relationship("Job", back_populates="matches")

    def __repr__(self):
        return (
            f"<MatchHistory resume={self.resume_id} "
            f"job={self.job_id} score={self.similarity_score:.2f}>"
        )


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Dependency para FastAPI: fornece uma sessão de banco e a fecha ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Cria todas as tabelas no banco (executar na inicialização)."""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Remove todas as tabelas (usar com cuidado — apenas em dev/testes)."""
    Base.metadata.drop_all(bind=engine)
