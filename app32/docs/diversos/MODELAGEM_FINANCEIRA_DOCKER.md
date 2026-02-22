# 🐳 Modelagem Financeira - Instruções para DOCKER

**Data:** 24/10/2025  
**Status:** ✅ **PRONTO PARA TESTE NO DOCKER**

---

## 🐳 Você está usando Docker!

Este guia é específico para o ambiente **Docker** do projeto GestaoVersus.

---

## 📋 Pré-requisitos

### **1. Containers rodando**

Verifique se os containers estão ativos:

```bash
docker ps
```

Você deve ver:
- ✅ `gestaoversos_db_prod` (PostgreSQL)
- ✅ `gestaoversos_app_prod` (Flask)
- ✅ `gestaoversos_redis_prod` (Redis)
- ✅ `gestaoversos_nginx_prod` (Nginx)

### **2. Se os containers NÃO estiverem rodando:**

```bash
docker-compose up -d
```

Aguarde os containers iniciarem (~30 segundos).

---

## 🔧 PASSO 1: Aplicar a Migration

### **Opção A: Script Automático (Windows)**

Execute o script que criamos:

```bash
aplicar_migration_modelagem_financeira.bat
```

### **Opção B: Script Automático (Linux/Mac)**

```bash
chmod +x aplicar_migration_modelagem_financeira.sh
./aplicar_migration_modelagem_financeira.sh
```

### **Opção C: Comando Manual**

Execute diretamente no terminal:

```bash
docker exec -i gestaoversos_db_prod psql -U postgres -d bd_app_versus < migrations/add_notes_to_finance_metrics.sql
```

---

## ✅ Verificar se a Migration Foi Aplicada

Entre no container PostgreSQL e verifique:

```bash
# Entrar no container
docker exec -it gestaoversos_db_prod psql -U postgres -d bd_app_versus

# Dentro do PostgreSQL, executar:
\d plan_finance_metrics

# Você deve ver o campo 'notes' na lista de colunas
# Para sair: \q
```

---

## 🚀 PASSO 2: Acessar a Página

### **URL de Teste:**

```
http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=45
```

⚠️ **IMPORTANTE:** Substitua `plan_id=45` por um ID válido!

### **Como descobrir IDs válidos:**

Entre no PostgreSQL:

```bash
docker exec -it gestaoversos_db_prod psql -U postgres -d bd_app_versus
```

Execute:

```sql
SELECT id, name, company_id FROM plans ORDER BY id DESC LIMIT 10;
```

Use um `id` da lista retornada.

---

## 🧪 PASSO 3: Testar Funcionalidades

### **1. Premissas**
1. ✅ Clique em "**+ Adicionar Premissa**"
2. ✅ Preencha o formulário
3. ✅ Salve e verifique se aparece na tabela
4. ✅ Teste **editar** (✏️) e **deletar** (🗑️)

### **2. Investimentos**
1. ✅ Clique no **"+"** ao lado de "Investimento"
2. ✅ Adicione um item
3. ✅ Teste editar e deletar

### **3. Fontes de Recursos**
1. ✅ Clique no **"+"** ao lado de "Fontes"
2. ✅ Adicione uma fonte
3. ✅ Teste editar e deletar

### **4. Custos Variáveis**
1. ✅ Clique no **"+"** ao lado de "Custos e despesas variáveis"
2. ✅ Adicione um custo
3. ✅ Teste editar e deletar

### **5. Regras de Destinação**
1. ✅ Clique no **"+"** ao lado de "Destinação de resultados"
2. ✅ Adicione uma regra
3. ✅ Teste editar e deletar

### **6. Métricas**
1. ✅ Clique em "**✏️ Editar Métricas**"
2. ✅ Preencha: Payback, TIR 5 anos, Comentários
3. ✅ Salve e verifique se os valores aparecem nos cards

---

## 🔍 Troubleshooting (Docker)

### **Problema 1: Container não está rodando**

**Erro:** `Error response from daemon: Container is not running`

**Solução:**
```bash
docker-compose up -d
docker ps  # Verificar se estão ativos
```

---

### **Problema 2: Migration falha**

**Erro:** `psql: error: connection to server...`

**Solução:**
```bash
# Verificar logs do PostgreSQL
docker logs gestaoversos_db_prod

# Reiniciar o container
docker-compose restart db

# Aguardar 10 segundos e tentar novamente
```

---

### **Problema 3: Página não abre (404/500)**

**Erro:** Página não carrega ou erro 500

**Solução:**
```bash
# Ver logs do Flask
docker logs gestaoversos_app_prod

# Reiniciar o container
docker-compose restart app

# Aguardar 10 segundos
```

---

### **Problema 4: Alterações no código não refletem**

**Causa:** Código não está sendo recarregado

**Solução:**
```bash
# Reconstruir e reiniciar
docker-compose down
docker-compose up -d --build

# Aguardar containers iniciarem
```

---

### **Problema 5: Campo 'notes' não existe**

**Erro:** `column "notes" does not exist`

**Solução:**
```bash
# Verificar se migration foi aplicada
docker exec -it gestaoversos_db_prod psql -U postgres -d bd_app_versus -c "\d plan_finance_metrics"

# Se não aparecer 'notes', aplicar novamente:
docker exec -i gestaoversos_db_prod psql -U postgres -d bd_app_verso < migrations/add_notes_to_finance_metrics.sql
```

