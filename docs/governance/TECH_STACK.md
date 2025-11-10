# 🛠️ Stack Tecnológica Oficial

**Última Atualização:** 28/10/2025  
**Versão:** 1.0  
**Status:** ✅ Ativo

---

## 🎯 Filosofia

> "Escolhemos tecnologias estáveis, bem documentadas e com comunidade ativa. Evitamos adicionar dependências sem justificativa clara."

---

## 📚 Stack Aprovada

### Backend Core

| Tecnologia | Versão | Justificativa | Status |
|------------|--------|---------------|--------|
| **Python** | 3.9+ | Linguagem principal, ótimo para IA e dados | ✅ Obrigatório |
| **Flask** | 2.3.3 | Framework web leve e flexível | ✅ Obrigatório |
| **SQLAlchemy** | 2.0.21 | ORM maduro com suporte PostgreSQL/SQLite | ✅ Obrigatório |
| **Flask-Login** | 0.6.3 | Autenticação padrão Flask | ✅ Obrigatório |
| **Flask-Migrate** | 4.0.5 | Gerenciamento de migrations | ✅ Obrigatório |

### Banco de Dados

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **PostgreSQL** | 12+ | Banco principal (produção) | ✅ Obrigatório |
| **SQLite** | 3.x | Desenvolvimento e backup | ✅ Obrigatório |

**⚠️ IMPORTANTE:** Sempre escrever queries compatíveis com ambos os bancos.

### Segurança

| Tecnologia | Versão | Justificativa | Status |
|------------|--------|---------------|--------|
| **bcrypt** | 4.0.1 | Hash de senhas | ✅ Obrigatório |
| **Werkzeug** | 2.3.7 | Segurança e utilitários Flask | ✅ Obrigatório |
| **Flask-WTF** | 1.1.1 | Proteção CSRF | ✅ Obrigatório |

### Frontend

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **Jinja2** | - | Template engine (vem com Flask) | ✅ Obrigatório |
| **JavaScript Vanilla** | ES6+ | Interatividade client-side | ✅ Obrigatório |
| **CSS Custom** | - | Estilização | ✅ Obrigatório |

**❌ NÃO USAR:** React, Vue, Angular (mantém simplicidade)

### APIs & Serialização

| Tecnologia | Versão | Justificativa | Status |
|------------|--------|---------------|--------|
| **Flask-RESTful** | 0.3.10 | APIs REST estruturadas | ✅ Recomendado |
| **marshmallow** | 3.20.1 | Serialização e validação | ✅ Recomendado |

### Relatórios & PDFs

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **ReportLab** | 4.0.4 | Geração de PDFs complexos | ✅ Obrigatório |
| **Playwright** | 1.55.0 | PDF via HTML (casos específicos) | ⚠️ Usar com cautela |

**Regra:** Preferir ReportLab. Playwright apenas para layouts HTML complexos.

### Background Jobs & Scheduling

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **APScheduler** | 3.10.4 | Tarefas agendadas (cron-like) | ✅ Obrigatório |
| **Windows Task Scheduler** | n/a | Backups do PostgreSQL e `git push` diário | ✅ Obrigatório |
| **Celery** | 5.3.1 | Tarefas assíncronas (opcional) | ⚠️ Não configurado |
| **Redis** | 4.6.0 | Cache e message broker | ✅ Aprovado |

**Nota:** APScheduler cobre rotinas internas da aplicação. Tarefas operacionais (backup e publicação Git) rodam via Windows Task Scheduler. Celery permanece instalado para uso futuro se necessário.

### Integrações

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **boto3** | 1.34.131 | AWS S3 (backups) | ✅ Aprovado |
| **requests** | 2.31.0 | HTTP client | ✅ Obrigatório |

### Desenvolvimento & Qualidade

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **pytest** | 7.4.2 | Framework de testes | ✅ Obrigatório |
| **pytest-flask** | 1.2.0 | Testes Flask | ✅ Obrigatório |
| **black** | 23.7.0 | Formatação de código | ✅ Obrigatório |
| **flake8** | 6.0.0 | Linting | ✅ Obrigatório |

### Virtualização & Deploy

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **Docker** | 20.10+ | Containerização | ✅ Obrigatório |
| **Docker Compose** | 2.0+ | Orquestração local | ✅ Obrigatório |
| **PostgreSQL (Windows Host)** | 18 | Banco principal compartilhado pelo host | ✅ Obrigatório |
| **PostgreSQL (Docker)** | 18-alpine | Uso emergencial / restauração pontual | ⚠️ Suporte legado |
| **Redis (Docker)** | 7-alpine | Cache em container | ✅ Aprovado |
| **Adminer (Docker)** | latest | Gerenciador de banco web | ✅ Dev only |
| **MailHog (Docker)** | latest | Teste de e-mails | ✅ Dev only |

**Ambiente de Desenvolvimento:**
- `docker-compose.yml` orquestra app, Celery, Redis e Nginx conectando ao PostgreSQL do host (`host.docker.internal`)
- Backups automáticos gerados em `backups/` via `scripts/backup/run_pg_backup.ps1` (12h/18h/22h)
- Publicação diária no GitHub às 18h com `scripts/deploy/auto_git_push.ps1` (requer credenciais configuradas)

### Checklist de Alterações Relacionadas a Infraestrutura

- [ ] Avaliar se a mudança impacta Dockerfiles, `docker-compose.yml`, variáveis de ambiente ou serviços auxiliares executados em containers.
- [ ] Atualizar os arquivos de Docker e exemplos de configuração (`.env.example`, scripts) sempre que houver novas dependências, portas ou integrações.
- [ ] Executar `docker compose up --build` (ou comando equivalente) para validar o stack containerizado antes de concluir a tarefa.
- [ ] Documentar no PR/commit como a validação em Docker foi realizada; ausência desta evidência bloqueia a revisão.

