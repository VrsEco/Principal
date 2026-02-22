#!/bin/bash

echo "========================================"
echo "    CONFIGURACAO POSTGRESQL - APP29"
echo "    Banco: bd_app_versus"
echo "========================================"
echo

echo "1. Verificando PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL não encontrado!"
    echo "   Instale o PostgreSQL primeiro"
    echo "   Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "   CentOS/RHEL: sudo yum install postgresql postgresql-server"
    echo "   macOS: brew install postgresql"
    exit 1
fi

echo "✅ PostgreSQL encontrado"
echo

echo "2. Configurando variáveis de ambiente..."
echo "   POSTGRES_HOST=localhost"
echo "   POSTGRES_PORT=5432"
echo "   POSTGRES_DB=bd_app_versus"
echo "   POSTGRES_USER=postgres"
echo

export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=bd_app_versus
export POSTGRES_USER=postgres

echo -n "Digite a senha do PostgreSQL: "
read -s POSTGRES_PASSWORD
echo

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ Senha não pode estar vazia!"
    exit 1
fi

export POSTGRES_PASSWORD

echo
echo "3. Testando conexão com PostgreSQL..."
if ! psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d postgres -c "SELECT version();" &> /dev/null; then
    echo "❌ Erro ao conectar PostgreSQL!"
    echo "   Verifique:"
    echo "   - Se o PostgreSQL está rodando"
    echo "   - Se a senha está correta"
    echo "   - Se o usuário 'postgres' existe"
    exit 1
fi

echo "✅ Conexão com PostgreSQL OK"
echo

echo "4. Criando banco de dados 'bd_app_versus'..."
if psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d postgres -c "CREATE DATABASE bd_app_versus;" &> /dev/null; then
    echo "✅ Banco 'bd_app_versus' criado com sucesso"
else
    echo "⚠️  Banco 'bd_app_versus' já existe ou erro ao criar"
fi

echo
echo "5. Executando migração de dados..."
if ! python3 migrate_to_postgresql.py; then
    echo "❌ Erro na migração!"
    exit 1
fi

echo
echo "6. Verificando migração..."
if ! python3 verify_postgresql_migration.py; then
    echo "❌ Erro na verificação!"
    exit 1
fi

echo
echo "========================================"
echo "    MIGRAÇÃO CONCLUÍDA COM SUCESSO!"
echo "========================================"
echo
echo "Para usar PostgreSQL, configure o arquivo .env:"
echo
echo "DB_TYPE=postgresql"
echo "POSTGRES_HOST=localhost"
echo "POSTGRES_PORT=5432"
echo "POSTGRES_DB=bd_app_versus"
echo "POSTGRES_USER=postgres"
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo
echo "DATABASE_URL=postgresql://postgres:$POSTGRES_PASSWORD@localhost:5432/bd_app_versus"
echo
