# 🚀 GestaoVersus - Sistema de Gestão Empresarial

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

Sistema modular de gestão empresarial com foco em **Planejamento Estratégico Visual (PEV)** e **Gestão de Reuniões e Valores (GRV)**.

---

## 📋 Índice

- [Características](#características)
- [Quick Start](#quick-start)
- [Documentação](#documentação)
- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Deploy](#deploy)
- [Contribuindo](#contribuindo)

---

## ✨ Características

### Módulos Principais

- **PEV (Planejamento Estratégico Visual)**
  - Gestão de OKRs (Objectives & Key Results)
  - Indicadores e métricas
  - Roadmap de projetos
  - Mapa de processos

- **GRV (Gestão de Reuniões e Valores)**
  - Agendamento de reuniões
  - Gestão de participantes
  - Atas e acompanhamento
  - Relatórios profissionais em PDF

- **Meetings (Gestão de Reuniões)**
  - Calendário integrado
  - Convites e notificações
  - Agenda colaborativa
  - Histórico completo

### Funcionalidades

- ✅ **Multi-tenant** - Múltiplas empresas
- ✅ **Autenticação** - Login seguro com Flask-Login
- ✅ **Relatórios** - PDF profissionais com Playwright
- ✅ **API RESTful** - Endpoints documentados
- ✅ **Background Tasks** - Celery + Redis
- ✅ **Logs Automáticos** - Auditoria completa
- ✅ **Backup Automático** - Diário com retenção

---

## ⚡ Quick Start

### Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+

### Desenvolvimento (5 minutos)

```bash
# 1. Clone o repositório
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app31

# 2. Configure ambiente
cp env.development.example .env

# 3. Inicie os containers
docker-compose -f docker-compose.dev.yml up -d

# 4. Aguarde 30 segundos e acesse:
# - Aplicação: http://localhost:5003
# - Admin DB: http://localhost:8080
# - Email Test: http://localhost:8025
```

**Login padrão:**
- Email: `admin@gestaoversos.com`
- Senha: `admin123` ⚠️ **(TROCAR IMEDIATAMENTE!)**

### Produção

Ver [QUICK_START.md](QUICK_START.md) ou [README_DEPLOY.md](README_DEPLOY.md)

---

## 📚 Documentação

### Guias Essenciais

- **[QUICK_START.md](QUICK_START.md)** - Início rápido (10 min)
- **[README_DEPLOY.md](README_DEPLOY.md)** - Guia completo de deploy
- **[_GUIA_CONCEITOS_VIRTUALIZACAO.md](_GUIA_CONCEITOS_VIRTUALIZACAO.md)** - Conceitos de Docker/Deploy
- **[_VIRTUALIZACAO_COMPLETA.md](_VIRTUALIZACAO_COMPLETA.md)** - Resumo técnico completo

### Documentação Técnica

- **Governança:** `/docs/governance/`
  - `TECH_STACK.md` - Stack tecnológica
  - `ARCHITECTURE.md` - Arquitetura do sistema
  - `CODING_STANDARDS.md` - Padrões de código
  - `DATABASE_STANDARDS.md` - Padrões de banco
  - `API_STANDARDS.md` - Padrões de API
  - `FORBIDDEN_PATTERNS.md` - Anti-patterns

- **Templates:** `/docs/templates/`
  - `feature_template.md` - Nova feature
  - `bugfix_template.md` - Correção de bug
  - `module_template.md` - Novo módulo

---

## 🛠️ Tecnologias

### Backend
- **Python** 3.9+
- **Flask** 2.3.3
- **SQLAlchemy** 2.0.21
- **PostgreSQL** 15 / SQLite (dev)
- **Redis** 7 (cache & queues)
- **Celery** 5.3.1 (background tasks)

### Frontend
- **Jinja2** Templates
- **JavaScript** Vanilla
- **CSS3** Custom

### DevOps
- **Docker** & **Docker Compose**
- **Nginx** (reverse proxy + SSL)
- **Gunicorn** (WSGI server)
- **GitHub Actions** (CI/CD)
- **Let's Encrypt** (SSL grátis)

### Cloud
- **Google Cloud Run** / **App Engine**
- **AWS S3** (backups)
- **Google Cloud Storage** (backups)

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────┐
│          INTERNET (Usuários)                │
└──────────────────┬──────────────────────────┘
                   │ HTTPS (443)
                   ↓
┌─────────────────────────────────────────────┐
│  NGINX                                      │
│  - SSL/TLS                                  │
│  - Rate Limiting                            │
│  - Static Files                             │
└──────────────────┬──────────────────────────┘
                   │ HTTP (5002)
                   ↓
┌─────────────────────────────────────────────┐
│  GUNICORN (4 workers)                       │
│  - Flask App                                │
│  - Blueprints (PEV, GRV, Meetings)          │
└──────────┬────────┬────────┬────────────────┘
           │        │        │
     ┌─────┘        │        └─────┐
     ↓              ↓              ↓
┌─────────┐  ┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Redis   │  │ Celery   │
│    15    │  │    7     │  │ Worker   │
└─────────┘  └──────────┘  └──────────┘
```

### Estrutura do Projeto

```
app31/
├── 📱 Frontend
│   ├── templates/          # Jinja2 templates
│   └── static/             # CSS, JS, images
│
├── 🔧 Backend
│   ├── models/             # SQLAlchemy models
│   ├── services/           # Lógica de negócio
│   ├── modules/            # Blueprints (PEV, GRV, Meetings)
│   ├── middleware/         # Auto-log, decorators
│   └── api/                # REST API
│
├── 🐳 Docker
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
├── 🌐 Nginx
│   └── nginx/
│       ├── nginx.conf
│       └── conf.d/
│
├── 🤖 CI/CD
│   └── .github/workflows/
│
├── 💾 Scripts
│   ├── backup/
│   ├── deploy/
│   └── init_app.py
│
└── 📚 Docs
    ├── governance/
    └── templates/
```

---

## 🚀 Deploy

### Opções de Hospedagem

#### 1. Google Cloud (Recomendado)

```bash
# Setup automático
./scripts/deploy/setup_gcp.sh
```

#### 2. Servidor VPS (DigitalOcean, AWS, etc)

```bash
# Deploy em servidor
docker-compose up -d
```

#### 3. Local (Desenvolvimento)

```bash
# Ambiente dev com hot-reload
docker-compose -f docker-compose.dev.yml up -d
```

Ver guia completo: [README_DEPLOY.md](README_DEPLOY.md)

---

## 🔐 Segurança

- ✅ SSL/TLS obrigatório em produção
- ✅ Rate limiting contra DDoS
- ✅ Security headers (HSTS, CSP, etc)
- ✅ Senhas com bcrypt
- ✅ SQL injection protection (ORM)
- ✅ CSRF protection
- ✅ Input validation
- ✅ Logs de auditoria

---

## 💾 Backup

### Automático
- **Frequência:** Diário às 3:00 AM
- **Retenção:** 30 dias
- **Storage:** Local + S3/GCS
- **Compressão:** gzip

### Manual

```bash
# Backup
python scripts/backup/backup_database.py

# Restore
python scripts/backup/restore_database.py
```

---

## 🧪 Testes

```bash
# Rodar testes
pytest

# Com coverage
pytest --cov=. --cov-report=html

# Específico
pytest tests/test_pev.py
```

---

## 📊 Monitoring

### Health Checks

- `/health` - Status geral
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe

### Logs

```bash
# Ver logs em tempo real
docker-compose logs -f app

# Logs específicos
docker-compose logs app | grep ERROR
```

---

## 🤝 Contribuindo

### Workflow

1. Fork o projeto
2. Crie branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -am 'Adiciona nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra Pull Request

### Padrões

- **Código:** Seguir [CODING_STANDARDS.md](docs/governance/CODING_STANDARDS.md)
- **Commits:** Mensagens claras em português
- **Testes:** Adicionar testes para novas features
- **Docs:** Atualizar documentação

---

## 📞 Suporte

- **Issues:** https://github.com/mff2000/GestaoVersus/issues
- **Email:** suporte@congigr.com
- **Docs:** `/docs/`

---

## 📄 License

Proprietary - Todos os direitos reservados © 2025 GestaoVersus

---

## 🎯 Roadmap

### Q4 2025
- [ ] Dashboard analytics avançado
- [ ] Integração com Google Calendar
- [ ] App mobile (React Native)
- [ ] API pública documentada

### Q1 2026
- [ ] WhatsApp bot integration
- [ ] IA para sugestões de OKRs
- [ ] Multi-idioma (EN, ES)
- [ ] Marketplace de templates

---

## 🙏 Agradecimentos

- Equipe de desenvolvimento
- Comunidade Flask
- Comunidade Python
- Usuários beta testers

---

**🎉 Desenvolvido com ❤️ pela equipe GestaoVersus**

**Versão:** 1.0  
**Última atualização:** 20/10/2025  
**Status:** ✅ Produção
