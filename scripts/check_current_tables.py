#!/usr/bin/env python3
"""
Verificar tabelas atuais no banco
"""
import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from config import Config
from sqlalchemy import create_engine, text

config = Config()
engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

print('🔍 VERIFICANDO ESTRUTURA ATUAL DO BANCO...')
print()

with engine.connect() as conn:
    # Tabelas atuais
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    current_tables = [row[0] for row in result.fetchall()]

    print(f'📊 TOTAL DE TABELAS ATUAIS: {len(current_tables)}')
    print()

    # Separar por categoria (tabelas criadas após backup)
    sql_alchemy_tables = []
    other_tables = []

    for table in current_tables:
        if (table.startswith(('plan_', 'okr_', 'company_', 'meeting', 'process', 'routine', 'indicator', 'project_activity')) or
            table in ['notes', 'user_logs']):
            sql_alchemy_tables.append(table)
        else:
            other_tables.append(table)

    print('🆕 TABELAS SQLALCHEMY (CRIADAS APÓS BACKUP):')
    for table in sorted(sql_alchemy_tables):
        print(f'   ✅ {table}')

    print()
    print('📚 TABELAS ORIGINAIS DO BACKUP:')
    for table in sorted(other_tables):
        print(f'   📁 {table}')

    print()
    print('⚠️  ALERTA CRÍTICO:')
    print('   Restaurar o backup irá APAGAR TODAS as tabelas SQLAlchemy!')
    print(f'   Serão perdidas: {len(sql_alchemy_tables)} tabelas criadas recentemente')
    print()
    print('💡 RECOMENDAÇÃO:')
    print('   1. FAÇA UM NOVO BACKUP antes de qualquer restauração')
    print('   2. Considere restaurar apenas dados específicos se possível')
    print('   3. Use uma cópia do banco para testes')










