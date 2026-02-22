# 🚀 Plano de Migração para Produção - GestaoVersus

## 🎯 Objetivo

Preparar o sistema para uso em produção com clientes reais, mantendo ambiente de desenvolvimento seguro e funcional.

---

## 📊 Arquitetura Recomendada

### ❌ Arquitetura Incorreta (O que NÃO fazer)

```
┌─────────────────┐        ┌─────────────────┐
│  PRODUÇÃO       │        │  DESENVOLVIMENTO│
│  (Clientes)     │ ─────▶ │  (Testes)       │
│                 │ backup │                 │
│  PostgreSQL     │        │  PostgreSQL     │
│  Container ❌   │        │  com dados      │
└─────────────────┘        │  de clientes ❌ │
                           └─────────────────┘
```

**Problemas:**
- ❌ Container PostgreSQL em produção (sem redundância)
- ❌ Dados de clientes em ambiente dev (LGPD)
- ❌ Fluxo invertido (prod → dev)

---

### ✅ Arquitetura Correta (Recomendada)

```
┌──────────────────────────────────────────────────────────────┐
│                    FLUXO DE DADOS                            │
│                                                              │
│  DESENVOLVIMENTO ──▶ STAGING ──▶ PRODUÇÃO                   │
│  (Migrations)     (Testes)    (Clientes)                    │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│  DESENVOLVIMENTO    │
│  (Sua máquina)      │
│                     │
│  ┌───────────────┐  │
│  │ Docker        │  │
│  │ ├─ App        │  │
│  │ └─ PostgreSQL │  │
│  │    (Dev)      │  │
│  └───────────────┘  │
│                     │
│  Dados: Fictícios   │
│  ou Anonimizados    │
└─────────────────────┘
          │
          │ git push + migrations
          ▼
┌─────────────────────┐
│  STAGING            │
│  (Servidor teste)   │
│                     │
│  ┌───────────────┐  │
│  │ Docker        │  │
│  │ └─ App        │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │ PostgreSQL    │  │
│  │ (Gerenciado)  │  │
│  └───────────────┘  │
│                     │
│  Dados: Cópia de    │
│  prod (sanitizada)  │
└─────────────────────┘
          │
          │ Deploy após testes
          ▼
┌─────────────────────┐
│  PRODUÇÃO           │
│  (Cloud)            │
│                     │
│  ┌───────────────┐  │
│  │ Cloud Run/ECS │  │
│  │ └─ App        │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │ Cloud SQL     │  │
│  │ ou RDS        │  │
│  │               │  │
│  │ ✅ Backup     │  │
│  │ ✅ Redundância│  │
│  │ ✅ Segurança  │  │
│  └───────────────┘  │
│                     │
│  Dados: REAIS       │
│  (Clientes)         │
└─────────────────────┘
```

---

## 🛠️ FASE 1: Preparar Desenvolvimento (AGORA)

### Objetivo: Migrar para Docker Completo localmente

### Passo 1.1: Backup Completo

```bash
# Criar diretório de backups
mkdir backups
cd backups

# Backup do banco atual
pg_dump -h localhost -p 5432 -U postgres bd_app_versus > backup_pre_migracao_$(date +%Y%m%d_%H%M%S).sql

# Voltar para raiz
cd ..
```

### Passo 1.2: Ajustar docker-compose.dev.yml

**Alterações necessárias:**

```yaml
# docker-compose.dev.yml
services:
  app_dev:
    environment:
      # ANTES (conecta no banco local da máquina)
      # DATABASE_URL: postgresql://postgres:*Paraiso1978@host.docker.internal:5432/bd_app_versus
      
      # DEPOIS (conecta no container PostgreSQL)
      DATABASE_URL: postgresql://postgres:dev_password@db_dev:5432/bd_app_versus_dev
    
    depends_on:
      db_dev:
        condition: service_healthy  # DESCOMENTAR esta linha
      redis_dev:
        condition: service_healthy
```

### Passo 1.3: Migrar Dados para Container

```bash
# 1. Parar containers
docker-compose -f docker-compose.dev.yml down

# 2. Iniciar apenas PostgreSQL
docker-compose -f docker-compose.dev.yml up -d db_dev

# 3. Aguardar inicialização
timeout /t 20

# 4. Restaurar dados
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev < backups/backup_pre_migracao_*.sql

# 5. Verificar
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev -c "\dt"

# 6. Iniciar aplicação
docker-compose -f docker-compose.dev.yml up -d
```

### Passo 1.4: Testar

```bash
# Verificar status
docker-compose -f docker-compose.dev.yml ps

# Ver logs
docker-compose -f docker-compose.dev.yml logs -f app_dev

# Acessar aplicação
# http://localhost:5003
```

