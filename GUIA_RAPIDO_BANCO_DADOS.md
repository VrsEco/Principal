# 🚀 Guia Rápido - Banco de Dados Dev/Prod

## 📍 Situação Atual (O que você tem AGORA)

```
Você tem 2 bancos PostgreSQL:

📦 BANCO LOCAL (porta 5432)
   └─ bd_app_versus
   └─ 49 tabelas com DADOS
   └─ App Docker CONECTA AQUI ✅
   
🐳 BANCO DOCKER (porta 5433)  
   └─ bd_app_versus_dev
   └─ 0 tabelas (VAZIO)
   └─ Ninguém usa ❌
```

**Problema:** Você não consegue testar no Docker porque os dados estão no banco LOCAL, não no container.

---

## 🎯 3 Opções Disponíveis

### Opção 1: Docker Completo (MELHOR para longo prazo) 🌟

```
┌─────────────────────────────┐
│   Docker Container          │
│                             │
│   App ──▶ PostgreSQL        │
│   (5003)   (bd_app_versus_dev)│
│                             │
│   Dados no volume Docker    │
└─────────────────────────────┘
```

**Quando usar:**
- ✅ Trabalho em equipe
- ✅ Preparar para produção
- ✅ CI/CD
- ✅ Ambiente replicável

**Como ativar:**
```bash
python setup_database_strategy.py
# Escolha opção 1
```

---

### Opção 2: Híbrido (O que você tem AGORA) 

```
┌─────────────────────────────┐
│   Docker Container          │
│                             │
│   App                       │
│   (5003)                    │
│      │                      │
│      └─────────┐            │
└────────────────┼────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ PostgreSQL     │
        │ (LOCAL - 5432) │
        │ bd_app_versus  │
        └────────────────┘
```

**Quando usar:**
- ✅ Desenvolvimento solo
- ✅ Já tem banco local populado
- ✅ Performance máxima

**Status:** JÁ ESTÁ ATIVO

**Para copiar dados pro container também:**
```bash
python setup_database_strategy.py
# Escolha opção 2
```

---

### Opção 3: Sem Docker (Tradicional)

```
Tudo na máquina local:

App (5002) ──▶ PostgreSQL (5432)
```

**Quando usar:**
- ✅ Prototipagem rápida
- ✅ Aprendizado
- ✅ Problemas com Docker

**Como ativar:**
```bash
docker-compose -f docker-compose.dev.yml down
python app_pev.py
```

---

## 🛠️ Dia a Dia de Desenvolvimento

### Com Docker Completo (Opção 1)

```bash
# Manhã
cd C:\GestaoVersus\app31
docker-compose -f docker-compose.dev.yml up -d

# Desenvolver
# Código atualiza automaticamente (hot-reload)
# App: http://localhost:5003
# Adminer: http://localhost:8080

# Fim do dia
docker-compose -f docker-compose.dev.yml down
# Dados persistem! ✅
```

### Com Híbrido (Opção 2 - ATUAL)

```bash
# Manhã
docker-compose -f docker-compose.dev.yml up -d
# PostgreSQL local já está rodando

# Desenvolver
# App: http://localhost:5003
# Banco: localhost:5432 (DBeaver, pgAdmin)

# Fim do dia  
docker-compose -f docker-compose.dev.yml down
# Banco local continua rodando
```

### Sem Docker (Opção 3)

```bash
# Manhã
python app_pev.py

# Desenvolver
# App: http://localhost:5002

# Fim do dia
# Ctrl+C para parar
```

---

## 🚀 Produção

### Recomendação: Banco Gerenciado na Cloud

```
┌──────────────────────────┐
│   Servidor Produção      │
│                          │
│   Docker Container       │
│   ┌──────────────┐       │
│   │ App Flask    │       │
│   └──────┬───────┘       │
└──────────┼──────────────┘
           │
           ▼
    ┌──────────────┐
    │ Cloud SQL    │  ← Google Cloud
    │ RDS          │  ← AWS
    │ Azure DB     │  ← Azure
    └──────────────┘
```

**Bancos recomendados:**
- 🥇 **Google Cloud SQL** (PostgreSQL gerenciado)
- 🥈 **AWS RDS** (PostgreSQL gerenciado)
- 🥉 **DigitalOcean Managed Database**

**NÃO usar:** PostgreSQL em container sem backup/redundância

---

## ❓ FAQ Rápido

### "Qual estratégia devo usar?"

**Agora (dev solo):** Mantenha Híbrido (já funciona)  
**Futuro (equipe/prod):** Migre para Docker Completo

### "Como migrar dados para o container Docker?"

```bash
# Método 1: Script automático
python setup_database_strategy.py

# Método 2: Manual
pg_dump -h localhost -p 5432 -U postgres bd_app_versus > backup.sql
psql -h localhost -p 5433 -U postgres bd_app_versus_dev < backup.sql
```

### "Como acessar o banco Docker?"

```bash
# Via linha de comando
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev

# Via Adminer (navegador)
http://localhost:8080
# Server: db_dev
# User: postgres
# Pass: dev_password
# Database: bd_app_versus_dev

# Via DBeaver/pgAdmin
# Host: localhost
# Port: 5433
# User: postgres
# Pass: dev_password
# Database: bd_app_versus_dev
```

### "Como voltar atrás se der errado?"

**Docker Completo → Híbrido:**
1. Edite `docker-compose.dev.yml` (reverter linha 72)
2. Restaure backup se necessário
3. `docker-compose down && docker-compose up`

**Sempre faça backup antes de mudanças!**

---

## 📊 Comparação Rápida

| Critério | Docker Completo | Híbrido | Sem Docker |
|----------|----------------|---------|------------|
| Fácil começar | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Trabalho equipe | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| Próximo produção | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Performance | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Replicável | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |

---

## 🎬 Próximos Passos

1. **Ler documentação completa:** `docs/ESTRATEGIA_BANCO_DADOS.md`
2. **Executar script de configuração:** `python setup_database_strategy.py`
3. **Escolher estratégia:** Baseado nas suas necessidades
4. **Testar:** Acessar http://localhost:5003 (Docker) ou :5002 (local)

---

## 🆘 Precisa de Ajuda?

```bash
# Ver status dos bancos
python setup_database_strategy.py
# Escolha opção 4 para documentação

# Verificar containers
docker ps

# Logs do container
docker logs gestaoversos_app_dev

# Conectar no banco
psql -h localhost -p 5433 -U postgres -d bd_app_versus_dev
```

---

**Criado:** 20/10/2025  
**Versão:** 1.0  
**Status:** ✅ Pronto para uso

