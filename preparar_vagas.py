"""
preparar_vagas.py — Unifica os datasets de vagas em um único JSON.

Fontes suportadas:
  * LinkedIn Software Engineering Jobs (asaniczka) — arquivo único 'postings.csv'
    com colunas: job_title, company, ..., job_summary, job_skills.
  * Data Science Job Postings and Skills (asaniczka) — três arquivos ligados por
    'job_link': job_postings.csv (metadados), job_summary.csv (job_summary),
    job_skills.csv (job_skills).

Saída: data/processado/vagas_processadas.json
Cada registro:
  {
    "id": <job_link>,
    "fonte": "linkedin_swe" | "data_science",
    "titulo": str, "empresa": str,
    "descricao": str,                     # texto natural (usado pelo SBERT e TF-IDF)
    "skills_dataset": [str, ...],         # skills que já vêm no dataset
    "skills_extraidas": [str, ...]        # skills detectadas pelo nosso extrator (forma canônica)
  }
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.extraction.skills_extractor import extrator

# csv com campos grandes (job_summary) estoura o limite padrão
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

DIR_RAW        = os.path.join("data", "raw")
CAMINHO_SAIDA  = os.path.join("data", "processado", "vagas_processadas.json")


def _split_skills(valor: str) -> list[str]:
    """Divide a string de skills do dataset (separada por vírgula) em lista limpa."""
    if not valor:
        return []
    return [s.strip() for s in valor.split(",") if s.strip()]


def _registro(job_link, fonte, titulo, empresa, descricao, skills_str):
    descricao = (descricao or "").strip()
    return {
        "id": job_link,
        "fonte": fonte,
        "titulo": (titulo or "").strip(),
        "empresa": (empresa or "").strip(),
        "descricao": descricao,
        "skills_dataset": _split_skills(skills_str),
        "skills_extraidas": sorted(set(extrator.extrair_lista(descricao))),
    }


def processar_linkedin(caminho: str, limite=None) -> list[dict]:
    registros = []
    with open(caminho, encoding="utf-8", errors="ignore", newline="") as f:
        for i, linha in enumerate(csv.DictReader(f)):
            if limite and i >= limite:
                break
            desc = linha.get("job_summary", "")
            if not desc or len(desc) < 30:
                continue
            registros.append(_registro(
                linha.get("job_link") or f"linkedin_{i}",
                "linkedin_swe",
                linha.get("job_title"), linha.get("company"),
                desc, linha.get("job_skills", ""),
            ))
    return registros


def processar_data_science(dir_raw: str, limite=None) -> list[dict]:
    # Índices por job_link para juntar os três arquivos
    summaries, skills = {}, {}
    with open(os.path.join(dir_raw, "job_summary.csv"), encoding="utf-8", errors="ignore", newline="") as f:
        for row in csv.DictReader(f):
            summaries[row["job_link"]] = row.get("job_summary", "")
    with open(os.path.join(dir_raw, "job_skills.csv"), encoding="utf-8", errors="ignore", newline="") as f:
        for row in csv.DictReader(f):
            skills[row["job_link"]] = row.get("job_skills", "")

    registros = []
    with open(os.path.join(dir_raw, "job_postings.csv"), encoding="utf-8", errors="ignore", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if limite and i >= limite:
                break
            link = row["job_link"]
            desc = summaries.get(link, "")
            if not desc or len(desc) < 30:
                continue
            registros.append(_registro(
                link, "data_science",
                row.get("job_title"), row.get("company"),
                desc, skills.get(link, ""),
            ))
    return registros


def main():
    p = argparse.ArgumentParser(description="Unifica os datasets de vagas em um JSON.")
    p.add_argument("--fonte", choices=["linkedin", "data_science", "ambos"], default="ambos")
    p.add_argument("--limite", type=int, help="Limita o nº de vagas por fonte (para testes).")
    p.add_argument("--dir-raw", default=DIR_RAW)
    p.add_argument("--saida", default=CAMINHO_SAIDA)
    args = p.parse_args()

    vagas = []
    if args.fonte in ("linkedin", "ambos"):
        caminho = os.path.join(args.dir_raw, "postings.csv")
        if os.path.exists(caminho):
            vagas += processar_linkedin(caminho, args.limite)
        else:
            print(f"[aviso] {caminho} não encontrado — pulando LinkedIn.")
    if args.fonte in ("data_science", "ambos"):
        if os.path.exists(os.path.join(args.dir_raw, "job_postings.csv")):
            vagas += processar_data_science(args.dir_raw, args.limite)
        else:
            print("[aviso] arquivos do Data Science Postings não encontrados — pulando.")

    # remove vagas sem nenhuma skill detectada (não ajudam no matching técnico)
    vagas = [v for v in vagas if v["skills_extraidas"]]

    os.makedirs(os.path.dirname(args.saida), exist_ok=True)
    with open(args.saida, "w", encoding="utf-8") as f:
        json.dump(vagas, f, ensure_ascii=False, indent=2)

    print(f"{len(vagas)} vagas processadas e salvas em {args.saida}")
    if vagas:
        media = sum(len(v["skills_extraidas"]) for v in vagas) / len(vagas)
        print(f"Média de skills detectadas por vaga: {media:.1f}")


if __name__ == "__main__":
    main()