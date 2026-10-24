"""
Extração de habilidades técnicas com base na taxonomia ESCO.

Base de referência:
  1. ESCO — coleção de habilidades digitais (1.284 conceitos), versão adaptada para
     PT-BR (data/esco/digitalSkillsCollection_ptbr.csv). Se o arquivo em inglês
     (data/esco/digitalSkillsCollection_en.csv) estiver presente, seus rótulos também
     são usados, já que os conjuntos de dados de currículos e vagas estão em inglês.
  2. Complemento — ferramentas que a ESCO não cobre (Docker, Kubernetes, React...),
     vindas da lista curada em complemento_skills.py. Termos da lista que a ESCO já
     cobre são descartados do complemento, para não contar a mesma habilidade duas vezes.

Cada habilidade detectada é devolvida pelo nome canônico: o rótulo preferencial
ESCO em PT-BR (sem o qualificador entre parênteses) ou o termo do complemento.
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from typing import Dict, List, Set

from src.extraction.complemento_skills import ALIASES, BASE_SKILLS

PASTA_ESCO = os.path.join(os.path.dirname(__file__), "..", "..", "data", "esco")
ARQUIVO_ESCO_PTBR = os.path.join(PASTA_ESCO, "digitalSkillsCollection_ptbr.csv")
ARQUIVO_ESCO_EN = os.path.join(PASTA_ESCO, "digitalSkillsCollection_en.csv")

# Rótulos que, em textos reais, coincidem com palavras comuns e geram falsos positivos
# (medido na amostra de vagas e currículos: "less" casava com 57% dos documentos).
# "ml" na ESCO é a linguagem ML, não machine learning. Do complemento, saem pelo mesmo
# motivo "go", "solid" ("solid experience") e "rest" ("the rest of").
ROTULOS_IGNORADOS: Set[str] = {
    "less", "source", "ml", "scratch", "chef", "salt", "unity",
    "eclipse", "ide", "pms", "go", "solid", "rest",
}

# Termos que só contam escritos em maiúsculas: "R" isolado (não "R&D") e "REST"/"RESTful"
# (a palavra "rest" em minúsculas fica ignorada).
PADROES_SO_MAIUSCULA = {
    "R": re.compile(r"(?<![\w+#.&])R(?![\w+#&])"),
    "rest": re.compile(r"\bREST(?:ful)?\b"),
}

CATEGORIA_POR_TIPO = {"knowledge": "conhecimento", "skill/competence": "habilidade"}


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def chave_rotulo(rotulo: str) -> str:
    """Forma usada na busca: sem qualificador entre parênteses, sem tags, sem acento, minúscula."""
    rotulo = re.sub(r"<[^>]+>", "", rotulo)
    rotulo = re.sub(r"\s*\(.*?\)", "", rotulo)
    return sem_acento(rotulo).strip().lower()


def nome_exibicao(rotulo: str) -> str:
    rotulo = re.sub(r"<[^>]+>", "", rotulo)
    return re.sub(r"\s*\(.*?\)", "", rotulo).strip()


def forma_canonica_complemento(texto: str) -> str:
    """Aplica os aliases da lista curada e junta o termo ("c++" -> "cplusplus", "sql server" -> "sqlserver")."""
    texto = texto.lower()
    texto = ALIASES.get(texto, texto)
    return re.sub(r"[\s.\-]", "", texto)


def ler_rotulos(caminho: str) -> List[dict]:
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


class ExtratorSkills:

    def __init__(self, arquivo_ptbr: str = ARQUIVO_ESCO_PTBR, arquivo_en: str = ARQUIVO_ESCO_EN):
        self.categoria: Dict[str, str] = {}      # nome canônico -> categoria
        self.rotulo_para_nome: Dict[str, str] = {}  # chave de busca -> nome canônico
        self.usa_rotulos_ingles = os.path.exists(arquivo_en)

        conceitos = {linha["conceptUri"]: linha for linha in ler_rotulos(arquivo_ptbr)}
        self.total_conceitos_esco = len(conceitos)

        rotulos_por_conceito: Dict[str, List[str]] = {uri: [] for uri in conceitos}
        fontes = [ler_rotulos(arquivo_ptbr)]
        if self.usa_rotulos_ingles:
            fontes.append(ler_rotulos(arquivo_en))
        for linhas in fontes:
            for linha in linhas:
                uri = linha["conceptUri"]
                if uri not in rotulos_por_conceito:
                    continue
                rotulos_por_conceito[uri].append(linha["preferredLabel"])
                # o CSV original separa os rótulos alternativos por quebra de linha; o adaptado, por " | "
                alternativos = re.split(r"\n|\s*\|\s*", linha.get("altLabels") or "")
                rotulos_por_conceito[uri].extend(r for r in alternativos if r.strip())

        for uri, linha in conceitos.items():
            nome = nome_exibicao(linha["preferredLabel"])
            self.categoria[nome] = CATEGORIA_POR_TIPO.get(linha["skillType"], "habilidade")
            for rotulo in rotulos_por_conceito[uri]:
                chave = chave_rotulo(rotulo)
                if len(chave) >= 2 and chave not in ROTULOS_IGNORADOS:
                    self.rotulo_para_nome.setdefault(chave, nome)

        # Complemento: termos da lista curada que nenhum rótulo ESCO cobre.
        # compara com e sem os aliases da lista ("angular" vira "angularjs" pelo alias, mas é o mesmo conceito)
        canonicas_esco = {}
        for chave, nome in self.rotulo_para_nome.items():
            canonicas_esco[forma_canonica_complemento(chave)] = nome
            canonicas_esco[re.sub(r"[\s.\-]", "", chave)] = nome
        canonicas_esco["r"] = "R"
        self.complemento: Dict[str, List[str]] = {}
        for categoria, termos in BASE_SKILLS.items():
            for termo in termos:
                if termo in ROTULOS_IGNORADOS or termo in canonicas_esco:
                    continue
                self.complemento.setdefault(categoria, []).append(termo)
                self.categoria[termo] = categoria
        self.categoria["rest"] = "metodologias"  # detectado só em maiúsculas (PADROES_SO_MAIUSCULA)
        self.total_complemento = sum(len(termos) for termos in self.complemento.values())

        alternativas = sorted(map(re.escape, self.rotulo_para_nome), key=len, reverse=True)
        self.padrao_esco = re.compile(r"(?<![\w+#.])(" + "|".join(alternativas) + r")(?![\w+#])")

    def _normalizar_complemento(self, texto: str) -> str:
        texto = texto.lower()
        for alias, canonica in ALIASES.items():
            texto = re.sub(r"\b" + re.escape(alias) + r"\b", canonica, texto)
        return texto

    def extrair(self, texto: str) -> Dict[str, List[str]]:
        """Habilidades agrupadas por categoria (usado pela interface)."""
        if not texto:
            return {}
        encontradas: Set[str] = {self.rotulo_para_nome[chave] for chave in self.padrao_esco.findall(sem_acento(texto.lower()))}
        encontradas.update(nome for nome, padrao in PADROES_SO_MAIUSCULA.items() if padrao.search(texto))

        normalizado = self._normalizar_complemento(texto)
        for termos in self.complemento.values():
            encontradas.update(t for t in termos if re.search(r"\b" + re.escape(t) + r"\b", normalizado))

        agrupadas: Dict[str, List[str]] = {}
        for nome in sorted(encontradas):
            agrupadas.setdefault(self.categoria.get(nome, "habilidade"), []).append(nome)
        return agrupadas

    def extrair_lista(self, texto: str) -> List[str]:
        """Lista plana de habilidades (usada no armazenamento e na comparação)."""
        return [nome for nomes in self.extrair(texto).values() for nome in nomes]

    def categoria_da_skill(self, skill: str) -> str | None:
        return self.categoria.get(skill)

    def comparar(self, texto_curriculo: str, texto_vaga: str) -> Dict[str, List[str]]:
        skills_curriculo = set(self.extrair_lista(texto_curriculo))
        skills_vaga = set(self.extrair_lista(texto_vaga))
        return {
            "em_comum": sorted(skills_curriculo & skills_vaga),
            "ausentes": sorted(skills_vaga - skills_curriculo),
            "extras": sorted(skills_curriculo - skills_vaga),
        }


extrator = ExtratorSkills()


def extrair_skills(texto: str) -> Dict[str, List[str]]:
    return extrator.extrair(texto)


def extrair_skills_lista(texto: str) -> List[str]:
    return extrator.extrair_lista(texto)


if __name__ == "__main__":
    print(f"Conceitos ESCO: {extrator.total_conceitos_esco} | rótulos de busca: {len(extrator.rotulo_para_nome)} "
          f"| rótulos em inglês: {'sim' if extrator.usa_rotulos_ingles else 'não'} | complemento: {extrator.total_complemento}")
    exemplo = "Python developer with SQL, Docker, Kubernetes and React. Less than 2 years building from scratch. R&D team."
    print(extrator.comparar(exemplo, "Vaga: Python, banco de dados PostgreSQL, Kubernetes, linguagem R."))
