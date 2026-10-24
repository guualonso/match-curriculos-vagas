"""
Lista curada de ferramentas e tecnologias usada como COMPLEMENTO da ESCO.

Só entram na extração os termos que a ESCO não cobre (Docker, Kubernetes, React...).
Os que a ESCO já cobre (Python, SQL, Java...) são associados ao conceito ESCO
correspondente, para não contar a mesma habilidade duas vezes.
"""

from typing import Dict, List, Set

BASE_SKILLS: Dict[str, List[str]] = {

    "linguagens": [
        "python", "java", "javascript", "typescript", "kotlin", "swift",
        "cplusplus", "csharp", "go", "rust", "ruby", "php", "scala",
        "r", "matlab", "perl", "lua", "dart", "groovy", "cobol",
        "assembly", "vba", "powershell", "bash", "shell",
    ],

    "frontend": [
        "html", "css", "reactjs", "vuejs", "angularjs", "angular",
        "svelte", "jquery", "bootstrap", "tailwind", "sass", "less",
        "webpack", "vite", "nextjs", "nuxt", "storybook",
    ],

    "backend": [
        "nodejs", "django", "flask", "fastapi", "spring", "springboot",
        "laravel", "rails", "express", "aspnet", "dotnet", "quarkus",
        "micronaut", "nestjs", "strapi",
    ],

    "banco_de_dados": [
        "sql", "mysql", "postgresql", "sqlite", "oracle", "sqlserver",
        "mongodb", "redis", "cassandra", "dynamodb", "elasticsearch",
        "neo4j", "firebase", "supabase", "mariadb", "db2",
    ],

    "cloud": [
        "aws", "azure", "googlecloudplatform", "heroku", "digitalocean",
        "vercel", "netlify", "oraclecloud", "ibmcloud", "cloudflare",
    ],

    "devops": [
        "docker", "kubernetes", "jenkins", "githubactions", "gitlab",
        "terraform", "ansible", "prometheus", "grafana", "nginx",
        "apache", "linux", "git", "circleci", "argocd", "helm",
        "pulumi", "vagrant",
    ],

    "infraestrutura": [
        "vmware", "pfsense", "zabbix", "wireshark", "cisco",
        "windowsserver", "activedirectory", "hypervv", "proxmox",
        "virtualbox", "oraclevm", "samba", "putty", "nagios",
        "openvpn", "mikrotik", "fortinet", "checkpoint",
        "dhcp", "dns", "ftp", "ssh", "tcp", "vpn",
        "firewall", "vlan", "routing", "switching",
    ],

    "sistemas_operacionais": [
        "ubuntu", "debian", "centos", "redhat", "fedora", "kali",
        "windows", "macos", "freebsd", "android", "ios",
    ],

    "seguranca": [
        "cybersecurity", "pentest", "soc", "siem", "ids", "ips",
        "owasp", "criptografia", "ssl", "tls", "oauth", "jwt",
        "lgpd", "gdpr", "iso27001", "nist",
    ],

    "dados": [
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
        "tableau", "powerbi", "spark", "hadoop", "airflow", "dbt",
        "kafka", "rabbitmq", "looker", "metabase", "qlik",
    ],

    "ia_ml": [
        "machinelearning", "deeplearning", "artificialintelligence",
        "naturallanguageprocessing", "tensorflow", "pytorch", "keras",
        "scikitlearn", "opencv", "huggingface", "langchain",
        "xgboost", "lightgbm", "mlflow", "airflow",
    ],

    "metodologias": [
        "scrum", "kanban", "agile", "tdd", "bdd", "ddd",
        "solid", "rest", "graphql", "soap", "microservices", "api",
        "devops", "gitflow", "cleancode", "cleanarchitecture",
    ],

    "mobile": [
        "reactnative", "flutter", "xamarin", "ionic", "swiftui",
        "jetpackcompose",
    ],

    "testes": [
        "junit", "pytest", "jest", "selenium", "cypress", "postman",
        "swagger", "sonarqube", "testng", "mockito", "locust",
        "gatling", "k6",
    ],

    "ferramentas": [
        "git", "github", "gitlab", "bitbucket", "jira", "confluence",
        "trello", "notion", "slack", "figma", "vscode",
    ],

    "erp": [
        "sap", "salesforce", "servicenow", "totvs", "dynamics",
        "sharepoint", "powerautomate", "powerbi",
    ],
}

TODAS_SKILLS: Set[str] = {
    skill for skills in BASE_SKILLS.values() for skill in skills
}

ALIASES: Dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "c++": "cplusplus",
    "c#": "csharp",
    ".net": "dotnet",
    "golang": "go",
    "vb": "vba",
    "ps1": "powershell",

    "react": "reactjs",
    "vue": "vuejs",
    "angular": "angularjs",
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
    "maria db": "mariadb",

    "gcp": "googlecloudplatform",
    "google cloud": "googlecloudplatform",
    "amazon web services": "aws",
    "microsoft azure": "azure",

    "active directory": "activedirectory",
    "ad ds": "activedirectory",
    "windows server": "windowsserver",
    "hyper-v": "hypervv",
    "hyper v": "hypervv",
    "oracle vm": "oraclevm",
    "virtual box": "virtualbox",
    "pf sense": "pfsense",
    "open vpn": "openvpn",

    "cyber security": "cybersecurity",
    "penetration test": "pentest",
    "penetration testing": "pentest",

    "red hat": "redhat",
    "kali linux": "kali",
    "mac os": "macos",

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

    "clean code": "cleancode",
    "clean architecture": "cleanarchitecture",
    "git flow": "gitflow",

    "react native": "reactnative",
    "jetpack compose": "jetpackcompose",
    "swift ui": "swiftui",

    "power automate": "powerautomate",
    "ms dynamics": "dynamics",
}
