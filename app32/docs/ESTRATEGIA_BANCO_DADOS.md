# 🗄️ Estratégia de Banco de Dados - Desenvolvimento e Produção

## 📊 Situação Atual (Diagnóstico)

### O Que Está Acontecendo?

Atualmente temos **DOIS** bancos PostgreSQL:

```
┌─────────────────────────────────────────────────────────────┐
│                    MÁQUINA LOCAL                            │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │  PostgreSQL Local (Porta 5432)                     │   │
│  │  Database: bd_app_versus                           │   │
│  │  Status: ✅ 49 tabelas com dados                   │   │
│  └────────────────────────────────────────────────────┘   │
│                          ▲                                  │
│                          │                                  │
│                          │ conecta via host.docker.internal│
│  ┌──────────────────────┼─────────────────────────────┐   │
│  │  Docker Container    │                             │   │
│  │                      │                             │   │
│  │  ┌───────────────────┴──────────────┐             │   │
│  │  │  App Flask (porta 5003)          │             │   │
│  │  │  Conecta: localhost:5432         │             │   │
│  │  └──────────────────────────────────┘             │   │
│  │                                                    │   │
│  │  ┌──────────────────────────────────┐             │   │
│  │  │  PostgreSQL Container (5433)     │             │   │
│  │  │  Database: bd_app_versus_dev     │             │   │
│  │  │  Status: ⚠️ VAZIO (0 tabelas)    │             │   │
│  │  └──────────────────────────────────┘             │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Problema:** O container Docker tem um banco PostgreSQL, mas **NÃO ESTÁ SENDO USADO**. A aplicação no Docker conecta no banco local da sua máquina.

---

## 🎯 Estratégias Possíveis

### Estratégia 1: Docker Completo (RECOMENDADO) 🌟

**O que é:** Tudo dentro do Docker, incluindo banco de dados.

**Vantagens:**
- ✅ Ambiente 100% isolado e replicável
- ✅ Fácil compartilhar com equipe (todos usam mesma configuração)
- ✅ Mais próximo do ambiente de produção
- ✅ Não precisa instalar PostgreSQL local
- ✅ Dados persistem em volumes Docker

**Desvantagens:**
- ⚠️ Precisa migrar dados existentes
- ⚠️ Overhead de performance (mínimo)

**Quando usar:** Desenvolvimento em equipe, CI/CD, deploy

**Como funciona:**
```yaml
# docker-compose.dev.yml
app_dev:
  environment:
    # Conecta no PostgreSQL do container
    DATABASE_URL: postgresql://postgres:dev_password@db_dev:5432/bd_app_versus_dev
  depends_on:
    db_dev:
      condition: service_healthy
```

---

### Estratégia 2: Híbrido (ATUAL)

**O que é:** App no Docker, mas banco de dados na máquina local.

**Vantagens:**
- ✅ Dados persistem fora do Docker
- ✅ Performance nativa (sem virtualização)
- ✅ Fácil acessar dados com ferramentas locais

**Desvantagens:**
- ❌ Ambiente não é totalmente replicável
- ❌ Precisa PostgreSQL instalado local
- ❌ Configuração diferente entre dev e prod
- ❌ Dificulta CI/CD

**Quando usar:** Desenvolvimento solo com banco legado

**Como funciona:**
```yaml
# docker-compose.dev.yml (atual)
app_dev:
  environment:
    # Conecta na máquina host
    DATABASE_URL: postgresql://postgres:*Paraiso1978@host.docker.internal:5432/bd_app_versus
```

---

### Estratégia 3: Sem Docker (Tradicional)

**O que é:** Tudo direto na máquina (sem Docker).

**Vantagens:**
- ✅ Mais simples inicialmente
- ✅ Performance máxima
- ✅ Debugging mais fácil

**Desvantagens:**
- ❌ "Funciona na minha máquina" 
- ❌ Difícil replicar ambiente
- ❌ Precisa instalar tudo manualmente

**Quando usar:** Prototipagem rápida, aprendizado

---

## 🏗️ Recomendação para Desenvolvimento

### Opção A: Desenvolvimento com Docker Completo (MELHOR) 🌟

```
Desenvolvimento              Produção
┌──────────────┐            ┌──────────────┐
│   Docker     │            │   Docker     │
│  ┌────────┐  │            │  ┌────────┐  │
│  │  App   │  │            │  │  App   │  │
│  └───┬────┘  │            │  └───┬────┘  │
│      │       │            │      │       │
│  ┌───▼────┐  │            │  ┌───▼────┐  │
│  │ PG Dev │  │            │  │ PG Prod│  │
│  └────────┘  │            │  └────────┘  │
└──────────────┘            └──────────────┘
  Mesma estrutura!            Escalável!
```

**Fluxo de trabalho:**
1. `docker-compose up` → tudo inicia
2. Desenvolve código
3. Dados persistem em volume Docker
4. Commit código + migrations
5. Deploy: mesmo `docker-compose` em produção

---

### Opção B: Desenvolvimento Híbrido

```
Desenvolvimento              Produção
┌──────────────┐            ┌──────────────┐
│   Docker     │            │   Docker     │
│  ┌────────┐  │            │  ┌────────┐  │
│  │  App   │  │            │  │  App   │  │
│  └───┬────┘  │            │  └───┬────┘  │
└──────┼───────┘            │      │       │
       │                    │  ┌───▼────┐  │
   ┌───▼────┐               │  │ PG Prod│  │
   │ PG Local│              │  └────────┘  │
   └────────┘               └──────────────┘
   Na máquina                Diferente!
