# GUIA DE EXECUCAO - MIGRATIONS PEV NO POWERSHELL

## OPCAO 1: Executar SQL Diretamente (RECOMENDADO)

### Passo 1: Abrir PowerShell como Administrador
```powershell
# Navegue ate a pasta do projeto
cd C:\GestaoVersus\app32
```

### Passo 2: Executar Migration SQL
```powershell
# Conectar ao PostgreSQL e executar o arquivo SQL
psql -h localhost -p 5432 -U postgres -d bd_app_versus -f migrations\pev_complete_migration.sql
```

**Senha:** *Paraiso1978

### Passo 3: Verificar Tabelas Criadas
```powershell
# Conectar ao banco
psql -h localhost -p 5432 -U postgres -d bd_app_versus

# Dentro do psql, executar:
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'plans', 'participants', 'section_status',
    'okrs_global', 'key_results_global', 'okrs_area', 'key_results_area', 'interviews',
    'products', 'segments', 'structures', 'financial_models', 'investments', 'alignment_data'
)
ORDER BY table_name;

# Sair do psql
\q
```

---

## OPCAO 2: Executar Linha por Linha (Se psql nao estiver no PATH)

### Passo 1: Localizar psql.exe
```powershell
# Procurar psql.exe
Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Recurse -Filter psql.exe
```

### Passo 2: Executar com Caminho Completo
```powershell
# Exemplo (ajuste o caminho conforme sua instalacao):
& "C:\Program Files\PostgreSQL\14\bin\psql.exe" -h localhost -p 5432 -U postgres -d bd_app_versus -f migrations\pev_complete_migration.sql
```

---

## OPCAO 3: Copiar e Colar SQL Manualmente

### Passo 1: Conectar ao PostgreSQL
```powershell
psql -h localhost -p 5432 -U postgres -d bd_app_versus
```

### Passo 2: Copiar SQL
Abra o arquivo: `migrations\pev_complete_migration.sql`
Copie TODO o conteudo (Ctrl+A, Ctrl+C)

### Passo 3: Colar no psql
Cole o SQL no terminal do psql e pressione Enter

---

## OPCAO 4: Usar pgAdmin (Interface Grafica)

1. Abra pgAdmin
2. Conecte ao servidor PostgreSQL
3. Selecione o banco `bd_app_versus`
4. Clique em Tools > Query Tool
5. Abra o arquivo `migrations\pev_complete_migration.sql`
6. Clique em Execute (F5)

---

## VERIFICACAO POS-EXECUCAO

### Verificar com Python
```powershell
python check_pev_tables_simple.py
```

### Verificar com SQL
```sql
-- Contar tabelas PEV
SELECT COUNT(*) as tabelas_pev
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'plans', 'participants', 'section_status',
    'okrs_global', 'key_results_global', 'okrs_area', 'key_results_area', 'interviews',
    'products', 'segments', 'structures', 'financial_models', 'investments', 'alignment_data'
);
-- Resultado esperado: 14 tabelas
```

---

## TROUBLESHOOTING

### Erro: "psql nao e reconhecido"
**Solucao:** Adicione PostgreSQL ao PATH ou use caminho completo

```powershell
# Adicionar ao PATH temporariamente
$env:Path += ";C:\Program Files\PostgreSQL\14\bin"

# Agora pode usar psql normalmente
psql -h localhost -p 5432 -U postgres -d bd_app_versus -f migrations\pev_complete_migration.sql
```

### Erro: "FATAL: password authentication failed"
**Solucao:** Verifique a senha no .env

```powershell
# Ver senha configurada
cat .env | Select-String "POSTGRES_PASSWORD"
```

### Erro: "relation already exists"
**Solucao:** Normal! O SQL usa `CREATE TABLE IF NOT EXISTS`, entao tabelas existentes serao ignoradas

### Erro: "foreign key constraint"
**Solucao:** Certifique-se que as tabelas `companies`, `users` e `employees` existem

```sql
-- Verificar tabelas necessarias
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('companies', 'users', 'employees');
```

---

## ROLLBACK (Se necessario)

### Remover todas as tabelas PEV
```sql
-- CUIDADO: Isso apaga TODOS os dados!
DROP TABLE IF EXISTS alignment_data CASCADE;
DROP TABLE IF EXISTS investments CASCADE;
DROP TABLE IF EXISTS financial_models CASCADE;
DROP TABLE IF EXISTS structures CASCADE;
DROP TABLE IF EXISTS segments CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS interviews CASCADE;
DROP TABLE IF EXISTS key_results_area CASCADE;
DROP TABLE IF EXISTS okrs_area CASCADE;
DROP TABLE IF EXISTS key_results_global CASCADE;
DROP TABLE IF EXISTS okrs_global CASCADE;
DROP TABLE IF EXISTS section_status CASCADE;
DROP TABLE IF EXISTS participants CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS migration_history CASCADE;
```

---

## RESUMO DOS COMANDOS (COPY-PASTE)

```powershell
# 1. Navegar ate o projeto
cd C:\GestaoVersus\app32

# 2. Executar migrations
psql -h localhost -p 5432 -U postgres -d bd_app_versus -f migrations\pev_complete_migration.sql

# 3. Verificar
python check_pev_tables_simple.py
```

**Senha quando solicitado:** *Paraiso1978

---

## PROXIMOS PASSOS APOS MIGRATIONS

1. Verificar que todas as 14 tabelas foram criadas
2. Executar `python check_pev_tables_simple.py` para confirmar
3. Comecar implementacao do codigo Python
4. Ou solicitar geracao automatica de codigo com IA

---

**Arquivo SQL:** migrations\pev_complete_migration.sql
**Tamanho:** ~8KB
**Tabelas:** 14 + 1 (migration_history)
**Tempo estimado:** 5-10 segundos

BOA SORTE! 🚀
