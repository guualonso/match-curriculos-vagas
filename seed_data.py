import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, create_tables, Job, Resume
from src.preprocessamento.limpador_texto import clean_text
from src.extraction.skills_extractor import extractor as skills_extractor

# ---------------------------------------------------------------------------
# Vagas simuladas (baseadas em vagas reais de LinkedIn/Indeed para TI no Brasil)
# ---------------------------------------------------------------------------

VAGAS = [
    {
        "title": "Desenvolvedor Python Backend Pleno",
        "company": "FinTech Brasil",
        "source": "linkedin",
        "description": """
Buscamos desenvolvedor Python Pleno para integrar nosso time de backend.

Responsabilidades:
- Desenvolvimento e manutenção de APIs REST com FastAPI e Django
- Modelagem e otimização de queries em PostgreSQL
- Integração com serviços AWS (Lambda, S3, SQS)
- Containerização com Docker e orquestração com Kubernetes
- Implementação de testes unitários e de integração com pytest

Requisitos obrigatórios:
- Python (3+ anos)
- FastAPI ou Django
- PostgreSQL e Redis
- Docker
- Git

Diferenciais:
- AWS (certificação desejável)
- Kafka ou RabbitMQ
- GraphQL
- Scrum / Kanban
        """,
    },
    {
        "title": "Desenvolvedor Full Stack Java + React",
        "company": "Banco Digital XYZ",
        "source": "indeed",
        "description": """
Vaga para desenvolvedor Full Stack com foco em Java no backend e React no frontend.

Responsabilidades:
- Desenvolvimento de microserviços com Java e Spring Boot
- Criação de interfaces modernas com React e TypeScript
- Integração com bancos relacionais (PostgreSQL, Oracle) e NoSQL (MongoDB)
- Deploy em nuvem Azure
- Participação em cerimônias ágeis (Scrum)

Requisitos:
- Java (Spring Boot)
- React e TypeScript
- SQL (PostgreSQL ou Oracle)
- Docker
- REST API
- Git

Diferenciais:
- Azure certificado
- Kafka
- Kubernetes
- TDD / BDD
        """,
    },
    {
        "title": "Data Engineer",
        "company": "Varejo Analytics",
        "source": "glassdoor",
        "description": """
Engenheiro de Dados para construção e manutenção de pipelines de dados em larga escala.

Responsabilidades:
- Desenvolvimento de pipelines ETL/ELT com Python e Apache Spark
- Orquestração de workflows com Apache Airflow
- Modelagem de dados para Data Warehouse
- Ingestão de dados em tempo real com Kafka
- Criação de dashboards com Power BI e Tableau

Requisitos:
- Python
- SQL avançado
- Apache Spark
- Airflow
- AWS (S3, Glue, Redshift) ou GCP
- Docker

Diferenciais:
- dbt
- Kafka
- Databricks
- Pandas / NumPy
        """,
    },
    {
        "title": "Engenheiro DevOps / SRE",
        "company": "SaaS Corp",
        "source": "linkedin",
        "description": """
Engenheiro DevOps para automação de infraestrutura e garantia de confiabilidade dos sistemas.

Responsabilidades:
- Gerenciamento de clusters Kubernetes em AWS EKS
- Automação de infraestrutura com Terraform e Ansible
- Configuração e manutenção de pipelines CI/CD (GitHub Actions, Jenkins)
- Monitoramento com Prometheus e Grafana
- Administração de servidores Linux

Requisitos:
- Kubernetes e Docker
- Terraform
- AWS
- Linux / Bash / Shell
- GitHub Actions ou Jenkins
- Git

Diferenciais:
- Ansible
- Grafana e Prometheus
- Python para automação
- Certificação AWS
        """,
    },
    {
        "title": "Cientista de Dados / ML Engineer",
        "company": "HealthTech",
        "source": "linkedin",
        "description": """
Cientista de dados para desenvolvimento de modelos preditivos na área de saúde.

Responsabilidades:
- Análise exploratória e limpeza de dados com Pandas e NumPy
- Desenvolvimento de modelos de machine learning com scikit-learn e PyTorch
- Processamento de linguagem natural (NLP) com spaCy e HuggingFace
- Deploy de modelos via API (FastAPI)
- Visualização de resultados com Matplotlib, Seaborn e Plotly

Requisitos:
- Python
- Pandas, NumPy, scikit-learn
- Machine learning
- SQL
- Git

Diferenciais:
- Deep learning (PyTorch ou TensorFlow)
- NLP / HuggingFace
- AWS SageMaker ou GCP Vertex
- MLflow
        """,
    },
    {
        "title": "Desenvolvedor Mobile Android/iOS",
        "company": "Startup EdTech",
        "source": "manual",
        "description": """
Desenvolvedor mobile para criação de aplicativos educacionais.

Responsabilidades:
- Desenvolvimento de apps Android com Kotlin
- Desenvolvimento de apps iOS com Swift
- Implementação de soluções cross-platform com Flutter
- Integração com APIs REST
- Publicação nas lojas Google Play e App Store

Requisitos:
- Kotlin (Android) ou Swift (iOS)
- Flutter ou React Native
- REST API
- Git

Diferenciais:
- Firebase
- Testes com Jest ou JUnit
- CI/CD mobile
        """,
    },
    {
        "title": "Desenvolvedor Frontend React Sênior",
        "company": "AgTech Brasil",
        "source": "linkedin",
        "description": """
Desenvolvedor Frontend sênior para modernização de plataforma agrícola.

Responsabilidades:
- Desenvolvimento de interfaces com React e TypeScript
- Componentização com design system próprio
- Integração com APIs GraphQL e REST
- Testes com Jest e Cypress
- Performance e acessibilidade web

Requisitos:
- React (3+ anos)
- TypeScript
- HTML e CSS avançado
- Jest
- Git

Diferenciais:
- GraphQL
- NextJS
- Tailwind CSS
- Cypress
- Docker
        """,
    },
    {
        "title": "Arquiteto de Software",
        "company": "Consultoria Tech",
        "source": "manual",
        "description": """
Arquiteto de Software para definição de padrões e orientação técnica de times.

Responsabilidades:
- Definição de arquitetura de microserviços e APIs
- Avaliação e seleção de tecnologias
- Revisão de código e mentoria de desenvolvedores
- Documentação de decisões arquiteturais (ADR)
- Integração entre sistemas legados e novas soluções

Requisitos:
- Experiência com microservices e REST API
- Docker e Kubernetes
- PostgreSQL e MongoDB
- AWS ou Azure
- Scrum / DDD / SOLID

Diferenciais:
- GraphQL
- Kafka
- Terraform
- Spring Boot ou FastAPI
        """,
    },
]

