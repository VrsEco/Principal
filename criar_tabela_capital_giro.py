#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Criar tabela plan_finance_capital_giro"""

from database.postgres_helper import get_engine
from sqlalchemy import text

engine = get_engine()

with engine.connect() as conn:
    # Criar tabela
    print("[1/3] Criando tabela plan_finance_capital_giro...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS plan_finance_capital_giro (
            id SERIAL PRIMARY KEY,
            plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
            item_type VARCHAR(50) NOT NULL,
            contribution_date DATE NOT NULL,
            amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            description TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted BOOLEAN DEFAULT FALSE
        )
    """))
    conn.commit()
    print("   ✅ Tabela criada!")
    
    # Criar índice
    print("[2/3] Criando índices...")
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_capital_giro_plan_id 
        ON plan_finance_capital_giro(plan_id)
    """))
    conn.commit()
    print("   ✅ Índices criados!")
    
    # Adicionar coluna executive_summary
    print("[3/3] Adicionando coluna executive_summary...")
    try:
        conn.execute(text("""
            ALTER TABLE plan_finance_metrics 
            ADD COLUMN IF NOT EXISTS executive_summary TEXT
        """))
        conn.commit()
        print("   ✅ Coluna adicionada!")
    except Exception as e:
        if 'already exists' in str(e) or 'já existe' in str(e):
            print("   ⚠️  Coluna já existe (OK)")
        else:
            print(f"   ❌ Erro: {e}")

print("\n" + "="*50)
print("✅ MIGRATION APLICADA COM SUCESSO!")
print("="*50)
print("\nAgora teste salvar no modal novamente!")

