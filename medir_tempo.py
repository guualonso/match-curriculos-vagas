import argparse
import io
import json
import os
import statistics
import time

from app.database import Job, SessionLocal
from app.services.matching_service import (
    comparar_vaga_com_curriculos,
    curriculos_distintos,
    matcher_semantico,
    matcher_tfidf,
    montar_payload_vagas,
    unificar_resultados,
)
from src.extraction.skills_extractor import extrator
from src.preprocessamento.limpador_texto import limpar_texto
from src.utils.leitor_arquivo import leitor

CAMINHO_CURRICULOS = os.path.join("data", "processado", "curriculos_processados.json")


def cronometrar(funcao, *argumentos):
    inicio = time.perf_counter()
    resultado = funcao(*argumentos)
    return time.perf_counter() - inicio, resultado


def analisar_curriculo(texto_curriculo, vagas):
    inicio = time.perf_counter()
    limpar_texto(texto_curriculo)
    extrator.extrair(texto_curriculo)
    tempo_tfidf, resultados_tfidf = cronometrar(matcher_tfidf.comparar_varios, texto_curriculo, vagas)
    tempo_sbert, resultados_sbert = cronometrar(matcher_semantico.comparar_varios, texto_curriculo, vagas)
    unificar_resultados(resultados_tfidf, resultados_sbert)
    return tempo_tfidf, tempo_sbert, time.perf_counter() - inicio


def resumo(tempos):
    return f"média {statistics.mean(tempos):.2f} s, máximo {max(tempos):.2f} s"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantidade", type=int, default=20, help="Currículos medidos na aba Currículo → Vagas.")
    parser.add_argument("--vagas", type=int, default=10, help="Vagas medidas na aba Vaga → Currículos.")
    parser.add_argument("--arquivo", help="Currículo real (PDF, DOCX ou TXT) para incluir a leitura do arquivo.")
    args = parser.parse_args()

    with SessionLocal() as sessao:
        vagas_banco = sessao.query(Job).order_by(Job.id).all()
        vagas = montar_payload_vagas(vagas_banco)
        curriculos_banco = curriculos_distintos(sessao)

        curriculos = [c["texto_bruto"] for c in json.load(open(CAMINHO_CURRICULOS, encoding="utf-8"))]
        curriculos = curriculos[-(args.quantidade + 1):]

        print(f"Currículo → Vagas: {args.quantidade} currículos comparados com {len(vagas)} vagas")
        _, _, primeira = analisar_curriculo(curriculos[0], vagas)
        medicoes = [analisar_curriculo(texto, vagas) for texto in curriculos[1:]]
        print(f"  primeira análise: {primeira:.2f} s")
        print(f"  seguintes (total): {resumo([m[2] for m in medicoes])}")
        print(f"    só TF-IDF: {resumo([m[0] for m in medicoes])} | só SBERT: {resumo([m[1] for m in medicoes])}")

        print(f"\nVaga → Currículos: {args.vagas} vagas comparadas com {len(curriculos_banco)} currículos")
        escolhidas = vagas_banco[:args.vagas + 1]
        primeira, _ = cronometrar(comparar_vaga_com_curriculos, escolhidas[0], curriculos_banco)
        tempos = [cronometrar(comparar_vaga_com_curriculos, vaga, curriculos_banco)[0] for vaga in escolhidas[1:]]
        print(f"  primeira análise: {primeira:.2f} s")
        print(f"  seguintes: {resumo(tempos)} "
              f"(≈ {statistics.mean(tempos) / len(curriculos_banco) * 1000:.0f} ms por currículo)")

    if args.arquivo:
        with open(args.arquivo, "rb") as arquivo:
            conteudo = arquivo.read()
        leitura, _ = cronometrar(leitor.ler, io.BytesIO(conteudo), os.path.basename(args.arquivo))
        print(f"\nLeitura do arquivo {os.path.basename(args.arquivo)}: {leitura:.3f} s")


if __name__ == "__main__":
    main()
