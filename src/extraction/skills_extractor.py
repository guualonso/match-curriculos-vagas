"""
Módulo de extração de habilidades técnicas.
Identifica skills de TI em currículos e descrições de vagas
usando uma lista de referência organizada por categoria.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

# ---------------------------------------------------------------------------
# Base de habilidades técnicas por categoria
# ---------------------------------------------------------------------------

BASE_SKILLS: Dict[str, List[str]] = {
    "linguagens": [
        "python", "java", "javascript", "typescript", "kotlin", "swift",
        "cplusplus", "csharp", "go", "rust", "ruby", "php", "scala",
        "r", "matlab", "perl", "lua", "dart", "groovy", "cobol",
    ],
    "frontend": [
        "html", "css", "reactjs", "vuejs", "angularjs", "angular",
        "svelte", "jquery", "bootstrap", "tailwind", "sass", "less",
        "webpack", "vite", "nextjs", "nuxt",
    ],
    "backend": [
        "nodejs", "django", "flask", "fastapi", "spring", "springboot",
        "laravel", "rails", "express", "aspnet", "dotnet", "quarkus",
        "micronaut", "nestjs",
    ],
    "banco_de_dados": [
        "sql", "mysql", "postgresql", "sqlite", "oracle", "sqlserver",
        "mongodb", "redis", "cassandra", "dynamodb", "elasticsearch",
        "neo4j", "firebase", "supabase",
    ],
    "cloud": [
        "aws", "azure", "googlecloudplatform", "heroku", "digitalocean",
        "vercel", "netlify", "oraclecloud", "ibmcloud",
    ],
    "devops": [
        "docker", "kubernetes", "jenkins", "githubactions", "gitlab",
        "terraform", "ansible", "prometheus", "grafana", "nginx",
        "apache", "linux", "bash", "shell", "git",
    ],
    "dados": [
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
        "tableau", "powerbi", "spark", "hadoop", "airflow", "dbt",
        "kafka", "rabbitmq",
    ],
    "ia_ml": [
        "machinelearning", "deeplearning", "artificialintelligence",
        "naturallanguageprocessing", "tensorflow", "pytorch", "keras",
        "scikitlearn", "opencv", "huggingface", "langchain",
    ],
    "metodologias": [
        "scrum", "kanban", "agile", "devops", "tdd", "bdd", "ddd",
        "solid", "rest", "graphql", "soap", "microservices", "api",
    ],
    "mobile": [
        "android", "ios", "reactnative", "flutter", "xamarin", "ionic",
    ],
    "testes": [
        "junit", "pytest", "jest", "selenium", "cypress", "postman",
        "swagger", "sonarqube",
    ],
}

# Conjunto plano para lookup rápido
TODAS_SKILLS: Set[str] = {skill for skills in BASE_SKILLS.values() for skill in skills}

# Aliases e variações comuns → forma canônica
ALIASES: Dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "c++": "cplusplus",
    "c#": "csharp",
    ".net": "dotnet",
    "golang": "go",
    "react": "reactjs",
    "vue": "vuejs",
    "angular": "angularjs",
    "next": "nextjs",
    "next.js": "nextjs",
    "node": "nodejs",
    "node.js": "nodejs",
    "fast api": "fastapi",
    "asp.net": "aspnet",
    "spring boot": "springboot",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "elastic": "elasticsearch",
    "sql server": "sqlserver",
    "gcp": "googlecloudplatform",
    "google cloud": "googlecloudplatform",
    "amazon web services": "aws",
    "ml": "machinelearning",
    "dl": "deeplearning",
    "ai": "artificialintelligence",
    "nlp": "naturallanguageprocessing",
    "scikit learn": "scikitlearn",
    "scikit-learn": "scikitlearn",
    "hugging face": "huggingface",
    "k8s": "kubernetes",
    "github actions": "githubactions",
    "power bi": "powerbi",
    "power-bi": "powerbi",
    "apache spark": "spark",
}


class ExtratorSkills:
    """
    Extrai habilidades técnicas de um texto.
    Retorna as skills encontradas agrupadas por categoria.
    """

    def __init__(self):
        self.base = BASE_SKILLS
        self.todas = TODAS_SKILLS
        self.aliases = ALIASES

    def _normalizar(self, texto: str) -> str:
        """Normalização mínima para matching de skills."""
        texto = texto.lower().strip()
        for alias, canonica in self.aliases.items():
            texto = re.sub(r"\b" + re.escape(alias) + r"\b", canonica, texto)
        return texto

    def extrair(self, texto: str) -> Dict[str, List[str]]:
        """
        Extrai habilidades do texto e retorna agrupadas por categoria.

        Args:
            texto: Texto do currículo ou descrição da vaga.

        Returns:
            Dicionário com categorias como chaves e listas de skills.
        """
        normalizado = self._normalizar(texto)
        encontradas: Dict[str, List[str]] = {}

        for categoria, skills in self.base.items():
            correspondencias = []
            for skill in skills:
                padrao = r"\b" + re.escape(skill) + r"\b"
                if re.search(padrao, normalizado):
                    correspondencias.append(skill)
            if correspondencias:
                encontradas[categoria] = correspondencias

        return encontradas

    def extrair_lista(self, texto: str) -> List[str]:
        """Retorna lista plana de todas as skills encontradas no texto."""
        categorizadas = self.extrair(texto)
        return [skill for skills in categorizadas.values() for skill in skills]

    def categoria_da_skill(self, skill: str) -> str | None:
        """Retorna a categoria de uma skill específica."""
        skill = skill.lower()
        for categoria, skills in self.base.items():
            if skill in skills:
                return categoria
        return None

    def comparar(self, texto_curriculo: str, texto_vaga: str) -> Dict[str, List[str]]:
        """
        Compara as skills de um currículo com os requisitos de uma vaga.

        Returns:
            Dicionário com:
                - em_comum : skills presentes em ambos
                - ausentes  : skills da vaga que o currículo não tem
                - extras    : skills do currículo além dos requisitos da vaga
        """
        skills_curriculo = set(self.extrair_lista(texto_curriculo))
        skills_vaga = set(self.extrair_lista(texto_vaga))

        return {
            "em_comum": sorted(skills_curriculo & skills_vaga),
            "ausentes":  sorted(skills_vaga - skills_curriculo),
            "extras":    sorted(skills_curriculo - skills_vaga),
        }


# Instância padrão
extrator = ExtratorSkills()


def extrair_skills(texto: str) -> Dict[str, List[str]]:
    """Função de conveniência: extrai skills categorizadas."""
    return extrator.extrair(texto)


def extrair_skills_lista(texto: str) -> List[str]:
    """Função de conveniência: retorna lista plana de skills."""
    return extrator.extrair_lista(texto)
