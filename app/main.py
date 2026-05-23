"""
Aplicação FastAPI — Resume Job Matcher
TCC: Extração de Habilidades Técnicas em Currículos e Análise de Compatibilidade
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import create_tables
from app.routes import router
from app.schemas import HealthResponse

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="Resume Job Matcher",
    description=(
        "API para extração de habilidades técnicas em currículos "
        "e análise de compatibilidade com vagas utilizando PLN, TF-IDF e cosseno."
    ),
    version="1.0.0",
    contact={"name": "Gustavo Moreira Alonso & Pedro Fukuya Ohno"},
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    create_tables()
    print("✅  Banco de dados inicializado.")
    print("🌐  Interface web: http://localhost:8000")
    print("📖  Documentação: http://localhost:8000/docs")


@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
def health_check():
    try:
        import spacy
        spacy.load("pt_core_news_sm")
        lang = "pt"
    except OSError:
        try:
            import spacy
            spacy.load("en_core_web_sm")
            lang = "en"
        except OSError:
            lang = "none"

    return HealthResponse(status="ok", version="1.0.0", model_language=lang)


@app.get("/", include_in_schema=False)
@app.get("/app", include_in_schema=False)
def serve_frontend():
    index = BASE_DIR / "templates" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Resume Job Matcher API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
