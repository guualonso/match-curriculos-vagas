import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Resume, SessionLocal, create_tables
from src.extraction.skills_extractor import extrator
from src.preprocessamento.limpador_texto import limpar_texto

PASTA = os.path.join("data", "processado")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantidade", type=int, default=100, help="Número de currículos a cadastrar.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    with open(os.path.join(PASTA, "split_curriculos.json"), encoding="utf-8") as arquivo:
        ids_teste = {id_curriculo for id_curriculo, conjunto in json.load(arquivo).items() if conjunto == "teste"}
    with open(os.path.join(PASTA, "curriculos_processados.json"), encoding="utf-8") as arquivo:
        candidatos = [c for c in json.load(arquivo) if str(c["id"]) in ids_teste and c.get("skills_lista")]

    create_tables()
    database = SessionLocal()
    try:
        textos_existentes = {texto for (texto,) in database.query(Resume.raw_text)}
        candidatos = [c for c in candidatos if c["texto_bruto"] not in textos_existentes]
        sorteados = random.Random(args.seed).sample(candidatos, min(args.quantidade, len(candidatos)))

        for curriculo in sorteados:
            cargo = curriculo.get("categoria") or "sem cargo"
            database.add(Resume(
                filename=f"Currículo {curriculo['id']} ({cargo})",
                raw_text=curriculo["texto_bruto"],
                cleaned_text=limpar_texto(curriculo["texto_bruto"]),
                extracted_skills=extrator.extrair(curriculo["texto_bruto"]),
            ))
        database.commit()
        print(f"{len(sorteados)} currículos cadastrados. Total no banco: {database.query(Resume).count()}.")
    finally:
        database.close()


if __name__ == "__main__":
    main()