```

**Fluxo de trabalho:**
1. PostgreSQL local rodando
2. `docker-compose up` → app inicia
3. App conecta em `host.docker.internal`
4. Backup antes de deploy
5. Restore em produção

---

## 🛠️ Como Implementar - Opção A (Docker Completo)

### Passo 1: Migrar Dados para Container

```bash
# 1. Parar containers
docker-compose -f docker-compose.dev.yml down

# 2. Backup do banco local
pg_dump -h localhost -p 5432 -U postgres bd_app_versus > backup_local.sql

# 3. Ajustar docker-compose.dev.yml (veja abaixo)

# 4. Iniciar container PostgreSQL
docker-compose -f docker-compose.dev.yml up -d db_dev

# 5. Aguardar inicialização (20 segundos)
timeout /t 20

# 6. Criar estrutura (rodar migrations)
python scripts/init_app.py --env docker

# 7. Restaurar dados
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev < backup_local.sql

# 8. Iniciar aplicação
docker-compose -f docker-compose.dev.yml up -d
```

### Passo 2: Ajustar docker-compose.dev.yml

```yaml
services:
  app_dev:
    environment:
      # ANTES (conectava no local)
      # DATABASE_URL: postgresql://postgres:*Paraiso1978@host.docker.internal:5432/bd_app_versus
      
      # DEPOIS (conecta no container)
      DATABASE_URL: postgresql://postgres:dev_password@db_dev:5432/bd_app_versus_dev
    
    depends_on:
      db_dev:
        condition: service_healthy  # Descomenta essa linha
```

### Passo 3: Variáveis de Ambiente

Criar `.env.docker`:
```bash
# Docker Development
FLASK_APP=app_pev.py
FLASK_ENV=development
DATABASE_URL=postgresql://postgres:dev_password@db_dev:5432/bd_app_versus_dev
REDIS_URL=redis://redis_dev:6379/0
```

---

## 🛠️ Como Implementar - Opção B (Híbrido - Atual)

**Se quiser manter híbrido mas com dados no container:**

```bash
# 1. Backup do banco local
pg_dump -h localhost -p 5432 -U postgres bd_app_versus > backup_local.sql

# 2. Container já existe, só precisa popular
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev < backup_local.sql

# 3. Testar conexão no container
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev -c "\dt"
```

**Para testar app com banco do container:**

```bash
# Temporariamente, mudar variável de ambiente
set DATABASE_URL=postgresql://postgres:dev_password@localhost:5433/bd_app_versus_dev
python app_pev.py

# Ou criar um config_docker.py separado
```

---

## 🚀 Fluxo de Trabalho Dia a Dia

### Cenário 1: Docker Completo (Recomendado)

```bash
# Manhã - Iniciar trabalho
cd C:\GestaoVersus\app31
docker-compose -f docker-compose.dev.yml up -d

# Verificar status
docker-compose -f docker-compose.dev.yml ps

# Acessar logs
docker-compose -f docker-compose.dev.yml logs -f app_dev

# Desenvolvimento
# - Edita código (hot-reload automático)
# - Acessa http://localhost:5003
# - Usa Adminer em http://localhost:8080

# Fim do dia
docker-compose -f docker-compose.dev.yml down
# Dados persistem em volume!
```

### Cenário 2: Híbrido (Atual)

```bash
# Manhã
# 1. Iniciar PostgreSQL local (já inicia com Windows)
# 2. Iniciar Docker
docker-compose -f docker-compose.dev.yml up -d

# Desenvolvimento
# - App: http://localhost:5003
# - Banco local: localhost:5432 (DBeaver, pgAdmin)
# - Banco container: localhost:5433 (opcional)

# Fim do dia
docker-compose -f docker-compose.dev.yml down
```

---

## 📦 Produção

### Deploy com Docker (Cloud Run, AWS ECS, etc)

```yaml
# docker-compose.prod.yml
services:
  app:
    environment:
      DATABASE_URL: postgresql://user:pass@db-prod.servidor.com:5432/bd_app_versus
      # Ou Cloud SQL, RDS, etc
```

**Banco de dados em produção:**
- ✅ **Cloud SQL** (Google Cloud)
- ✅ **RDS** (AWS)
- ✅ **Azure Database for PostgreSQL**
- ✅ **DigitalOcean Managed Database**

**NÃO usar container PostgreSQL em produção** (sem redundância, backups, etc)

---

## 🎓 Resumo - Qual Escolher?

| Aspecto | Docker Completo | Híbrido | Sem Docker |
|---------|----------------|---------|------------|
| **Facilidade inicial** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Replicabilidade** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Performance** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Trabalho em equipe** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **CI/CD** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Próximo de produção** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

### 🏆 Recomendação Final

**Para este projeto:**
- **Desenvolvimento solo atual:** Use **Híbrido** (já funciona)
- **Preparar para equipe/produção:** Migre para **Docker Completo**

---

## 🆘 Problemas Comuns

### "Não consigo conectar no banco do container"

```bash
# Verificar se container está rodando
docker ps | findstr postgres

# Verificar logs
docker logs gestaoversos_db_dev

# Testar conexão
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev
```

### "Container não mantém dados"

```bash
# Verificar volumes
docker volume ls | findstr postgres

# Volume deve existir:
# app31_postgres_data_dev
```

### "App não conecta no banco"

```bash
# Verificar variável de ambiente
docker exec gestaoversos_app_dev env | findstr DATABASE_URL

# Deve mostrar a URL correta
```

---

## 📚 Próximos Passos

Escolha uma estratégia e siga o guia de implementação acima!

**Dúvidas?** Consulte:
- `/docs/governance/DECISION_LOG.md` - Decisões arquiteturais
- `GUIA_COMPLETO_DOCKER_DESENVOLVIMENTO.md` - Docker detalhado
- Este arquivo!

---

**Última atualização:** 20/10/2025  
**Autor:** Sistema GestaoVersus  
**Status:** ✅ Documentação completa

