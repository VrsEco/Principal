# 🐘 Guia de Migração para PostgreSQL

## 📋 Visão Geral

Este guia explica como migrar o APP29 do SQLite para PostgreSQL com o nome de banco `bd_app_versus`.

## ✅ Pré-requisitos

1. **PostgreSQL instalado** (versão 12 ou superior)
2. **Python 3.8+** com dependências instaladas
3. **Acesso administrativo** ao PostgreSQL
4. **Backup do banco SQLite** (recomendado)

## 🚀 Método 1: Script Automático (Recomendado)

### Windows
```bash
setup_postgresql_environment.bat
```

### Linux/macOS
```bash
chmod +x setup_postgresql_environment.sh
./setup_postgresql_environment.sh
```

## 🔧 Método 2: Manual

### 1. Instalar PostgreSQL

#### Windows
- Download: https://www.postgresql.org/download/windows/
- Instalar com usuário padrão `postgres`

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### CentOS/RHEL
```bash
sudo yum install postgresql postgresql-server
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### macOS
```bash
brew install postgresql
brew services start postgresql
```

### 2. Configurar Variáveis de Ambiente

```bash
# Windows (CMD)
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set POSTGRES_DB=bd_app_versus
set POSTGRES_USER=postgres
set POSTGRES_PASSWORD=sua_senha_aqui

# Linux/macOS
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=bd_app_versus
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=sua_senha_aqui
```

### 3. Criar Banco de Dados

```bash
psql -h localhost -U postgres -c "CREATE DATABASE bd_app_versus;"
```

### 4. Executar Migração

```bash
python migrate_to_postgresql.py
```

### 5. Verificar Migração

```bash
python verify_postgresql_migration.py
```

### 6. Configurar Aplicação

Criar arquivo `.env`:

```env
# Trocar para PostgreSQL
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bd_app_versus
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha_aqui

# SQLAlchemy URLs
DATABASE_URL=postgresql://postgres:sua_senha_aqui@localhost:5432/bd_app_versus
DEV_DATABASE_URL=postgresql://postgres:sua_senha_aqui@localhost:5432/bd_app_versus
```

## 🔄 Voltar para SQLite

Se precisar voltar para SQLite temporariamente:

```env
DB_TYPE=sqlite
SQLITE_DB_PATH=instance/pevapp22.db
DATABASE_URL=sqlite:///instance/pevapp22.db
```

## 📊 Estrutura de Tabelas Migradas

O script migra as seguintes tabelas:

| Tabela | Descrição |
|--------|-----------|
| `users` | Usuários do sistema |
| `companies` | Empresas cadastradas |
| `plans` | Planejamentos estratégicos |
| `participants` | Participantes dos planos |
| `company_data` | Dados específicos das empresas |
| `driver_topics` | Tópicos direcionadores |
| `okr_global` | OKRs globais |
| `key_results` | Resultados-chave |
| `okr_area` | OKRs por área |
| `key_results_area` | Resultados-chave por área |
| `projects` | Projetos |
| `project_tasks` | Tarefas dos projetos |
| `ai_agents` | Agentes de IA |
| `user_logs` | Logs de usuário |

## 🔍 Verificações Automáticas

O script de verificação checa:

- ✅ **Conectividade** com PostgreSQL
- ✅ **Estrutura** das tabelas
- ✅ **Contagem** de registros
- ✅ **Dados críticos** (usuários, empresas)
- ✅ **Integridade** dos dados

## 🐛 Solução de Problemas

### Erro: "FATAL: password authentication failed"
```bash
# Verificar senha do PostgreSQL
sudo -u postgres psql
\password postgres
```

### Erro: "database does not exist"
```bash
# Criar banco manualmente
psql -h localhost -U postgres -c "CREATE DATABASE bd_app_versus;"
```

### Erro: "connection refused"
```bash
# Verificar se PostgreSQL está rodando
# Windows: Services.msc → PostgreSQL
# Linux: sudo systemctl status postgresql
# macOS: brew services list | grep postgresql
```

### Erro: "permission denied"
```bash
# Dar permissões ao usuário
psql -h localhost -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE bd_app_versus TO postgres;"
```

## 📈 Performance

### Vantagens do PostgreSQL:
- ✅ **Melhor performance** para grandes volumes
- ✅ **Concorrência** superior
- ✅ **Recursos avançados** (JSON, arrays, etc.)
- ✅ **Backup/restore** robusto
- ✅ **Escalabilidade** horizontal

### Comparação de Performance:
- **SQLite**: Ideal para desenvolvimento e pequenas aplicações
- **PostgreSQL**: Ideal para produção e aplicações médias/grandes

## 🔐 Segurança

### Configurações Recomendadas:

1. **Usuário dedicado** (não usar `postgres`)
2. **Senha forte** para o banco
3. **SSL habilitado** em produção
4. **Firewall** configurado
5. **Backups automáticos**

### Exemplo de usuário dedicado:
```sql
CREATE USER app29_user WITH PASSWORD 'senha_forte_aqui';
GRANT ALL PRIVILEGES ON DATABASE bd_app_versus TO app29_user;
```

## 📞 Suporte

Se encontrar problemas:

1. **Verificar logs** do PostgreSQL
2. **Executar** `verify_postgresql_migration.py`
3. **Consultar** documentação do PostgreSQL
4. **Verificar** variáveis de ambiente

## 🎯 Próximos Passos

Após a migração bem-sucedida:

1. ✅ **Testar** todas as funcionalidades
2. ✅ **Configurar** backup automático
3. ✅ **Monitorar** performance
4. ✅ **Documentar** mudanças
5. ✅ **Treinar** equipe

---

**Status**: ✅ Pronto para produção  
**Versão**: 1.0  
**Data**: $(date)  
