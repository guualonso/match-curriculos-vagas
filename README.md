# Resume Job Matcher

> **TCC — Bacharelado em Ciência da Computação | IFSP Campus Salto**
> Extração de Habilidades Técnicas em Currículos e Análise de Compatibilidade com Vagas de TI: Comparativo entre TF-IDF e Sentence-BERT
>
> **Autores:** Gustavo Moreira Alonso · Pedro Fukuya Ohno
> **Orientadora:** Giovana Yuko Nakashima

---

## Sobre o projeto

Sistema que automatiza a triagem de currículos para vagas de tecnologia da informação. Dado um currículo (PDF, DOCX ou TXT) e um conjunto de descrições de vagas, a aplicação:

1. **Extrai o texto** do currículo via PyMuPDF (PDF) ou python-docx (DOCX)
2. **Pré-processa** o texto — remove ruídos, normaliza termos técnicos, detecta o idioma e aplica tokenização, lematização e remoção de stopwords com spaCy
3. **Identifica habilidades técnicas** com base na taxonomia ESCO (1.284 habilidades digitais, adaptada para PT-BR) e em um complemento de ferramentas
4. **Calcula a compatibilidade** por dois métodos:
   - **TF-IDF**: similaridade do cosseno entre vetores TF-IDF combinada ao score de habilidades
   - **Sentence-BERT**: similaridade do cosseno entre embeddings de um modelo multilíngue ajustado (fine-tuning) para o domínio de TI
5. **Unifica os dois métodos**: mostra o top N de vagas compatíveis (nível Médio ou Alto em pelo menos um método), indicando quais métodos as apontaram, e lista as demais com sua posição. Na direção inversa, a partir de uma vaga, lista os currículos compatíveis

---

## Estrutura do repositório

```
match-curriculos-vagas/
├── data/
│   ├── esco/              # habilidades digitais da ESCO (PT-BR adaptada e EN)
│   ├── raw/               # datasets brutos do Kaggle
│   └── processado/        # dados processados, pares de treino, gabarito e resultados
│
├── src/
│   ├── preprocessamento/
│   │   └── limpador_texto.py     # LimpadorTexto: limpeza, idioma, lematização
│   ├── extraction/
│   │   ├── skills_extractor.py   # ExtratorSkills: extração baseada na ESCO
│   │   └── complemento_skills.py # ferramentas que a ESCO não cobre
│   ├── matching/
│   │   ├── matcher.py            # MatcherCurriculoVaga (TF-IDF) e ResultadoMatch
│   │   └── semantic_matcher.py   # MatcherSemantico (Sentence-BERT)
│   └── utils/
│       └── leitor_arquivo.py     # LeitorArquivo: PDF, DOCX e TXT
│
├── app/
│   ├── main.py            # FastAPI — entrypoint
│   ├── routers/           # endpoints da API, um arquivo por domínio
│   ├── services/
│   │   └── matching_service.py  # upload, persistência e escolha do método
│   ├── database.py        # SQLAlchemy — modelos e sessão
│   ├── schemas.py         # Pydantic — schemas de entrada/saída
│   ├── templates/         # interface web
│   └── static/            # CSS e módulos JavaScript (ES6)
│
├── models/sbert_finetuned/    # modelo ajustado (gerado pelo finetune_sbert.py, fora do git)
├── importar_dataset.py        # currículos do Resume Dataset
├── preparar_vagas.py          # vagas dos datasets do LinkedIn
├── preparar_pares.py          # split por currículo e pares de treino
├── finetune_sbert.py          # ajuste fino do SBERT
├── amostra_anotacao.py        # amostra estratificada do gabarito
├── avaliar_comparativo.py     # métricas no gabarito (170 pares)
├── avaliar_validacao_sbert.py # métricas do SBERT no conjunto de validação
├── medir_tempo.py             # tempo de processamento por currículo (RNF01)
├── popular_vagas.py           # cadastra vagas do dataset no banco
├── popular_curriculos.py      # cadastra currículos do dataset no banco (aba Vaga → Currículos)
├── tests/test_matcher.py      # testes unitários (pytest)
└── requirements.txt
```

