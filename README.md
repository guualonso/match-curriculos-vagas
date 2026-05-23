# Resume Job Matcher

> **TCC — TAC1 | IFSP**
> Extração de Habilidades Técnicas em Currículos e Análise de Compatibilidade com Vagas de Emprego utilizando Processamento de Linguagem Natural
>
> **Autores:** Gustavo Moreira Alonso · Pedro Fukuya Ohno
> **Orientadora:** Giovana Yuko Nakashima

---

## Sobre o projeto

Sistema que automatiza a triagem de currículos para vagas de tecnologia da informação. Dado um currículo (PDF ou DOCX) e um conjunto de descrições de vagas, a aplicação:

1. **Extrai o texto** do currículo via PyMuPDF (PDF) ou python-docx (DOCX)
2. **Pré-processa** o texto — remove ruídos, normaliza termos técnicos, aplica tokenização e lematização com spaCy
3. **Identifica skills técnicas** com base em lista de referência (linguagens, frameworks, cloud, dados, IA/ML etc.)
4. **Vetoriza** currículo e vagas com TF-IDF (scikit-learn)
5. **Calcula compatibilidade** via similaridade do cosseno + score de skills
6. **Retorna ranking** de vagas ordenado por compatibilidade, com skills em comum e ausentes

---

## Estrutura do repositório

```
resume-job-matcher/
├── data/
│   ├── raw/               # currículos e vagas brutos
│   └── processado/        # dados pré-processados
│
├── src/
│   ├── preprocessamento/
│   │   └── text_cleaner.py       # limpeza e normalização de texto
│   ├── extraction/
│   │   └── skills_extractor.py   # extração de habilidades técnicas
│   ├── matching/
│   │   └── matcher.py            # TF-IDF + similaridade do cosseno
│   └── utils/
│       └── file_reader.py        # leitura de PDF e DOCX
│
├── app/
│   ├── main.py            # FastAPI — entrypoint
│   ├── routes.py          # endpoints da API
│   ├── database.py        # SQLAlchemy — modelos e sessão
│   └── schemas.py         # Pydantic — schemas de entrada/saída
│
├── notebooks/
│   └── experimentos.ipynb # testes exploratórios
│
├── tests/
│   └── test_matcher.py    # testes unitários (pytest)
│
├── requirements.txt
├── .env.example
└── README.md
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

# 4. Baixe o modelo spaCy (português)
python -m spacy download pt_core_news_sm

# Se preferir inglês:
# python -m spacy download en_core_web_sm

# 5. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com a URL do seu banco PostgreSQL
```

---

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
| `POST` | `/api/v1/match/resume/{id}` | Matchear currículo com todas as vagas |
| `POST` | `/api/v1/match/upload-and-match` | Upload + match em uma chamada |
| `POST` | `/api/v1/match/quick` | Match rápido (texto direto, sem BD) |
| `GET` | `/api/v1/history/resume/{id}` | Histórico de matches |
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
  -F "top_n=5"

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
| FastAPI | API REST |
| spaCy | NLP — tokenização e lematização |
| scikit-learn | TF-IDF + similaridade do cosseno |
| PyMuPDF (fitz) | Extração de texto de PDFs |
| python-docx | Leitura de arquivos DOCX |
| SQLAlchemy | ORM |
| PostgreSQL | Banco de dados |
| Pydantic | Validação de dados |

---

## Metodologia

O score de compatibilidade final é calculado como uma combinação ponderada:

```
score_final = 0.6 × score_tfidf_cosseno + 0.4 × score_skills
```

Onde:
- **score_tfidf_cosseno**: similaridade do cosseno entre os vetores TF-IDF do currículo e da vaga
- **score_skills**: proporção de skills da vaga presentes no currículo (`|skills_comuns| / |skills_vaga|`)

---

## Dataset

Para validação, será utilizado o [Resume Dataset](https://www.kaggle.com/datasets/saugataroyarghya/resume-dataset) disponível no Kaggle, complementado com dados simulados em português.
