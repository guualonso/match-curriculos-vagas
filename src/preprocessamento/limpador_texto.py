import re
import unicodedata
from typing import List

import spacy

try:
    nlp = spacy.load("pt_core_news_sm")
    IDIOMA = "pt"
except OSError:
    try:
        nlp = spacy.load("en_core_web_sm")
        IDIOMA = "en"
    except OSError:
        raise RuntimeError(
            "Nenhum modelo spaCy encontrado. Execute:\n"
            "  python -m spacy download pt_core_news_sm\n"
            "  ou\n"
            "  python -m spacy download en_core_web_sm"
        )

STOPWORDS_DOMINIO = {
    "anos", "ano", "experiência", "experiencias", "empresa", "trabalho",
    "atividades", "desenvolvida", "desenvolvidas", "desenvolvido", "desenvolvidos",
    "responsável", "responsabilidades", "cargo", "função", "atuação",
    "conhecimento", "conhecimentos", "habilidade", "habilidades",
    "formação", "graduação", "cursando", "cursou", "bacharel", "tecnólogo",
    "profissional", "profissionais", "candidato", "candidatos",
    "vaga", "vagas",
    "years", "year", "experience", "company", "work", "activities",
    "responsible", "responsibilities", "position", "role", "knowledge",
    "skills", "skill", "degree", "bachelor", "candidate",
}


NORMALIZACOES = {
    r"\bnode\.js\b": "nodejs",
    r"\bvue\.js\b": "vuejs",
    r"\breact\.js\b": "reactjs",
    r"\bangular\.js\b": "angularjs",
    r"\bc\+\+": "cplusplus",
    r"\bc#\b": "csharp",
    r"\.net\b": "dotnet",
    r"\basp\.net\b": "aspnet",
    r"\bml\b": "machinelearning",
    r"\bai\b": "artificialintelligence",
    r"\bnlp\b": "naturallanguageprocessing",
    r"\bgcp\b": "googlecloudplatform",
}

class LimpadorTexto:

    def __init__(self, remover_stopwords: bool = True, lematizar: bool = True):
        self.remover_stopwords = remover_stopwords
        self.lematizar = lematizar

    def remover_acentos(self, texto: str) -> str:
        nfkd = unicodedata.normalize("NFKD", texto)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def remover_caracteres_especiais(self, texto: str) -> str:
        texto = re.sub(r"[^\w\s\-]", " ", texto)
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    def remover_urls(self, texto: str) -> str:
        return re.sub(r"https?://\S+|www\.\S+", " ", texto)

    def remover_emails(self, texto: str) -> str:
        return re.sub(r"\S+@\S+\.\S+", " ", texto)

    def remover_telefones(self, texto: str) -> str:
        return re.sub(r"(\+?\d[\d\s\-\(\)]{7,}\d)", " ", texto)

    def normalizar_termos_tecnicos(self, texto: str) -> str:
        texto = texto.lower()
        for padrao, substituto in NORMALIZACOES.items():
            texto = re.sub(padrao, substituto, texto)
        return texto

    def tokenizar_e_limpar(self, texto: str) -> List[str]:
        doc = nlp(texto)
        tokens = []
        for token in doc:
            if token.is_punct or token.is_space or len(token.text) < 2:
                continue
            if self.remover_stopwords and token.is_stop:
                continue
            lema = token.lemma_.lower()
            if self.remover_stopwords and lema in STOPWORDS_DOMINIO:
                continue
            palavra = lema if self.lematizar else token.text.lower()
            if palavra.isdigit():
                continue
            tokens.append(palavra)
        return tokens

    def limpar(self, texto: str) -> str:
        if not texto or not isinstance(texto, str):
            return ""

        texto = self.remover_urls(texto)
        texto = self.remover_emails(texto)
        texto = self.remover_telefones(texto)
        texto = self.normalizar_termos_tecnicos(texto)
        texto = self.remover_caracteres_especiais(texto)
        texto = self.remover_acentos(texto)
        tokens = self.tokenizar_e_limpar(texto)
        return " ".join(tokens)

    def limpar_lote(self, textos: List[str]) -> List[str]:
        return [self.limpar(t) for t in textos]


limpador = LimpadorTexto()


def limpar_texto(texto: str) -> str:
    return limpador.limpar(texto)