---

## 🚫 Tecnologias Proibidas

### ❌ Não Adicionar Sem Aprovação

| Tecnologia | Motivo | Alternativa Aprovada |
|------------|--------|---------------------|
| **Django** | Já temos Flask | Flask |
| **FastAPI** | Consistência com Flask | Flask-RESTful |
| **MongoDB** | Já temos PostgreSQL | PostgreSQL + JSONB |
| **MySQL** | Consistência PostgreSQL | PostgreSQL |
| **jQuery** | Legacy, usar vanilla JS | JavaScript ES6+ |
| **Bootstrap** | Preferimos CSS custom | CSS custom |
| **TypeScript** | Overhead desnecessário | JavaScript ES6+ |
| **GraphQL** | Complexidade adicional | REST + Flask-RESTful |
| **ORMs alternativos** | Já temos SQLAlchemy | SQLAlchemy |

---

## 📦 Estrutura de Dependências

### requirements.txt - Estrutura Obrigatória

```txt
# Core Flask
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
# ... (agrupado por categoria)

# Database
SQLAlchemy==2.0.21
psycopg2-binary==2.9.7

# NUNCA usar versões "latest" ou sem pin
# SEMPRE especificar versões exatas
```

**Regras:**
- ✅ Sempre versões pinadas (==)
- ✅ Comentários separando categorias
- ✅ Alfabético dentro de cada categoria
- ❌ Nunca usar >= ou ~ (apenas em dev)

---

## 🔄 Processo de Adição de Nova Tecnologia

### Checklist Obrigatório

```markdown
## Proposta de Nova Dependência

- [ ] **Nome:** [nome da biblioteca]
- [ ] **Versão:** [versão específica]
- [ ] **Motivo:** [por que precisamos?]
- [ ] **Alternativas avaliadas:** [o que mais foi considerado?]
- [ ] **Compatibilidade:** Funciona com PostgreSQL E SQLite?
- [ ] **Licença:** Compatível com uso comercial?
- [ ] **Manutenção:** Última atualização < 6 meses?
- [ ] **Documentação:** Tem docs em português ou inglês?
- [ ] **Tamanho:** < 50MB de dependências extras?
- [ ] **Testes:** Tem testes e CI ativo?
```

### Aprovação Necessária

- **Dependência < 10MB:** Aprovação informal (chat)
- **Dependência > 10MB:** Documentar em DECISION_LOG.md
- **Mudança de framework:** Reunião + aprovação formal

---

## 🎯 Padrões de Versão

### Quando Atualizar

| Tipo de Atualização | Quando | Risco | Testes |
|---------------------|--------|-------|--------|
| **Patch** (X.Y.Z) | Imediatamente | Baixo | Básicos |
| **Minor** (X.Y) | Mensalmente | Médio | Completos |
| **Major** (X) | Planejado | Alto | Regressão total |

### Exemplo:
- `2.3.3 → 2.3.4` = Patch (OK fazer)
- `2.3.3 → 2.4.0` = Minor (testar bem)
- `2.3.3 → 3.0.0` = Major (planejar sprint)

---

## 🔍 Compatibilidade PostgreSQL/SQLite

### ✅ Padrões Compatíveis

```python
# ✅ BOM - Funciona em ambos
from sqlalchemy import Column, Integer, String, Text

class Model(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
```

### ❌ Padrões Incompatíveis

```python
# ❌ RUIM - PostgreSQL específico
from sqlalchemy.dialects.postgresql import JSONB

class Model(db.Model):
    data = Column(JSONB)  # SQLite não tem JSONB

# ✅ CORRETO - Usar JSON genérico
from sqlalchemy import JSON
class Model(db.Model):
    data = Column(JSON)  # Funciona em ambos
```

---

## 📊 Monitoramento de Dependências

### Ferramentas Aprovadas

```bash
# Verificar vulnerabilidades
pip-audit

# Verificar atualizações
pip list --outdated

# Verificar tamanho
pip show [package]
```

### Frequência

- **Semanal:** Verificar vulnerabilidades críticas
- **Mensal:** Revisar dependências desatualizadas
- **Trimestral:** Limpar dependências não utilizadas

---

## 🎓 Onde Aprender Mais

| Tecnologia | Documentação Oficial |
|------------|---------------------|
| Flask | https://flask.palletsprojects.com/ |
| SQLAlchemy | https://docs.sqlalchemy.org/ |
| PostgreSQL | https://www.postgresql.org/docs/ |
| ReportLab | https://docs.reportlab.com/ |

---

## 📝 Histórico de Mudanças

| Data | Mudança | Motivo |
|------|---------|--------|
| 18/10/2025 | Criação inicial | Documentar stack atual |
| 20/10/2025 | Adicionado APScheduler 3.10.4 | Tarefas agendadas automáticas para rotinas |
| 20/10/2025 | Adicionada seção Virtualização & Deploy | Documentar ambiente Docker |
| 20/10/2025 | PostgreSQL atualizado para v18-alpine | Compatibilidade com versão local |
| 28/10/2025 | Orquestração usando PostgreSQL do host + automações de backup/push | Alinhar infraestrutura ao banco corporativo |

---

## ✅ Validação

**Este documento é válido?**
- ✅ Reflete 100% das dependências em `requirements.txt`
- ✅ Todas as versões estão corretas
- ✅ Todas as tecnologias listadas estão em uso

**Próxima revisão:** Mensal (todo dia 1º)

---

**Responsável:** Time de Desenvolvimento  
**Aprovado por:** Tech Lead



