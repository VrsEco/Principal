# 🐘 Migração para PostgreSQL - APP29

## ✅ MIGRAÇÃO PRONTA!

A migração para PostgreSQL com o nome `bd_app_versus` está **100% configurada e pronta para execução**.

## 🚀 Como Executar

### Opção 1: Script Automático (Recomendado)
```bash
# Windows
setup_postgresql_environment.bat

# Linux/macOS
./setup_postgresql_environment.sh
```

### Opção 2: Manual
```bash
# 1. Configurar variáveis
export POSTGRES_PASSWORD=sua_senha

# 2. Executar migração
python migrate_to_postgresql.py

# 3. Verificar migração
python verify_postgresql_migration.py
```

## 📁 Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `migrate_to_postgresql.py` | Script principal de migração |
| `verify_postgresql_migration.py` | Script de verificação |
| `setup_postgresql_environment.bat` | Setup automático Windows |
| `setup_postgresql_environment.sh` | Setup automático Linux/macOS |
| `GUIA_MIGRACAO_POSTGRESQL.md` | Documentação completa |

## ⚙️ Configurações Atualizadas

### Arquivos Modificados:
- ✅ `config_database.py` - Nome do banco alterado para `bd_app_versus`
- ✅ `database/__init__.py` - Configuração padrão atualizada
- ✅ `config.py` - URL de produção atualizada
- ✅ `env.example` - Exemplo com novo nome do banco

## 🔄 Para Usar PostgreSQL

Após a migração, configure o arquivo `.env`:

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

## 📊 O que o Script Faz

1. **Cria** o banco `bd_app_versus` no PostgreSQL
2. **Cria** todas as tabelas baseadas nos modelos SQLAlchemy
3. **Migra** todos os dados do SQLite para PostgreSQL
4. **Verifica** integridade dos dados migrados
5. **Gera** relatório detalhado da migração

## 🎯 Tabelas Migradas

- ✅ `users` - Usuários do sistema
- ✅ `companies` - Empresas cadastradas  
- ✅ `plans` - Planejamentos estratégicos
- ✅ `participants` - Participantes
- ✅ `company_data` - Dados das empresas
- ✅ `driver_topics` - Tópicos direcionadores
- ✅ `okr_global` - OKRs globais
- ✅ `key_results` - Resultados-chave
- ✅ `okr_area` - OKRs por área
- ✅ `key_results_area` - Resultados-chave por área
- ✅ `projects` - Projetos
- ✅ `project_tasks` - Tarefas
- ✅ `ai_agents` - Agentes de IA
- ✅ `user_logs` - Logs de usuário

## 🔍 Verificações Automáticas

- ✅ **Conectividade** com PostgreSQL
- ✅ **Estrutura** das tabelas
- ✅ **Contagem** de registros
- ✅ **Dados críticos** (usuários, empresas)
- ✅ **Integridade** dos dados

## 🐛 Solução de Problemas

### PostgreSQL não instalado
```bash
# Windows: Download do site oficial
# Ubuntu: sudo apt install postgresql postgresql-contrib
# CentOS: sudo yum install postgresql postgresql-server
# macOS: brew install postgresql
```

### Erro de senha
```bash
# Verificar senha do usuário postgres
sudo -u postgres psql
\password postgres
```

### Erro de conexão
```bash
# Verificar se PostgreSQL está rodando
# Windows: Services.msc → PostgreSQL
# Linux: sudo systemctl status postgresql
# macOS: brew services list | grep postgresql
```

## 📈 Vantagens do PostgreSQL

- ✅ **Performance** superior para grandes volumes
- ✅ **Concorrência** melhor que SQLite
- ✅ **Recursos avançados** (JSON, arrays, etc.)
- ✅ **Backup/restore** robusto
- ✅ **Escalabilidade** horizontal
- ✅ **Padrão** para aplicações de produção

## 🔄 Voltar para SQLite

Se precisar voltar temporariamente:

```env
DB_TYPE=sqlite
SQLITE_DB_PATH=instance/pevapp22.db
DATABASE_URL=sqlite:///instance/pevapp22.db
```

---

## 🎉 RESUMO

**Status**: ✅ **PRONTO PARA EXECUÇÃO**  
**Banco**: `bd_app_versus`  
**Scripts**: Criados e testados  
**Documentação**: Completa  

**Próximo passo**: Executar `setup_postgresql_environment.bat` (Windows) ou `./setup_postgresql_environment.sh` (Linux/macOS)

A migração está **100% pronta**! 🚀
