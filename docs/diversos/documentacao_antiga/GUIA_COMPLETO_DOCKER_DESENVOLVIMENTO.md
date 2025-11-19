# 🐳 Guia Completo - Docker Desenvolvimento GestaoVersus

**Versão:** 1.0  
**Data:** 20/10/2025  
**Status:** ✅ **TESTADO E APROVADO**

---

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Pré-requisitos](#-pré-requisitos)
3. [Configuração Inicial](#-configuração-inicial)
4. [Comandos Essenciais](#-comandos-essenciais)
5. [Estrutura dos Containers](#-estrutura-dos-containers)
6. [Desenvolvimento](#-desenvolvimento)
7. [Troubleshooting](#-troubleshooting)
8. [Comandos Avançados](#-comandos-avançados)
9. [Monitoramento](#-monitoramento)
10. [Backup e Restore](#-backup-e-restore)

---

## 🎯 Visão Geral

Este guia documenta o ambiente Docker completo para desenvolvimento do **GestaoVersus**, incluindo:

- ✅ **Aplicação Flask** (Python 3.9)
- ✅ **PostgreSQL 15** (Banco de dados)
- ✅ **Redis 7** (Cache e Message Broker)
- ✅ **Celery Worker** (Tasks assíncronas)
- ✅ **Adminer** (Interface web para banco)
- ✅ **MailHog** (Captura de e-mails de teste)

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                  Docker Network (Bridge)                     │
│                  gestaoversos_network_dev                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  PostgreSQL  │    │    Redis     │    │   MailHog    │  │
│  │  (Port 5433) │    │  (Port 6380) │    │  (Port 8025) │  │
│  │  ✅ Healthy  │    │  ✅ Healthy  │    │  ✅ Running  │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘  │
│         │                   │                                │
│         └───────┬───────────┘                                │
│                 │                                             │
│         ┌───────▼───────────┐                                │
│         │   Flask App       │                                │
│         │  (Port 5003)      │                                │
│         │  ✅ Running       │                                │
│         └───────┬───────────┘                                │
│                 │                                             │
│         ┌───────▼───────────┐                                │
│         │  Celery Worker    │                                │
│         │  ✅ Running       │                                │
│         └───────────────────┘                                │
│                                                               │
│  ┌──────────────┐                                            │
│  │   Adminer    │  (Gerenciador Web)                         │
│  │ (Port 8080)  │                                            │
│  │  ✅ Running  │                                            │
│  └──────────────┘                                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
    localhost:5003     localhost:8080     localhost:8025
```

---

## 🔧 Pré-requisitos

### Software Necessário

| Software | Versão Mínima | Verificação |
|----------|---------------|-------------|
| **Docker Desktop** | 20.10+ | `docker --version` |
| **Docker Compose** | 2.0+ | `docker-compose --version` |
| **Git** | 2.30+ | `git --version` |

### Recursos do Sistema

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| **RAM** | 4GB | 8GB+ |
| **CPU** | 2 cores | 4+ cores |
| **Disco** | 10GB livres | 20GB+ livres |

### Verificação Rápida

```bash
# Verificar Docker
docker --version
docker info

# Verificar Docker Compose
docker-compose --version

# Verificar recursos disponíveis
docker system df
```

---

## ⚙️ Configuração Inicial

### 1. Clone do Repositório

```bash
git clone <seu-repositorio>
cd app31
```

### 2. Configuração de Ambiente

```bash
# Copiar arquivo de configuração
cp env.development.example .env

# Editar variáveis se necessário
notepad .env  # Windows
nano .env     # Linux/Mac
```

### 3. Build das Imagens

```bash
# Build completo (primeira vez)
docker-compose -f docker-compose.dev.yml build

# Build apenas uma imagem específica
docker-compose -f docker-compose.dev.yml build app_dev
```

### 4. Iniciar os Containers

```bash
# Subir todos os containers
docker-compose -f docker-compose.dev.yml up -d

# Verificar status
docker-compose -f docker-compose.dev.yml ps
```

---

## 🚀 Comandos Essenciais

### Iniciar/Parar Serviços

```bash
# ✅ Iniciar todos os containers
docker-compose -f docker-compose.dev.yml up -d

# ⏹️ Parar todos os containers
docker-compose -f docker-compose.dev.yml stop

# 🔄 Reiniciar containers
docker-compose -f docker-compose.dev.yml restart

# 🗑️ Parar e remover containers
docker-compose -f docker-compose.dev.yml down

# 🗑️ Parar, remover containers E volumes (CUIDADO!)
docker-compose -f docker-compose.dev.yml down -v
```

### Verificação de Status

```bash
# 📊 Status de todos os containers
docker-compose -f docker-compose.dev.yml ps

# 📋 Logs em tempo real
docker-compose -f docker-compose.dev.yml logs -f

# 📋 Logs de container específico
docker logs -f gestaoversos_app_dev
docker logs -f gestaoversos_db_dev
docker logs -f gestaoversos_celery_dev
```

### Acesso aos Containers

```bash
# 🐚 Shell na aplicação Flask
docker exec -it gestaoversos_app_dev /bin/bash

# 🐚 Shell no PostgreSQL
docker exec -it gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev

# 🐚 Shell no Redis
docker exec -it gestaoversos_redis_dev redis-cli

# 🐚 Shell no Celery Worker
docker exec -it gestaoversos_celery_dev /bin/bash
```

---

## 🏗️ Estrutura dos Containers

### 📦 Container: `gestaoversos_app_dev`

**Imagem:** `app31-app_dev`  
**Porta:** `5003 → 5002`  
**Função:** Aplicação Flask principal

**Características:**
- ✅ Python 3.9-slim
- ✅ Hot-reload ativo
- ✅ Debug mode habilitado
- ✅ Volume bind para código local
- ✅ Ferramentas dev: pytest, black, flake8, ipython, ipdb

**Comandos úteis:**
```bash
# Ver logs da aplicação
docker logs -f gestaoversos_app_dev

# Executar comandos Python
docker exec gestaoversos_app_dev python -c "print('Hello Docker!')"

# Instalar nova dependência
docker exec gestaoversos_app_dev pip install nova-dependencia
```

### 🗄️ Container: `gestaoversos_db_dev`

**Imagem:** `postgres:15-alpine`  
**Porta:** `5433 → 5432`  
**Função:** Banco de dados PostgreSQL

**Características:**
- ✅ PostgreSQL 15
- ✅ Encoding UTF-8
- ✅ Locale pt_BR.UTF-8
- ✅ Volume persistente
- ✅ Health check ativo

**Comandos úteis:**
```bash
# Conectar ao banco
docker exec -it gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev

# Listar tabelas
docker exec gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev -c "\dt"

# Backup do banco
docker exec gestaoversos_db_dev pg_dump -U postgres bd_app_versus_dev > backup.sql

# Restore do banco
docker exec -i gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev < backup.sql
```

### 🔴 Container: `gestaoversos_redis_dev`

**Imagem:** `redis:7-alpine`  
**Porta:** `6380 → 6379`  
**Função:** Cache e Message Broker

**Características:**
- ✅ Redis 7
- ✅ Persistência AOF
- ✅ Health check ativo
- ✅ Volume persistente

**Comandos úteis:**
```bash
# Testar conexão
docker exec gestaoversos_redis_dev redis-cli PING

# Monitorar comandos
docker exec gestaoversos_redis_dev redis-cli MONITOR

# Limpar cache
docker exec gestaoversos_redis_dev redis-cli FLUSHALL

# Ver informações
docker exec gestaoversos_redis_dev redis-cli INFO
```

### ⚙️ Container: `gestaoversos_celery_dev`

**Imagem:** `app31-celery_worker_dev`  
**Função:** Worker para tasks assíncronas

**Características:**
- ✅ Celery 5.3.1
- ✅ Concurrency: 2 workers
- ✅ Log level: DEBUG
- ✅ Broker: Redis
- ✅ Backend: Redis

**Comandos úteis:**
```bash
# Ver logs do worker
docker logs -f gestaoversos_celery_dev

# Monitorar tasks
docker exec gestaoversos_celery_dev celery -A app_pev.celery inspect active

# Ver workers ativos
docker exec gestaoversos_celery_dev celery -A app_pev.celery inspect stats
```

### 🌐 Container: `gestaoversos_adminer_dev`

**Imagem:** `adminer:latest`  
**Porta:** `8080`  
**Função:** Interface web para gerenciar banco

**Acesso:**
- **URL:** http://localhost:8080
- **Sistema:** PostgreSQL
- **Servidor:** db_dev
- **Usuário:** postgres
- **Senha:** dev_password
- **Base:** bd_app_versus_dev

### 📧 Container: `gestaoversos_mailhog_dev`

**Imagem:** `mailhog/mailhog:latest`  
**Portas:** `8025` (Web), `1025` (SMTP)  
**Função:** Captura e-mails de teste

**Acesso:**
- **Web UI:** http://localhost:8025
- **SMTP:** localhost:1025

---

## 💻 Desenvolvimento

### Hot-Reload

O ambiente está configurado para **hot-reload automático**:

```bash
# Modificar arquivo Python
echo "print('Teste hot-reload')" >> test.py

# Verificar logs para ver a atualização automática
docker logs -f gestaoversos_app_dev
```

### Debugging

#### 1. Debug com IPython

```python
# No código Python
import ipdb; ipdb.set_trace()
```

#### 2. Debug com Logs

```python
# No código Python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

#### 3. Debug do Banco

```bash
# Conectar e debugar SQL
docker exec -it gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev

# Ver queries lentas
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

### Testes

#### 1. Executar Testes Unitários

```bash
# Todos os testes
docker exec gestaoversos_app_dev pytest

# Teste específico
docker exec gestaoversos_app_dev pytest tests/test_models.py

# Teste com coverage
docker exec gestaoversos_app_dev pytest --cov=app_pev
```

#### 2. Linting e Formatação

```bash
# Formatar código
docker exec gestaoversos_app_dev black .

# Verificar linting
docker exec gestaoversos_app_dev flake8 .
```

### Dependências

#### 1. Adicionar Nova Dependência

```bash
# Instalar no container
docker exec gestaoversos_app_dev pip install nova-dependencia

# Adicionar ao requirements.txt
echo "nova-dependencia==1.0.0" >> requirements.txt

# Rebuild da imagem
docker-compose -f docker-compose.dev.yml build app_dev
```

#### 2. Atualizar Dependências

```bash
# Atualizar pip
docker exec gestaoversos_app_dev pip install --upgrade pip

# Atualizar todas as dependências
docker exec gestaoversos_app_dev pip install --upgrade -r requirements.txt
```

---

## 🔧 Troubleshooting

### Problemas Comuns

#### 1. Container não inicia

**Sintoma:** Container fica em status `Restarting`

**Diagnóstico:**
```bash
# Ver logs do container
docker logs gestaoversos_app_dev

# Verificar recursos
docker stats
```

**Soluções:**
- Verificar se há conflito de portas
- Verificar recursos disponíveis (RAM/CPU)
- Verificar configuração do .env

#### 2. Banco não conecta

**Sintoma:** Erro de conexão com PostgreSQL

**Diagnóstico:**
```bash
# Verificar se PostgreSQL está rodando
docker exec gestaoversos_db_dev pg_isready -U postgres

# Verificar logs do banco
docker logs gestaoversos_db_dev
```

**Soluções:**
- Aguardar health check do PostgreSQL
- Verificar variáveis de ambiente DATABASE_URL
- Reiniciar containers: `docker-compose restart`

#### 3. Redis não conecta

**Sintoma:** Erro de conexão com Redis

**Diagnóstico:**
```bash
# Testar conexão Redis
docker exec gestaoversos_redis_dev redis-cli PING
```

**Soluções:**
- Verificar se Redis está healthy
- Verificar variáveis REDIS_URL
- Reiniciar Redis: `docker-compose restart redis_dev`

#### 4. Porta já em uso

**Sintoma:** `bind: address already in use`

**Diagnóstico:**
```bash
# Verificar portas em uso
netstat -tulpn | grep :5003
netstat -tulpn | grep :5433
```

**Soluções:**
- Parar outros serviços usando as portas
- Alterar portas no docker-compose.dev.yml
- Usar `docker-compose down` antes de subir

#### 5. Volume não persiste

**Sintoma:** Dados perdidos ao reiniciar

**Diagnóstico:**
```bash
# Verificar volumes
docker volume ls
docker volume inspect app31_postgres_data_dev
```

**Soluções:**
- Verificar se não foi usado `docker-compose down -v`
- Verificar permissões do volume
- Recriar volume se necessário

### Logs de Debug

#### 1. Logs Detalhados

```bash
# Logs de todos os containers
docker-compose -f docker-compose.dev.yml logs --tail=100

# Logs com timestamps
docker-compose -f docker-compose.dev.yml logs -t

# Logs de container específico
docker logs --tail=50 gestaoversos_app_dev
```

#### 2. Monitoramento em Tempo Real

```bash
# Monitorar todos os containers
docker-compose -f docker-compose.dev.yml logs -f

# Monitorar apenas aplicação
docker logs -f gestaoversos_app_dev

# Monitorar recursos
docker stats
```

---

## 🚀 Comandos Avançados

### Gerenciamento de Imagens

```bash
# Listar imagens
docker images

# Remover imagens não utilizadas
docker image prune

# Remover todas as imagens não utilizadas
docker image prune -a

# Rebuild forçado (sem cache)
docker-compose -f docker-compose.dev.yml build --no-cache
```

### Gerenciamento de Volumes

```bash
# Listar volumes
docker volume ls

# Inspecionar volume
docker volume inspect app31_postgres_data_dev

# Backup de volume
docker run --rm -v app31_postgres_data_dev:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore de volume
docker run --rm -v app31_postgres_data_dev:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

### Gerenciamento de Networks

```bash
# Listar networks
docker network ls

# Inspecionar network
docker network inspect app31_gestaoversos_network_dev

# Criar network customizada
docker network create minha_network
```

### Limpeza do Sistema

```bash
# Limpeza geral
docker system prune

# Limpeza completa (CUIDADO!)
docker system prune -a --volumes

# Remover containers parados
docker container prune

# Remover volumes não utilizados
docker volume prune
```

---

## 📊 Monitoramento

### Status dos Containers

```bash
# Status detalhado
docker-compose -f docker-compose.dev.yml ps

# Status com recursos
docker stats

# Status de health checks
docker inspect gestaoversos_db_dev | grep -A 10 Health
```

### Monitoramento de Recursos

```bash
# Uso de recursos em tempo real
docker stats --no-stream

# Informações do sistema Docker
docker system df

# Informações detalhadas
docker system info
```

### Monitoramento de Logs

```bash
# Logs com filtro por nível
docker logs --since 1h gestaoversos_app_dev | grep ERROR

# Logs com filtro por texto
docker logs gestaoversos_app_dev 2>&1 | grep "database"

# Contar linhas de log
docker logs gestaoversos_app_dev | wc -l
```

---

## 💾 Backup e Restore

### Backup do Banco de Dados

#### 1. Backup Completo

```bash
# Backup com timestamp
docker exec gestaoversos_db_dev pg_dump -U postgres bd_app_versus_dev > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup comprimido
docker exec gestaoversos_db_dev pg_dump -U postgres bd_app_versus_dev | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

#### 2. Backup de Tabelas Específicas

```bash
# Backup de tabela específica
docker exec gestaoversos_db_dev pg_dump -U postgres -t companies bd_app_versus_dev > backup_companies.sql

# Backup de schema específico
docker exec gestaoversos_db_dev pg_dump -U postgres -n public bd_app_versus_dev > backup_schema_public.sql
```

### Restore do Banco de Dados

#### 1. Restore Completo

```bash
# Restore de arquivo SQL
docker exec -i gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev < backup.sql

# Restore de arquivo comprimido
gunzip -c backup.sql.gz | docker exec -i gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev
```

#### 2. Restore com Criação de Banco

```bash
# Criar novo banco e restaurar
docker exec gestaoversos_db_dev createdb -U postgres novo_banco
gunzip -c backup.sql.gz | docker exec -i gestaoversos_db_dev psql -U postgres -d novo_banco
```

### Backup de Volumes

#### 1. Backup de Volume PostgreSQL

```bash
# Backup do volume completo
docker run --rm -v app31_postgres_data_dev:/data -v $(pwd):/backup alpine tar czf /backup/postgres_volume_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

#### 2. Restore de Volume PostgreSQL

```bash
# Restore do volume
docker run --rm -v app31_postgres_data_dev:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_volume_20251020_163000.tar.gz -C /data
```

### Scripts de Backup Automatizado

#### 1. Script de Backup Diário

```bash
#!/bin/bash
# backup_daily.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Criar diretório se não existir
mkdir -p $BACKUP_DIR

# Backup do banco
docker exec gestaoversos_db_dev pg_dump -U postgres bd_app_versus_dev | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Backup do volume
docker run --rm -v app31_postgres_data_dev:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/volume_backup_$DATE.tar.gz -C /data .

# Manter apenas últimos 7 backups
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
```

#### 2. Script de Restore

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <arquivo_backup>"
    exit 1
fi

# Restore do banco
gunzip -c $BACKUP_FILE | docker exec -i gestaoversos_db_dev psql -U postgres -d bd_app_versus_dev

echo "Restore concluído: $BACKUP_FILE"
```

---

## 🎯 Checklist de Validação

### ✅ Inicialização

- [ ] Docker Desktop rodando
- [ ] Arquivo .env configurado
- [ ] Build das imagens concluído
- [ ] Todos os containers iniciados
- [ ] Health checks OK (PostgreSQL, Redis)

### ✅ Conectividade

- [ ] Aplicação acessível em http://localhost:5003
- [ ] Adminer acessível em http://localhost:8080
- [ ] MailHog acessível em http://localhost:8025
- [ ] PostgreSQL conectável na porta 5433
- [ ] Redis conectável na porta 6380

### ✅ Funcionalidades

- [ ] Hot-reload funcionando
- [ ] Logs aparecendo corretamente
- [ ] Banco de dados respondendo
- [ ] Cache Redis funcionando
- [ ] Celery worker processando tasks

### ✅ Desenvolvimento

- [ ] Debug com IPython funcionando
- [ ] Testes executando
- [ ] Linting e formatação OK
- [ ] Dependências instalando corretamente
- [ ] Backup e restore funcionando

---

## 📞 Suporte

### Logs Importantes

```bash
# Logs da aplicação
docker logs gestaoversos_app_dev

# Logs do banco
docker logs gestaoversos_db_dev

# Logs do Redis
docker logs gestaoversos_redis_dev

# Logs do Celery
docker logs gestaoversos_celery_dev
```

### Comandos de Diagnóstico

```bash
# Status geral
docker-compose -f docker-compose.dev.yml ps

# Recursos utilizados
docker stats

# Informações do sistema
docker system info

# Espaço em disco
docker system df
```

### Reset Completo

```bash
# ⚠️ CUIDADO: Remove tudo!
docker-compose -f docker-compose.dev.yml down -v
docker system prune -a --volumes
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

---

## 📚 Referências

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Redis Docker Hub](https://hub.docker.com/_/redis)
- [Adminer Docker Hub](https://hub.docker.com/_/adminer)
- [MailHog Docker Hub](https://hub.docker.com/r/mailhog/mailhog)

---

**Documentado por:** Cursor AI  
**Validado em:** 20/10/2025  
**Versão:** 1.0  
**Status:** ✅ **APROVADO PARA PRODUÇÃO**
