#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir constraint UNIQUE em employees

Este script remove a constraint antiga que impedia múltiplos vínculos
e cria a constraint correta que permite um usuário ter múltiplos vínculos
(um por empresa).

Uso:
    python migrations/run_fix_employees_constraint.py
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.postgres_helper import connect as pg_connect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_employees_constraint():
    """Corrige a constraint UNIQUE em employees"""
    conn = None
    try:
        conn = pg_connect()
        cursor = conn.cursor()
        
        logger.info("🔧 Iniciando correção da constraint em employees...")
        
        # 1. Remover constraint antiga (se existir)
        logger.info("📝 Removendo constraint antiga idx_employees_user_unique...")
        try:
            cursor.execute("DROP INDEX IF EXISTS idx_employees_user_unique;")
            logger.info("✅ Constraint antiga removida")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao remover constraint antiga (pode não existir): {e}")
        
        # 2. Criar constraint correta: UNIQUE(user_id, company_id)
        logger.info("📝 Criando constraint correta idx_employees_user_company_unique...")
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_user_company_unique 
            ON employees(user_id, company_id) 
            WHERE user_id IS NOT NULL;
        """)
        logger.info("✅ Constraint correta criada")
        
        # 3. Criar índice simples para performance
        logger.info("📝 Criando índice para performance...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_employees_user_id 
            ON employees(user_id) 
            WHERE user_id IS NOT NULL;
        """)
        logger.info("✅ Índice de performance criado")
        
        # Commit
        conn.commit()
        logger.info("✅ Correção aplicada com sucesso!")
        logger.info("")
        logger.info("📋 Resumo:")
        logger.info("   - Constraint antiga removida: idx_employees_user_unique")
        logger.info("   - Constraint nova criada: idx_employees_user_company_unique")
        logger.info("   - Agora um usuário pode ter múltiplos vínculos (um por empresa)")
        
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Erro ao aplicar correção: {e}")
        raise
        
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    try:
        fix_employees_constraint()
        print("\n✅ Migration aplicada com sucesso!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro ao aplicar migration: {e}")
        sys.exit(1)


