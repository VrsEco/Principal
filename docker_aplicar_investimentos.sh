#!/bin/bash
# Script para aplicar atualização de investimentos no Docker

echo "============================================"
echo "  APLICAR ATUALIZAÇÃO DE INVESTIMENTOS"
echo "  (Docker/PostgreSQL)"
echo "============================================"
echo ""
echo "Este script irá:"
echo "  1. Criar tabelas de investimento"
echo "  2. Aplicar migration com novos campos"
echo "  3. Popular categorias e itens padrão"
echo ""
echo "Pressione Enter para continuar..."
read

# Verificar se o container está rodando
if ! docker ps | grep -q app31; then
    echo "❌ Container não encontrado ou não está rodando!"
    echo "Execute: docker-compose up -d"
    exit 1
fi

echo ""
echo "[1/4] Criando tabelas de investimento..."
docker exec -i app31 python -c "
from config_database import get_db
db = get_db()
conn = db._get_connection()
cur = conn.cursor()
with open('migrations/create_investment_contributions.sql', 'r', encoding='utf-8') as f:
    cur.execute(f.read())
conn.commit()
print('✅ Tabelas criadas/verificadas!')
conn.close()
"

if [ $? -ne 0 ]; then
    echo "❌ Erro ao criar tabelas!"
    exit 1
fi

echo ""
echo "[2/4] Aplicando migration de novos campos..."
docker exec -i app31 python -c "
from config_database import get_db
db = get_db()
conn = db._get_connection()
cur = conn.cursor()
with open('migrations/20251028_update_investment_contributions.sql', 'r', encoding='utf-8') as f:
    cur.execute(f.read())
conn.commit()
print('✅ Migration aplicada com sucesso!')
conn.close()
"

if [ $? -ne 0 ]; then
    echo "❌ Erro ao aplicar migration!"
    exit 1
fi

echo ""
echo "[3/4] Populando categorias e itens padrão..."
docker exec -i app31 python scripts/seed_investment_items.py

if [ $? -ne 0 ]; then
    echo "❌ Erro ao popular dados!"
    exit 1
fi

echo ""
echo "[4/4] Verificando dados criados..."
docker exec -i app31 python -c "
from config_database import get_db
db = get_db()
conn = db._get_connection()
cur = conn.cursor()

# Verificar categorias
cur.execute('SELECT COUNT(*) FROM plan_finance_investment_categories')
cat_count = cur.fetchone()[0]
print(f'✅ Categorias criadas: {cat_count}')

# Verificar itens
cur.execute('SELECT COUNT(*) FROM plan_finance_investment_items')
item_count = cur.fetchone()[0]
print(f'✅ Itens criados: {item_count}')

conn.close()
"

echo ""
echo "============================================"
echo "  ✅ ATUALIZAÇÃO CONCLUÍDA!"
echo "============================================"
echo ""
echo "Novos campos adicionados:"
echo "  - description (Descrição)"
echo "  - system_suggestion (Sugestão do sistema)"
echo "  - adjusted_value (Valor ajustado)"
echo "  - calculation_memo (Memória de cálculo)"
echo ""
echo "Categorias e itens padrão criados:"
echo "  - Capital de Giro: Caixa, Recebíveis, Estoques"
echo "  - Imobilizado: Instalações, Máquinas, Outros"
echo ""
echo "🔄 Reinicie o container para aplicar as mudanças:"
echo "   docker-compose restart"
echo ""

