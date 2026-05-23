"""
Testes unitários para os módulos principais.
Execute com: pytest tests/ -v
"""

import pytest

from src.preprocessamento.text_cleaner import TextCleaner
from src.extraction.skills_extractor import SkillsExtractor
from src.matching.matcher import ResumeJobMatcher


# ---------------------------------------------------------------------------
# TextCleaner
# ---------------------------------------------------------------------------

class TestTextCleaner:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_remove_urls(self):
        text = "Visite https://linkedin.com/in/fulano para mais detalhes."
        result = self.cleaner.remove_urls(text)
        assert "https" not in result
        assert "linkedin" not in result

    def test_remove_email(self):
        text = "Contato: fulano@email.com"
        result = self.cleaner.remove_emails(text)
        assert "@" not in result

    def test_normalize_tech_terms(self):
        text = "Experiência com node.js e vue.js"
        result = self.cleaner.normalize_tech_terms(text)
        assert "nodejs" in result
        assert "vuejs" in result

    def test_clean_returns_string(self):
        result = self.cleaner.clean("Desenvolvedor Python com 3 anos de experiência.")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_clean_empty_string(self):
        assert self.cleaner.clean("") == ""

    def test_clean_none(self):
        assert self.cleaner.clean(None) == ""


# ---------------------------------------------------------------------------
# SkillsExtractor
# ---------------------------------------------------------------------------

class TestSkillsExtractor:
    def setup_method(self):
        self.extractor = SkillsExtractor()

    def test_extract_python(self):
        text = "Experiência com Python e SQL."
        result = self.extractor.extract_flat(text)
        assert "python" in result

    def test_extract_sql(self):
        text = "Conhecimento em SQL e PostgreSQL."
        result = self.extractor.extract_flat(text)
        assert "sql" in result
        assert "postgresql" in result

    def test_extract_multiple_categories(self):
        text = "Python, Docker, AWS, React, PostgreSQL"
        result = self.extractor.extract(text)
        categories = list(result.keys())
        assert len(categories) >= 3

    def test_alias_nodejs(self):
        text = "Trabalhou com node.js e express"
        result = self.extractor.extract_flat(text)
        assert "nodejs" in result

    def test_compare_matching(self):
        resume = "Python, SQL, Docker, AWS"
        job = "Python, SQL, Kubernetes"
        comparison = self.extractor.compare(resume, job)
        assert "python" in comparison["matching"]
        assert "sql" in comparison["matching"]
        assert "kubernetes" in comparison["missing"]
        assert "docker" in comparison["extra"]

    def test_get_skill_category(self):
        assert self.extractor.get_skill_category("python") == "linguagens"
        assert self.extractor.get_skill_category("docker") == "devops"
        assert self.extractor.get_skill_category("xyz_desconhecido") is None


# ---------------------------------------------------------------------------
# ResumeJobMatcher
# ---------------------------------------------------------------------------

class TestResumeJobMatcher:
    def setup_method(self):
        self.matcher = ResumeJobMatcher()

    def test_match_one_returns_score_between_0_and_1(self):
        resume = "Desenvolvedor Python com experiência em FastAPI, PostgreSQL e Docker."
        job = "Vaga para desenvolvedor Python com FastAPI e bancos relacionais."
        result = self.matcher.match_one(resume, job)
        assert 0.0 <= result.similarity_score <= 1.0

    def test_high_similarity_for_identical_texts(self):
        text = "Python, FastAPI, PostgreSQL, Docker, AWS, scikit-learn"
        result = self.matcher.match_one(text, text)
        assert result.similarity_score > 0.5

    def test_low_similarity_for_unrelated_texts(self):
        resume = "Contador com experiência em Excel e Word."
        job = "Desenvolvedor Python com machine learning e AWS."
        result = self.matcher.match_one(resume, job)
        assert result.similarity_score < 0.5

    def test_match_many_returns_sorted_results(self):
        resume = "Python, FastAPI, PostgreSQL, Docker"
        jobs = [
            {"id": "1", "title": "Vaga Python", "description": "Python, FastAPI, Docker"},
            {"id": "2", "title": "Vaga Java", "description": "Java, Spring Boot, MySQL"},
            {"id": "3", "title": "Vaga Frontend", "description": "React, TypeScript, CSS"},
        ]
        results = self.matcher.match_many(resume, jobs)
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_match_many_top_n(self):
        resume = "Python, FastAPI, PostgreSQL"
        jobs = [
            {"id": str(i), "title": f"Vaga {i}", "description": f"Python job {i}"}
            for i in range(5)
        ]
        results = self.matcher.match_many(resume, jobs, top_n=3)
        assert len(results) <= 3

    def test_match_result_has_skills(self):
        resume = "Python, Docker, AWS, PostgreSQL"
        job = "Python, Kubernetes, AWS"
        result = self.matcher.match_one(resume, job)
        assert "python" in result.matching_skills
        assert "aws" in result.matching_skills
        assert "kubernetes" in result.missing_skills

    def test_compatibility_level_labels(self):
        resume = "Python FastAPI Docker AWS PostgreSQL scikit-learn tensorflow kubernetes"
        job = "Python FastAPI Docker AWS PostgreSQL scikit-learn tensorflow kubernetes"
        result = self.matcher.match_one(resume, job)
        assert result._get_compatibility_level() in ("Alto", "Médio", "Baixo")