---

## Pré-requisitos

- Python 3.10+
- PostgreSQL rodando localmente (ou via Docker)

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/guualonso/match-curriculos-vagas.git
cd match-curriculos-vagas

# 2. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Baixe os modelos spaCy (o pré-processamento escolhe o modelo pelo idioma do texto)
python -m spacy download pt_core_news_sm
python -m spacy download en_core_web_sm

# 5. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com a URL do seu banco PostgreSQL
```

---

## Base de habilidades (ESCO)

A extração usa a coleção de habilidades digitais da ESCO v1.2.1 (1.284 conceitos),
adaptada para o português brasileiro, mais um complemento de ferramentas que a ESCO
não cobre (`src/extraction/complemento_skills.py`).

- `data/esco/digitalSkillsCollection_ptbr.csv` — versão adaptada (obrigatória, já no repositório)
- `data/esco/digitalSkillsCollection_en.csv` — rótulos em inglês (recomendada, porque os
  datasets estão em inglês). Baixe em https://esco.ec.europa.eu/en/use-esco/download.

Para conferir: `python -m src.extraction.skills_extractor`

## Reproduzindo o pipeline

```bash
python importar_dataset.py --limite 3000   # currículos -> curriculos_processados.json
python preparar_vagas.py                   # vagas -> vagas_processadas.json
python preparar_pares.py                   # split por currículo (seed 42) + pares positivos
python finetune_sbert.py --epocas 3 --batch 64 --seq 256 --fp16
python avaliar_comparativo.py              # gabarito: AUC-ROC, acurácia, precisão, revocação e F1 (limiar 0,40)
python avaliar_comparativo.py --sbert-base --saida data/processado/resultados_base.csv  # SBERT sem ajuste
python avaliar_validacao_sbert.py          # SBERT no conjunto de validação (antes x depois do ajuste)
python medir_tempo.py                      # tempo por currículo (RNF01)
python popular_vagas.py --quantidade 300   # cadastra 300 vagas do dataset no banco (interface)
python popular_curriculos.py --quantidade 100  # cadastra 100 currículos de teste no banco (interface)
```

`amostra_anotacao.py` gera a amostra de 170 pares do gabarito. Não rode de novo depois
de anotada: ela sortearia pares diferentes.

## Banco de dados

```bash
# Crie o banco no PostgreSQL
psql -U postgres -c "CREATE DATABASE resume_matcher;"

# As tabelas são criadas automaticamente no primeiro start da aplicação
```

> **Dica:** Para usar **SQLite** em desenvolvimento (sem PostgreSQL), altere o `.env`:
> ```
> DATABASE_URL=sqlite:///./resume_matcher.db
> ```
> E instale o driver: não precisa — SQLite já vem com Python.
> Mas mude `psycopg2-binary` por `aiosqlite` no `requirements.txt`.

---

## Executando a API

```bash
uvicorn app.main:app --reload
```

Acesse a documentação interativa em: **http://localhost:8000/docs**

---

## Endpoints principais

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/v1/jobs` | Cadastrar vaga |
| `GET` | `/api/v1/jobs` | Listar vagas |
| `POST` | `/api/v1/resumes/upload` | Upload de currículo |
| `GET` | `/api/v1/resumes` | Listar currículos (aba Currículos) |
| `DELETE` | `/api/v1/resumes/{id}` | Remover currículo e o seu histórico |
| `POST` | `/api/v1/match/resume/{id}` | Matchear currículo com todas as vagas |
| `GET` | `/api/v1/jobs/opcoes` | Todas as vagas (id, título e empresa) |
| `POST` | `/api/v1/match/upload-and-match` | Upload + match pelos dois métodos (currículo → vagas) |
| `GET` | `/api/v1/match/job/{id}/resumes` | Currículos compatíveis com uma vaga (vaga → currículos) |
| `POST` | `/api/v1/match/quick` | Match rápido pelos dois métodos (texto direto, sem BD) |
| `GET` | `/api/v1/history/resume/{id}` | Histórico de um currículo (um item por par, com os dois métodos) |
| `GET` | `/api/v1/history/recent` | Últimos pares analisados |
| `GET` | `/health` | Status da aplicação |