**✅ Após isso:** Ambiente dev totalmente em Docker!

---

## 🧪 FASE 2: Configurar Ambiente de Staging (Opcional mas Recomendado)

### Objetivo: Ambiente intermediário para testes antes de produção

### Opção A: Staging na Cloud (Recomendado)

```yaml
# docker-compose.staging.yml
version: '3.8'

services:
  app_staging:
    build: .
    environment:
      FLASK_ENV: production
      DATABASE_URL: ${STAGING_DATABASE_URL}  # Cloud SQL/RDS
      SECRET_KEY: ${STAGING_SECRET_KEY}
    ports:
      - "5002:5002"
```

### Opção B: Staging Local (Mais simples)

```bash
# Usar docker-compose.dev.yml mas com variáveis diferentes
cp docker-compose.dev.yml docker-compose.staging.yml
# Ajustar portas e nomes para não conflitar
```

**Staging serve para:**
- ✅ Testar deploys
- ✅ Testar migrations em ambiente "real"
- ✅ Testes de integração
- ✅ Demos para clientes

---

## 🚀 FASE 3: Deploy em Produção

### 3.1: Escolher Plataforma

| Plataforma | Dificuldade | Custo (estimado) | Recomendação |
|------------|-------------|------------------|--------------|
| **Google Cloud Run** | ⭐⭐ Fácil | ~R$50-200/mês | ⭐⭐⭐⭐⭐ Melhor |
| **Railway** | ⭐ Muito Fácil | ~$20-50/mês | ⭐⭐⭐⭐ Bom início |
| **AWS ECS** | ⭐⭐⭐ Médio | ~R$100-300/mês | ⭐⭐⭐⭐⭐ Escalável |
| **DigitalOcean App** | ⭐⭐ Fácil | ~$30-100/mês | ⭐⭐⭐⭐ Simples |
| **Heroku** | ⭐ Muito Fácil | ~$25-100/mês | ⭐⭐⭐ OK |

**Recomendação:** **Google Cloud Run** + **Cloud SQL**

**Por quê?**
- ✅ Pay-per-use (não paga quando não usa)
- ✅ Escala automaticamente
- ✅ Cloud SQL totalmente gerenciado
- ✅ Backups automáticos
- ✅ SSL gratuito
- ✅ Fácil de configurar

### 3.2: Configurar Banco de Dados de Produção

#### Opção 1: Google Cloud SQL (Recomendado)

```bash
# Criar instância Cloud SQL
gcloud sql instances create gestaoversos-prod \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \  # Pequeno, pode escalar depois
    --region=southamerica-east1 \  # São Paulo
    --backup \
    --backup-start-time=03:00 \  # 3h da manhã
    --maintenance-window-day=SUN \
    --maintenance-window-hour=4

# Criar banco de dados
gcloud sql databases create bd_app_versus \
    --instance=gestaoversos-prod

# Criar usuário
gcloud sql users create app_user \
    --instance=gestaoversos-prod \
    --password=SENHA_SEGURA_AQUI
```

**Características:**
- ✅ Backup automático diário
- ✅ Point-in-time recovery (até 7 dias)
- ✅ Alta disponibilidade
- ✅ Patches automáticos
- ✅ Monitoramento integrado

**Custo estimado:** R$50-150/mês (tier pequeno)

#### Opção 2: AWS RDS

```bash
# Criar via AWS Console ou CLI
aws rds create-db-instance \
    --db-instance-identifier gestaoversos-prod \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.3 \
    --allocated-storage 20 \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00"
```

#### Opção 3: Railway (Mais simples para começar)

```bash
# Via interface web Railway.app
1. Criar conta em railway.app
2. New Project → Deploy PostgreSQL
3. Copiar DATABASE_URL
```

**Características:**
- ✅ Setup em 2 minutos
- ✅ Backups automáticos
- ⚠️ Menos controle
- ⚠️ Pode ser mais caro ao escalar

**Custo estimado:** $10-30/mês

### 3.3: Deploy da Aplicação

#### Deploy no Google Cloud Run

```bash
# 1. Configurar projeto
gcloud config set project SEU_PROJETO_ID

# 2. Build e push da imagem
gcloud builds submit --tag gcr.io/SEU_PROJETO_ID/gestaoversos

# 3. Deploy
gcloud run deploy gestaoversos \
    --image gcr.io/SEU_PROJETO_ID/gestaoversos \
    --platform managed \
    --region southamerica-east1 \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=postgresql://user:pass@/bd_app_versus?host=/cloudsql/INSTANCE_CONNECTION_NAME" \
    --set-env-vars "SECRET_KEY=CHAVE_SECRETA_FORTE" \
    --add-cloudsql-instances INSTANCE_CONNECTION_NAME \
    --memory 512Mi
```

