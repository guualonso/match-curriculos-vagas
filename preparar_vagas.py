import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.extraction.skills_extractor import extrator

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

DIR_RAW        = os.path.join("data", "raw")
CAMINHO_SAIDA  = os.path.join("data", "processado", "vagas_processadas.json")


def _split_skills(valor: str) -> list[str]:
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
