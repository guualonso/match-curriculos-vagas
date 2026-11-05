from __future__ import annotations

import io

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import Job, MatchHistory, Resume
from src.preprocessamento.limpador_texto import limpar_texto as clean_text
from src.extraction.skills_extractor import extrator as skills_extractor
from src.utils.leitor_arquivo import leitor as file_reader
from src.matching.matcher import MatcherCurriculoVaga as ResumeJobMatcher
from src.matching.semantic_matcher import matcher_semantico

MAX_FILE_SIZE = 10 * 1024 * 1024

LIMIAR_COMPATIVEL = 0.40

matcher_tfidf = ResumeJobMatcher()


def normalizar_metodo(metodo: str | None) -> str:
    return "sbert" if (metodo or "").lower() == "sbert" else "tfidf"


def obter_motor(metodo: str):
    return matcher_semantico if metodo == "sbert" else matcher_tfidf


async def processar_upload(arquivo: UploadFile) -> dict:
    nome_arquivo = arquivo.filename or "curriculo"

    if not file_reader.formato_suportado(nome_arquivo):
        raise HTTPException(status_code=400, detail="Formato não suportado. Use PDF, DOCX ou TXT.")

    conteudo = await arquivo.read()

    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    if len(conteudo) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo permitido: 10MB.")

    try:
        texto_bruto = file_reader.ler(io.BytesIO(conteudo), nome_arquivo=nome_arquivo)
    except IOError as erro:
        raise HTTPException(status_code=422, detail=f"Erro ao processar arquivo: {erro}")
    except Exception as erro:
        raise HTTPException(status_code=500, detail=f"Erro inesperado ao processar arquivo: {erro}")

    if not texto_bruto.strip():
        raise HTTPException(status_code=422, detail="Não foi possível extrair texto do arquivo.")

    return {
        "nome_arquivo": nome_arquivo,
        "raw_text": texto_bruto,
        "cleaned_text": clean_text(texto_bruto),
        "skills": skills_extractor.extrair(texto_bruto),
    }


def salvar_curriculo(database: Session, dados_upload: dict) -> Resume:
    existente = database.query(Resume).filter(Resume.raw_text == dados_upload["raw_text"]).first()
    if existente:
        return existente
    curriculo = Resume(
        filename=dados_upload["nome_arquivo"],
        raw_text=dados_upload["raw_text"],
        cleaned_text=dados_upload["cleaned_text"],
        extracted_skills=dados_upload["skills"],
    )
    database.add(curriculo)
    database.commit()
    database.refresh(curriculo)
    return curriculo


def montar_payload_vagas(vagas: list[Job]) -> list[dict]:
    return [
        {
            "id": str(vaga.id),
            "title": vaga.title,
            "description": vaga.description,
            "texto_limpo": vaga.cleaned_text,
            "skills": (
                [skill for skills in vaga.extracted_skills.values() for skill in skills]
                if vaga.extracted_skills is not None else None
            ),
        }
        for vaga in vagas
    ]


def metodos_compativeis(resultado_tfidf, resultado_sbert, limiar: float = LIMIAR_COMPATIVEL) -> list[str]:
    return [
        metodo
        for metodo, resultado in (("tfidf", resultado_tfidf), ("sbert", resultado_sbert))
        if resultado.score_final >= limiar
    ]


def nota_para_ordenar(item: dict) -> float:
    if len(item["metodos"]) == 1:
        return item[item["metodos"][0]].score_final
    return (item["tfidf"].score_final + item["sbert"].score_final) / 2


def ordenar_por_compatibilidade(itens: list[dict]) -> list[dict]:
    itens.sort(key=lambda item: (len(item["metodos"]), nota_para_ordenar(item)), reverse=True)
    return itens


def unificar_resultados(resultados_tfidf, resultados_sbert, limiar: float = LIMIAR_COMPATIVEL) -> list[dict]:
    sbert_por_vaga = {resultado.id_vaga: resultado for resultado in resultados_sbert}
    itens = []
    for resultado_tfidf in resultados_tfidf:
        resultado_sbert = sbert_por_vaga[resultado_tfidf.id_vaga]
        itens.append({
            "tfidf": resultado_tfidf,
            "sbert": resultado_sbert,
            "metodos": metodos_compativeis(resultado_tfidf, resultado_sbert, limiar),
        })
    return ordenar_por_compatibilidade(itens)


def curriculos_distintos(database: Session) -> list[Resume]:
    por_texto: dict[str, Resume] = {}
    for curriculo in database.query(Resume).order_by(Resume.id.desc()):
        por_texto.setdefault(curriculo.raw_text, curriculo)
    return list(por_texto.values())


def comparar_vaga_com_curriculos(vaga: Job, curriculos: list[Resume]) -> list[dict]:
    itens = []
    for curriculo in curriculos:
        argumentos = (curriculo.raw_text, vaga.description, str(vaga.id), vaga.title)
        resultado_tfidf = matcher_tfidf.comparar_um(*argumentos)
        resultado_sbert = matcher_semantico.comparar_um(*argumentos)
        itens.append({
            "curriculo": curriculo,
            "tfidf": resultado_tfidf,
            "sbert": resultado_sbert,
            "metodos": metodos_compativeis(resultado_tfidf, resultado_sbert),
        })
    return ordenar_por_compatibilidade(itens)


def salvar_historico(database: Session, id_curriculo: int, resultado, metodo: str = "tfidf") -> None:
    dados = resultado.para_dict()
    database.add(MatchHistory(
        resume_id=id_curriculo,
        job_id=int(resultado.id_vaga),
        metodo=metodo,
        similarity_score=resultado.score_final,
        similarity_percent=resultado.score_percentual,
        compatibility_level=resultado.nivel_compatibilidade(),
        score_tfidf=dados.get("tfidf_score", 0.0),
        score_skills=dados.get("skills_score", 0.0),
        matching_skills=resultado.skills_comum,
        missing_skills=resultado.skills_ausentes,
        extra_skills=resultado.skills_extras,
    ))