**Resultado:** URL pública como `https://gestaoversos-xxx.run.app`

### 3.4: Configurar Domínio (Opcional)

```bash
# Mapear domínio customizado
gcloud run domain-mappings create \
    --service gestaoversos \
    --domain app.gestaoversos.com.br
```

---

## 🔄 FASE 4: Fluxo de Trabalho Contínuo

### 4.1: Desenvolvimento → Produção (Fluxo Correto)

```
┌─────────────────────────────────────────────────────┐
│  DESENVOLVIMENTO (Local)                            │
│                                                     │
│  1. Desenvolve feature                              │
│  2. Cria migration: flask db migrate                │
│  3. Testa localmente: flask db upgrade              │
│  4. Commit: git commit -am "Feature X"              │
│  5. Push: git push origin main                      │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  STAGING (Opcional)                                 │
│                                                     │
│  1. Deploy automático ou manual                     │
│  2. Roda migrations: flask db upgrade               │
│  3. Testes de integração                            │
│  4. Aprovação para produção                         │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  PRODUÇÃO                                           │
│                                                     │
│  1. Deploy (Cloud Run/ECS)                          │
│  2. Roda migrations: flask db upgrade               │
│  3. Verificação de saúde                            │
│  4. Monitoramento                                   │
└─────────────────────────────────────────────────────┘
```

### 4.2: E se Precisar de Dados de Produção em Dev?

**⚠️ NUNCA restaure backup direto!**

**✅ Use dados anonimizados:**

```sql
-- Script para anonimizar dados
-- sanitize_backup.sql

-- Anonimizar usuários
UPDATE users SET
    email = 'user_' || id || '@exemplo.com',
    phone = '11900000000',
    cpf = NULL;

-- Anonimizar empresas
UPDATE companies SET
    cnpj = NULL,
    phone = '11300000000';

-- Remover dados sensíveis
DELETE FROM user_logs WHERE created_at < NOW() - INTERVAL '30 days';
```

**Processo:**

```bash
# 1. Backup de produção
pg_dump -h PROD_HOST -U PROD_USER bd_app_versus > prod_backup.sql

# 2. Restaurar em banco temporário local
createdb bd_temp
psql -d bd_temp < prod_backup.sql

# 3. Anonimizar
psql -d bd_temp < scripts/sanitize_backup.sql

# 4. Dump anonimizado
pg_dump bd_temp > sanitized_backup.sql

# 5. Restaurar em dev
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev < sanitized_backup.sql

# 6. Limpar
dropdb bd_temp
```

### 4.3: Backups e Recuperação

#### Backups Automáticos (Produção)

**Cloud SQL/RDS já faz automaticamente!**

- ✅ Backup diário
- ✅ Retenção de 7-30 dias
- ✅ Point-in-time recovery

#### Backup Manual (Quando necessário)

```bash
# Backup completo
gcloud sql export sql gestaoversos-prod \
    gs://gestaoversos-backups/manual_$(date +%Y%m%d).sql \
    --database=bd_app_versus

# Ou via pg_dump se tiver acesso direto
pg_dump -h PROD_HOST -U PROD_USER bd_app_versus > backup_manual.sql
```

#### Recuperação de Desastre

```bash
# Restaurar de backup específico (Cloud SQL)
gcloud sql backups restore BACKUP_ID \
    --backup-instance=gestaoversos-prod

# Ou restaurar de arquivo
gcloud sql import sql gestaoversos-prod \
    gs://gestaoversos-backups/backup_20250120.sql \
    --database=bd_app_versus
```

---

## 📋 CHECKLIST COMPLETO

### ✅ Fase 1: Preparar Dev (FAZER AGORA)

- [ ] Fazer backup completo do banco atual
- [ ] Ajustar `docker-compose.dev.yml`
- [ ] Migrar dados para container Docker
- [ ] Testar aplicação com banco containerizado
- [ ] Documentar processo

**Tempo estimado:** 1-2 horas

### ✅ Fase 2: Configurar Migrations (Antes de Produção)

- [ ] Instalar Flask-Migrate
- [ ] Criar migrations do schema atual
- [ ] Testar migrations em ambiente limpo
- [ ] Documentar processo de migration

**Tempo estimado:** 2-4 horas

### ✅ Fase 3: Setup Produção (Quando pronto para clientes)

- [ ] Escolher plataforma (Cloud Run, Railway, AWS)
- [ ] Criar banco de dados gerenciado
- [ ] Configurar variáveis de ambiente
- [ ] Fazer deploy inicial
- [ ] Testar aplicação em produção
- [ ] Configurar domínio (se necessário)
- [ ] Configurar SSL (geralmente automático)

