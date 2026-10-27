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


def test_pronome_it_ignorado_e_sigla_it_detectada():
    assert "tecnologia informática" not in extrator.extrair_lista("I built it from the ground up")
    assert "tecnologia informática" in extrator.extrair_lista("Analista de IT com foco em suporte")


def test_alternativo_amplo_nao_rouba_termo_especifico():
    habilidades = extrator.extrair_lista("Deep learning with TensorFlow and Keras")
    assert "tensorflow" in habilidades and "keras" in habilidades
    assert "visão por computador" not in habilidades


def test_bi_so_em_maiusculas():
    assert "inteligência empresarial" in extrator.extrair_lista("Dashboards de BI no Power BI")
    assert "inteligência empresarial" not in extrator.extrair_lista("bi-weekly meetings")


class ModeloFalso:
    """Substitui o SBERT nos testes: o embedding de uma janela é [nº de palavras, 1], normalizado."""
    def __init__(self):
        self.janelas_recebidas = []

    def encode(self, textos, **_):
        import numpy as np
        self.janelas_recebidas.extend(textos)
        emb = np.array([[len(t.split()), 1.0] for t in textos])
        return emb / np.linalg.norm(emb, axis=1, keepdims=True)


def test_janelas_cobrem_o_texto_inteiro_com_sobreposicao():
    from src.matching.semantic_matcher import dividir_em_janelas
    palavras = [f"p{i}" for i in range(400)]
    janelas = dividir_em_janelas(" ".join(palavras))
    assert all(len(j.split()) <= 150 for j in janelas)
    assert janelas[-1].split()[-1] == "p399"          # nada é descartado
    assert janelas[1].split()[0] == "p120"            # 30 palavras de sobreposição
    assert dividir_em_janelas("texto curto") == ["texto curto"]


def test_embedding_do_texto_e_media_das_janelas():
    import numpy as np
    from src.matching.semantic_matcher import MatcherSemantico
    matcher = MatcherSemantico(modelo="falso", usar_janelas=True)
    matcher._modelo = ModeloFalso()
    emb = matcher._embeddings(["curto", " ".join(["x"] * 400)])
    assert len(matcher._modelo.janelas_recebidas) == 1 + 4   # 1 janela + 4 (inícios 0, 120, 240, 360)
    assert emb.shape == (2, 2)
    assert np.allclose(np.linalg.norm(emb, axis=1), 1.0)


def test_padrao_sem_janelas_le_so_o_inicio():
    from src.matching.semantic_matcher import MatcherSemantico
    matcher = MatcherSemantico(modelo="falso")
    matcher._modelo = ModeloFalso()
    matcher._embeddings(["curto", " ".join(["x"] * 400)])
    assert len(matcher._modelo.janelas_recebidas) == 2   # um texto por entrada, sem divisão


def test_cache_de_embeddings_codifica_cada_texto_uma_vez():
    from src.matching.semantic_matcher import MatcherSemantico
    matcher = MatcherSemantico(modelo="falso")
    matcher._modelo = ModeloFalso()
    matcher._embeddings(["vaga a", "vaga b"])
    emb = matcher._embeddings(["vaga a", "currículo novo", "vaga a"])
    assert matcher._modelo.janelas_recebidas == ["vaga a", "vaga b", "currículo novo"]
    assert emb.shape[0] == 3


def test_skills_precalculadas_dao_o_mesmo_resultado():
    matcher = MatcherCurriculoVaga()
    cv = "Python developer with Docker and PostgreSQL"
    vaga = "Vaga Python, Docker, Kubernetes"
    sem = matcher.match_many(cv, [{"id": "1", "title": "v", "description": vaga}])[0]
    com = matcher.match_many(cv, [{"id": "1", "title": "v", "description": vaga,
                                   "skills": extrator.extrair_lista(vaga)}])[0]
    assert sem.score_final == com.score_final and sem.skills_comum == com.skills_comum
