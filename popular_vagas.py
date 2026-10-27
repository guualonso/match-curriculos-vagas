"""
popular_vagas.py — Cadastra no banco uma amostra das vagas do dataset.

Lê data/processado/vagas_processadas.json (gerado por preparar_vagas.py), sorteia
`--quantidade` vagas (semente fixa, reproduzível) e grava cada uma com o texto
pré-processado e as habilidades já calculados, como faz o cadastro pela interface.
Assim as buscas não precisam reprocessar as vagas.

Também recalcula o texto limpo e as habilidades das vagas que já estavam no banco,
para que todas usem a versão atual do pré-processamento e do extrator.

Uso:
    python popular_vagas.py --quantidade 300
"""

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Job, SessionLocal, create_tables
from src.extraction.skills_extractor import extrator
from src.preprocessamento.limpador_texto import limpar_texto

ARQUIVO_VAGAS = os.path.join("data", "processado", "vagas_processadas.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantidade", type=int, default=300, help="Número de vagas a cadastrar.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    create_tables()
    database = SessionLocal()
    try:
        existentes = database.query(Job).all()
        for vaga in existentes:
            vaga.cleaned_text = limpar_texto(vaga.description)
            vaga.extracted_skills = extrator.extrair(vaga.description)
        print(f"{len(existentes)} vagas já cadastradas foram recalculadas.")

        descricoes_existentes = {vaga.description for vaga in existentes}
        with open(ARQUIVO_VAGAS, encoding="utf-8") as arquivo:
            candidatas = [v for v in json.load(arquivo) if v["descricao"] not in descricoes_existentes]
        sorteadas = random.Random(args.seed).sample(candidatas, min(args.quantidade, len(candidatas)))

        for numero, vaga in enumerate(sorteadas, start=1):
            database.add(Job(
                title=vaga["titulo"] or "Sem título",
                company=vaga.get("empresa"),
                description=vaga["descricao"],
                cleaned_text=limpar_texto(vaga["descricao"]),
                extracted_skills=extrator.extrair(vaga["descricao"]),
                source=vaga.get("fonte") or "dataset",
            ))
            if numero % 50 == 0:
                print(f"  {numero}/{len(sorteadas)} vagas processadas...")

        database.commit()
        print(f"{len(sorteadas)} vagas cadastradas. Total no banco: {database.query(Job).count()}.")
    finally:
        database.close()


if __name__ == "__main__":
    main()
