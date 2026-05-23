"""
Script de importação do dataset do Kaggle.
Combina múltiplas colunas do CSV para montar o texto completo do currículo,
processa e salva em data/processado/curriculos_processados.json
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.preprocessamento.limpador_texto import limpar_texto
from src.extraction.skills_extractor import extrator

CAMINHO_RAW        = os.path.join("data", "raw", "resume_data.csv")
CAMINHO_PROCESSADO = os.path.join("data", "processado", "curriculos_processados.json")

# Colunas do dataset que compõem o texto do currículo
COLUNAS_TEXTO = [
    "career_objective",
    "skills",
    "related_skils_in_job",
    "responsibilities",
    "responsibilities.1",
    "positions",
    "major_field_of_studies",
    "degree_names",
    "certification_skills",
]

# Coluna que representa o cargo/área (usada como categoria)
COLUNA_CARGO = "\ufeffjob_position_name"  # BOM no início do nome


def montar_texto(linha: dict) -> str:
    """Combina as colunas relevantes em um único texto de currículo."""
    partes = []
    for col in COLUNAS_TEXTO:
        valor = linha.get(col, "").strip()
        if valor and valor not in ("-", "N/A", "None", "nan"):
            partes.append(valor)
    return " | ".join(partes)


def importar(limite: int | None = None, visualizar: bool = False):
    if not os.path.exists(CAMINHO_RAW):
        print(f" Arquivo não encontrado: {CAMINHO_RAW}")
        return

    print(f" Lendo {CAMINHO_RAW}...\n")

    registros = []
    erros = 0

    with open(CAMINHO_RAW, encoding="utf-8-sig", errors="ignore") as f:
        leitor = csv.DictReader(f)

        for i, linha in enumerate(leitor):
            if limite and i >= limite:
                break

            texto_bruto = montar_texto(linha)
            cargo = linha.get(COLUNA_CARGO, "").strip()

            if not texto_bruto or len(texto_bruto) < 30:
                erros += 1
                continue

            if visualizar and i < 3:
                print(f"── Amostra {i+1} ──────────────────────")
                print(f"Cargo : {cargo}")
                print(f"Texto : {texto_bruto[:300]}")
                print()

            try:
                texto_limpo  = limpar_texto(texto_bruto)
                skills       = extrator.extrair(texto_bruto)
                skills_lista = extrator.extrair_lista(texto_bruto)

                registros.append({
                    "id":           i + 1,
                    "categoria":    cargo,
                    "texto_bruto":  texto_bruto[:3000],
                    "texto_limpo":  texto_limpo[:3000],
                    "skills":       skills,
                    "skills_lista": skills_lista,
                    "total_skills": len(skills_lista),
                })
            except Exception as e:
                erros += 1
                if erros <= 3:
                    print(f"⚠️  Erro no registro {i}: {e}")

    if visualizar:
        print(f"   Total no CSV        : {i + 1}")
        print(f"   Válidos processados : {len(registros)}")
        print(f"   Ignorados           : {erros}")

        # Mostra distribuição de skills
        contagem: dict = {}
        for r in registros:
            for s in r["skills_lista"]:
                contagem[s] = contagem.get(s, 0) + 1
        top = sorted(contagem.items(), key=lambda x: x[1], reverse=True)[:15]
        print("\n📈 Top 15 skills detectadas na amostra:")
        for skill, cnt in top:
            print(f"   {skill:<22} {cnt}")
        print("\n(modo visualização — nenhum arquivo foi salvo)")
        return

    # Salva JSON
    os.makedirs(os.path.dirname(CAMINHO_PROCESSADO), exist_ok=True)
    with open(CAMINHO_PROCESSADO, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    print(f" {len(registros)} currículos processados.")
    print(f"   {erros} registros ignorados.")
    print(f"   Salvo em: {CAMINHO_PROCESSADO}")

    # Resumo
    contagem: dict = {}
    for r in registros:
        for s in r["skills_lista"]:
            contagem[s] = contagem.get(s, 0) + 1
    top = sorted(contagem.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\n📈 Top 10 skills no dataset:")
    for skill, cnt in top:
        print(f"   {skill:<22} {cnt} currículos")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite",     type=int,            help="Limitar número de registros")
    parser.add_argument("--visualizar", action="store_true", help="Só visualiza, não salva")
    args = parser.parse_args()

    importar(limite=args.limite, visualizar=args.visualizar)