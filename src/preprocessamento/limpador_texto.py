import re
import unicodedata
from typing import List

import spacy

from spacy.lang.en.stop_words import STOP_WORDS as STOPWORDS_INGLES
from spacy.lang.pt.stop_words import STOP_WORDS as STOPWORDS_PORTUGUES

# Carrega os dois modelos; cada texto é processado pelo modelo do seu idioma.
MODELOS_SPACY = {}
for idioma, nome_modelo in (("pt", "pt_core_news_sm"), ("en", "en_core_web_sm")):
    try:
        MODELOS_SPACY[idioma] = spacy.load(nome_modelo)
    except OSError:
        pass

if not MODELOS_SPACY:
    raise RuntimeError(
        "Nenhum modelo spaCy encontrado. Execute:\n"
        "  python -m spacy download pt_core_news_sm\n"
        "  python -m spacy download en_core_web_sm"
    )


def detectar_idioma(texto: str) -> str:
    """'en' ou 'pt', pela contagem de stopwords de cada idioma nas primeiras 300 palavras."""
    palavras = re.findall(r"[a-zà-ú]+", texto.lower())[:300]
    pontos_ingles = sum(palavra in STOPWORDS_INGLES for palavra in palavras)
    pontos_portugues = sum(palavra in STOPWORDS_PORTUGUES for palavra in palavras)
    return "en" if pontos_ingles > pontos_portugues else "pt"


def modelo_para(texto: str):
    # Se o modelo do idioma detectado não estiver instalado, usa o que houver.
    return MODELOS_SPACY.get(detectar_idioma(texto)) or next(iter(MODELOS_SPACY.values()))

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
# Mesma lista sem acentos: o texto já chega sem acentos na checagem de stopwords.
STOPWORDS_DOMINIO = STOPWORDS_DOMINIO | {
    "".join(c for c in unicodedata.normalize("NFKD", palavra) if not unicodedata.combining(c))
    for palavra in STOPWORDS_DOMINIO
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

    def tokenizar_e_limpar(self, texto: str, modelo=None) -> List[str]:
        doc = (modelo or modelo_para(texto))(texto)
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

        # Detecta o idioma no texto original, antes de remover acentos.
        modelo = modelo_para(texto)

        texto = self.remover_urls(texto)
        texto = self.remover_emails(texto)
        texto = self.remover_telefones(texto)
        texto = self.normalizar_termos_tecnicos(texto)
        texto = self.remover_caracteres_especiais(texto)
        texto = self.remover_acentos(texto)
        tokens = self.tokenizar_e_limpar(texto, modelo)
        return " ".join(tokens)

    def limpar_lote(self, textos: List[str]) -> List[str]:
        return [self.limpar(t) for t in textos]


limpador = LimpadorTexto()


def limpar_texto(texto: str) -> str:
    return limpador.limpar(texto)