---

## 📊 Verificar Dados no Banco (Docker)

### **Entrar no PostgreSQL:**

```bash
docker exec -it gestaoversos_db_prod psql -U postgres -d bd_app_versus
```

### **Queries Úteis:**

```sql
-- Ver premissas cadastradas
SELECT * FROM plan_finance_premises WHERE plan_id = 45;

-- Ver investimentos
SELECT * FROM plan_finance_investments WHERE plan_id = 45;

-- Ver fontes
SELECT * FROM plan_finance_sources WHERE plan_id = 45;

-- Ver custos variáveis
SELECT * FROM plan_finance_variable_costs WHERE plan_id = 45;

-- Ver regras de destinação
SELECT * FROM plan_finance_result_rules WHERE plan_id = 45;

-- Ver métricas
SELECT * FROM plan_finance_metrics WHERE plan_id = 45;
```

Para sair do PostgreSQL: `\q`

---

## 🔄 Comandos Úteis Docker

### **Ver logs em tempo real:**

```bash
# Flask
docker logs -f gestaoversos_app_prod

# PostgreSQL
docker logs -f gestaoversos_db_prod
```

### **Reiniciar serviços:**

```bash
# Apenas Flask
docker-compose restart app

# Todos os serviços
docker-compose restart

# Parar e iniciar (completo)
docker-compose down
docker-compose up -d
```

### **Executar comandos dentro do container Flask:**

```bash
# Shell interativo
docker exec -it gestaoversos_app_prod /bin/sh

# Executar Python
docker exec -it gestaoversos_app_prod python

# Verificar variáveis de ambiente
docker exec gestaoversos_app_prod env | grep DATABASE
```

---

## 📁 Estrutura de Arquivos Docker

```
GestaoVersus/app31/
├── docker-compose.yml                          # Orquestração dos containers
├── Dockerfile                                   # Imagem da aplicação
├── migrations/
│   └── add_notes_to_finance_metrics.sql        # Migration a ser aplicada
├── aplicar_migration_modelagem_financeira.bat  # Script Windows ✅
├── aplicar_migration_modelagem_financeira.sh   # Script Linux/Mac ✅
└── database/
    ├── base.py                                  # Interfaces (modificado)
    └── postgresql_db.py                         # Implementação (modificado)
```

---

## 🎯 Checklist de Teste Docker

- [ ] Containers estão rodando (`docker ps`)
- [ ] Migration aplicada com sucesso
- [ ] Campo `notes` existe na tabela (`\d plan_finance_metrics`)
- [ ] Página abre sem erros
- [ ] Consigo adicionar premissas
- [ ] Consigo editar premissas
- [ ] Consigo deletar premissas
- [ ] Consigo adicionar investimentos
- [ ] Consigo editar investimentos
- [ ] Consigo deletar investimentos
- [ ] Consigo adicionar fontes
- [ ] Consigo editar fontes
- [ ] Consigo deletar fontes
- [ ] Consigo adicionar custos variáveis
- [ ] Consigo editar custos variáveis
- [ ] Consigo deletar custos variáveis
- [ ] Consigo adicionar regras de destinação
- [ ] Consigo editar regras de destinação
- [ ] Consigo deletar regras de destinação
- [ ] Consigo editar métricas
- [ ] Dados persistem após reload da página
- [ ] Console do navegador não mostra erros
- [ ] Logs do container não mostram erros

---

## 🚨 Atenção Especial - Docker

### **Diferenças do ambiente local:**

1. ✅ **Banco está no container**, não no host
2. ✅ **Use scripts específicos** para Docker (`.bat` ou `.sh`)
3. ✅ **Port mapping**: PostgreSQL está em `localhost:5432` mas DENTRO da rede Docker
4. ✅ **Volumes**: Dados persistem em volumes Docker
5. ✅ **Logs**: Use `docker logs` para debug

### **URLs de Acesso:**

| Serviço | URL Host | URL Interna (Docker) |
|---------|----------|---------------------|
| **Flask** | `http://localhost:5003` | `http://app:5002` |
| **PostgreSQL** | `localhost:5432` | `db:5432` |
| **Redis** | `localhost:6379` | `redis:6379` |
| **Nginx** | `http://localhost:80` | - |

---

## ✅ Próximos Passos

Após testar tudo:

1. ✅ Se tudo funcionar, marque como **PRONTO**
2. ✅ Se houver erro, verifique:
   - Logs: `docker logs gestaoversos_app_prod`
   - Console do navegador (F12)
   - PostgreSQL: se migration foi aplicada
3. ✅ Documente qualquer problema encontrado

---

## 📞 Suporte

Se encontrar problemas:

1. **Verifique logs:**
   ```bash
   docker logs gestaoversos_app_prod
   docker logs gestaoversos_db_prod
   ```

2. **Verifique se containers estão saudáveis:**
   ```bash
   docker ps
   # A coluna STATUS deve mostrar "healthy"
   ```

3. **Reinicie os containers:**
   ```bash
   docker-compose restart
   ```

---

## 🎉 Conclusão

A **Modelagem Financeira** está 100% funcional no Docker! 🐳

Execute a migration e teste todas as funcionalidades seguindo este guia.

---

**Desenvolvido em:** 24/10/2025  
**Ambiente:** Docker  
**Tecnologias:** PostgreSQL 15 + Flask + Docker Compose