# ---------------------------------------------------------------------------
# Currículos simulados
# ---------------------------------------------------------------------------

CURRICULOS = [
    {
        "filename": "curriculo_ana_python.txt",
        "raw_text": """
Ana Paula Ferreira | ana.ferreira@email.com | São Paulo, SP

FORMAÇÃO
Bacharel em Ciência da Computação — USP (2021)

EXPERIÊNCIA PROFISSIONAL

Desenvolvedora Backend — FinTech ABC (2022–2024)
- Desenvolvimento de APIs REST com Python e FastAPI
- Banco de dados PostgreSQL e Redis
- Docker e Kubernetes
- CI/CD com GitHub Actions
- AWS (EC2, S3, Lambda, SQS)
- Scrum

Estagiária de Desenvolvimento — Startup XYZ (2021–2022)
- Python e Django
- PostgreSQL
- Git

HABILIDADES TÉCNICAS
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git,
GitHub Actions, Pytest, Scrum, REST API, Linux
        """,
    },
    {
        "filename": "curriculo_carlos_fullstack.txt",
        "raw_text": """
Carlos Eduardo Souza | carlos@email.com | Rio de Janeiro, RJ

FORMAÇÃO
Tecnólogo em Análise e Desenvolvimento de Sistemas — FIAP (2020)

EXPERIÊNCIA

Desenvolvedor Full Stack Pleno — Banco Digital (2021–2024)
- Java com Spring Boot — microserviços
- React e TypeScript no frontend
- PostgreSQL e MongoDB
- Docker e Azure
- Testes com JUnit e Jest
- Metodologia Scrum/Kanban

Desenvolvedor Junior — Agência Digital (2019–2021)
- JavaScript, HTML, CSS
- ReactJS
- MySQL

COMPETÊNCIAS
Java, Spring Boot, React, TypeScript, JavaScript, HTML, CSS, PostgreSQL,
MongoDB, Docker, Azure, JUnit, Jest, Git, Scrum, REST API, Microservices
        """,
    },
    {
        "filename": "curriculo_beatriz_dados.txt",
        "raw_text": """
Beatriz Yamamoto | beatriz.yamamoto@email.com | Campinas, SP

FORMAÇÃO
Mestrado em Ciência de Dados — UNICAMP (2022)
Bacharel em Estatística — UNICAMP (2020)

EXPERIÊNCIA

Engenheira de Dados — Varejo Online (2022–2024)
- Pipelines ETL com Python e Apache Spark
- Airflow para orquestração
- AWS (S3, Glue, Redshift, EMR)
- SQL avançado — PostgreSQL e Redshift
- Kafka para streaming
- Power BI e Tableau para dashboards
- dbt para transformações

Data Analyst — Consultoria (2020–2022)
- Python (Pandas, NumPy, Matplotlib)
- SQL
- Excel avançado

HABILIDADES
Python, Pandas, NumPy, Spark, Airflow, Kafka, AWS, SQL, PostgreSQL,
Power BI, Tableau, dbt, Docker, Git
        """,
    },
]


def seed():
    print("🌱 Iniciando seed do banco de dados...\n")
    create_tables()
    db = SessionLocal()

    try:
        # Verifica se já há dados
        existing_jobs = db.query(Job).count()
        existing_resumes = db.query(Resume).count()

        if existing_jobs > 0:
            print(f"⚠️  Banco já possui {existing_jobs} vagas. Pulando vagas.")
        else:
            print("📋 Inserindo vagas simuladas...")
            for v in VAGAS:
                cleaned = clean_text(v["description"])
                skills = skills_extractor.extract(v["description"])
                job = Job(
                    title=v["title"],
                    company=v["company"],
                    description=v["description"],
                    cleaned_text=cleaned,
                    extracted_skills=skills,
                    source=v["source"],
                )
                db.add(job)
            db.commit()
            print(f"   ✅ {len(VAGAS)} vagas inseridas.")

        if existing_resumes > 0:
            print(f"⚠️  Banco já possui {existing_resumes} currículos. Pulando currículos.")
        else:
            print("\n👤 Inserindo currículos simulados...")
            for c in CURRICULOS:
                cleaned = clean_text(c["raw_text"])
                skills = skills_extractor.extract(c["raw_text"])
                resume = Resume(
                    filename=c["filename"],
                    raw_text=c["raw_text"],
                    cleaned_text=cleaned,
                    extracted_skills=skills,
                )
                db.add(resume)
            db.commit()
            print(f"   ✅ {len(CURRICULOS)} currículos inseridos.")

        print("\n🎉 Seed concluído! Acesse http://localhost:8000/docs para testar.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro durante o seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