**Tempo estimado:** 4-8 horas

### ✅ Fase 4: Operação (Contínuo)

- [ ] Monitorar logs
- [ ] Verificar backups diários
- [ ] Testar recuperação de backup (mensal)
- [ ] Atualizar dependências (mensal)
- [ ] Revisar custos (mensal)

---

## 💰 Estimativa de Custos Mensais

### Opção 1: Google Cloud (Recomendado)

| Serviço | Tier | Custo Mensal (estimado) |
|---------|------|-------------------------|
| Cloud Run | 1M requests | R$0-50 |
| Cloud SQL | db-f1-micro | R$50-100 |
| Cloud Storage (backups) | 10GB | R$2-5 |
| **TOTAL** | | **R$52-155/mês** |

### Opção 2: Railway (Mais simples)

| Serviço | Tier | Custo Mensal |
|---------|------|--------------|
| PostgreSQL | Starter | $10/mês |
| App | 512MB | $10-20/mês |
| **TOTAL** | | **$20-30/mês (~R$100-150)** |

### Opção 3: AWS

| Serviço | Tier | Custo Mensal (estimado) |
|---------|------|-------------------------|
| ECS Fargate | 0.5 vCPU | R$40-80 |
| RDS | db.t3.micro | R$80-150 |
| S3 (backups) | 10GB | R$2-3 |
| **TOTAL** | | **R$122-233/mês** |

**Nota:** Custos aumentam com uso (mais usuários, mais dados, mais processamento)

---

## 🔐 Segurança e Compliance

### LGPD (Lei Geral de Proteção de Dados)

✅ **Boas práticas:**

1. **Separação de ambientes**
   - Dados reais APENAS em produção
   - Dev usa dados fictícios ou anonimizados

2. **Backups seguros**
   - Criptografados
   - Acesso restrito
   - Retenção definida

3. **Logs**
   - NÃO logar dados sensíveis (CPF, senhas, etc)
   - Implementado `@auto_log_crud` já faz isso

4. **Acesso**
   - Produção: acesso restrito
   - Autenticação forte
   - Auditoria de acessos

### Checklist de Segurança

- [ ] Variáveis de ambiente (não hardcoded)
- [ ] HTTPS em produção (SSL)
- [ ] Senhas hasheadas (bcrypt) ✅
- [ ] SQL injection protegido (ORM) ✅
- [ ] Rate limiting
- [ ] Backups criptografados
- [ ] Logs sem dados sensíveis ✅
- [ ] Autenticação em todas as rotas ✅

---

## 📞 Suporte e Monitoramento

### Monitoramento Básico

```python
# Adicionar health check em app_pev.py
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Verificar conexão com banco
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
```

### Alertas

Configure alertas para:
- ❌ Aplicação down
- ⚠️ Uso de memória > 80%
- ⚠️ Uso de CPU > 80%
- ⚠️ Banco de dados lento (> 1s queries)
- ⚠️ Erros 500 frequentes

---

## 🎯 RESUMO: O Que Fazer AGORA

### Hoje (1-2 horas):

```bash
# 1. Backup
mkdir backups
pg_dump -h localhost -p 5432 -U postgres bd_app_versus > backups/backup_$(date +%Y%m%d).sql

# 2. Executar script de migração
python setup_database_strategy.py
# Escolha opção 1 (Docker Completo)

# 3. Testar
docker-compose -f docker-compose.dev.yml up -d
# Acessar http://localhost:5003
```

### Esta Semana (4-8 horas):

- [ ] Testar ambiente dev Docker completo
- [ ] Configurar Flask-Migrate
- [ ] Criar migrations do schema atual
- [ ] Testar migrations em ambiente limpo
- [ ] Escolher plataforma de hospedagem

### Próximo Mês (quando pronto para clientes):

- [ ] Deploy em produção
- [ ] Testes com usuários beta
- [ ] Configurar monitoramento
- [ ] Documentar processo de deploy
- [ ] Treinar equipe (se houver)

---

## 📚 Recursos Úteis

### Documentação

- **Google Cloud Run:** https://cloud.google.com/run/docs
- **Cloud SQL:** https://cloud.google.com/sql/docs
- **Railway:** https://docs.railway.app
- **Flask-Migrate:** https://flask-migrate.readthedocs.io

### Scripts Criados

- `setup_database_strategy.py` - Migração automatizada
- `docs/ESTRATEGIA_BANCO_DADOS.md` - Estratégias detalhadas
- `GUIA_RAPIDO_BANCO_DADOS.md` - Referência rápida

---

**Próximo passo:** Execute `python setup_database_strategy.py` e escolha opção 1!

---

**Data:** 20/10/2025  
**Versão:** 1.0  
**Status:** ✅ Pronto para implementação