---

## Exemplo de uso (curl)

```bash
# 1. Cadastrar uma vaga
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Desenvolvedor Python Sênior",
    "company": "Tech Corp",
    "description": "Buscamos dev com experiência em Python, FastAPI, PostgreSQL, Docker e AWS.",
    "source": "linkedin"
  }'

# 2. Upload de currículo e matching automático
curl -X POST http://localhost:8000/api/v1/match/upload-and-match \
  -F "file=@curriculo.pdf" \
  -F "limite_vagas=0"

# 3. Match rápido (sem arquivo)
curl -X POST http://localhost:8000/api/v1/match/quick \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Desenvolvedor Python com FastAPI, Docker e AWS.",
    "job_description": "Vaga para Python dev com FastAPI e cloud AWS.",
    "job_title": "Dev Python"
  }'
```

---

## Executando os testes

```bash
pytest tests/ -v
```

---

## Tecnologias utilizadas

| Tecnologia | Uso |
|------------|-----|
| Python 3.10+ | Linguagem principal |
| FastAPI + uvicorn | API REST |
| spaCy | PLN — tokenização e lematização (PT e EN) |
| scikit-learn | TF-IDF, similaridade do cosseno e métricas |
| sentence-transformers + PyTorch | Sentence-BERT e ajuste fino |
| PyMuPDF (fitz) | Extração de texto de PDFs |
| python-docx | Leitura de arquivos DOCX |
| SQLAlchemy | ORM |
| SQLite / PostgreSQL | Banco de dados (selecionado por `DATABASE_URL`) |
| Pydantic | Validação de dados |

---

## Metodologia

**TF-IDF** — o score final combina a similaridade lexical e as habilidades em comum:

```
score_final = 0.25 × cosseno_tfidf + 0.75 × score_skills
```

- **cosseno_tfidf**: similaridade do cosseno entre os vetores TF-IDF do currículo e da vaga (TF-IDF ajustado só ao par)
- **score_skills**: proporção das habilidades da vaga presentes no currículo
- Com menos de duas habilidades detectadas (currículo + vaga), o resultado traz um aviso.
- `testar_cobertura.py` mostra que o antigo fator de confiança (cobertura técnica) não alterava os resultados.

**Sentence-BERT** — o score é a similaridade do cosseno entre os embeddings do currículo e da vaga,
gerados pelo modelo `paraphrase-multilingual-MiniLM-L12-v2` ajustado com 10.501 pares positivos
(MultipleNegativesRankingLoss, 3 épocas, lotes de 64, 256 tokens, fp16).

**Níveis**: Alto (≥ 0,70), Médio (0,40 a 0,70) e Baixo (< 0,40).

**Avaliação**: gabarito de 170 pares anotados manualmente (40 compatíveis e 130 não compatíveis),
com AUC-ROC e acurácia, precisão, revocação e F1-score no limiar de 0,40.

---

## Dataset

- Currículos: [Resume Dataset](https://www.kaggle.com/datasets/saugataroyarghya/resume-dataset) (3.000 primeiros registros)
- Vagas: [LinkedIn Software Engineering Jobs](https://www.kaggle.com/datasets/asaniczka/software-engineer-job-postings-linkedin) e [Data Science Job Postings and Skills](https://www.kaggle.com/datasets/asaniczka/data-science-job-postings-and-skills) (20.133 vagas)
- Habilidades: [ESCO v1.2.1](https://esco.ec.europa.eu), coleção de habilidades digitais
