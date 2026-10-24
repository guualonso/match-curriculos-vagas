"""Testes dos módulos principais: pré-processamento, extração de habilidades (ESCO) e matcher TF-IDF."""

from src.preprocessamento.limpador_texto import LimpadorTexto, detectar_idioma
from src.extraction.skills_extractor import extrator
from src.matching.matcher import MatcherCurriculoVaga


class TestLimpadorTexto:
    def setup_method(self):
        self.limpador = LimpadorTexto()

    def test_remove_urls_e_emails(self):
        texto = self.limpador.limpar("Veja https://linkedin.com/in/fulano ou fulano@email.com")
        assert "https" not in texto and "@" not in texto

    def test_normaliza_termos_tecnicos(self):
        assert "nodejs" in self.limpador.normalizar_termos_tecnicos("Experiência com node.js")

    def test_texto_vazio_ou_nulo(self):
        assert self.limpador.limpar("") == ""
        assert self.limpador.limpar(None) == ""

    def test_detecta_idioma(self):
        assert detectar_idioma("Software engineer with experience in the design of APIs") == "en"
        assert detectar_idioma("Desenvolvedor com experiência no desenvolvimento de APIs") == "pt"

    def test_remove_stopwords_do_ingles(self):
        tokens = self.limpador.limpar("Engineer with experience in the design of services").split()
        assert "the" not in tokens and "with" not in tokens

    def test_remove_stopwords_de_dominio_acentuadas(self):
        assert "experiencia" not in self.limpador.limpar("Desenvolvedor com experiência em Python").split()


class TestExtratorSkills:
    def test_base_esco_carregada(self):
        assert extrator.total_conceitos_esco == 1284

    def test_detecta_conceito_esco_pelo_rotulo(self):
        assert "Python" in extrator.extrair_lista("Experience with Python and SQL")

    def test_detecta_complemento(self):
        assert "docker" in extrator.extrair_lista("Deploy com Docker e Kubernetes")

    def test_nao_duplica_termo_coberto_pela_esco(self):
        habilidades = extrator.extrair_lista("Python developer")
        assert habilidades.count("Python") == 1 and "python" not in habilidades

    def test_ignora_rotulos_ambiguos(self):
        habilidades = extrator.extrair_lista("Less than two years, built from scratch at the R&D team")
        assert habilidades == []

    def test_r_maiusculo_isolado(self):
        assert "R" in extrator.extrair_lista("Análise estatística em R e Python")

    def test_comparar(self):
        comparacao = extrator.comparar("Python, SQL, Docker", "Python, SQL, Kubernetes")
        assert set(comparacao["em_comum"]) == {"Python", "SQL"}
        assert comparacao["ausentes"] == ["kubernetes"]
        assert comparacao["extras"] == ["docker"]


class TestMatcherTfidf:
    def setup_method(self):
        self.matcher = MatcherCurriculoVaga()

    def test_score_entre_0_e_1(self):
        resultado = self.matcher.match_one("Desenvolvedor Python com Docker", "Vaga Python com Docker")
        assert 0.0 <= resultado.score_final <= 1.0

    def test_textos_relacionados_pontuam_mais(self):
        curriculo = "Python, FastAPI, PostgreSQL, Docker"
        relacionado = self.matcher.match_one(curriculo, "Python, FastAPI, Docker")
        sem_relacao = self.matcher.match_one(curriculo, "Contador com Excel e Word")
        assert relacionado.score_final > sem_relacao.score_final

    def test_match_many_ordenado_e_limitado(self):
        vagas = [
            {"id": "1", "title": "Python", "description": "Python, FastAPI, Docker"},
            {"id": "2", "title": "Java", "description": "Java, Spring Boot, MySQL"},
            {"id": "3", "title": "Front", "description": "React, TypeScript, CSS"},
        ]
        resultados = self.matcher.match_many("Python, FastAPI, Docker", vagas, top_n=2)
        scores = [r.score_final for r in resultados]
        assert len(resultados) == 2 and scores == sorted(scores, reverse=True)

    def test_nivel_de_compatibilidade(self):
        resultado = self.matcher.match_one("Python Docker AWS", "Python Docker AWS")
        assert resultado.nivel_compatibilidade() in ("Alto", "Médio", "Baixo")


def test_rest_so_em_maiusculas():
    assert "rest" in extrator.extrair_lista("APIs REST e serviços RESTful")
    assert "rest" not in extrator.extrair_lista("the rest of the team")
