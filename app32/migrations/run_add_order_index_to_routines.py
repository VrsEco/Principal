#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adicionar a coluna order_index na tabela routines.

Erro original:
psycopg2.errors.UndefinedColumn: column "order_index" of relation "routines" does not exist

Este script adiciona a coluna faltante para corrigir o erro de INSERT.
"""

import sys
import os
import logging

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.postgres_helper import connect as pg_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_order_index_column():
    """Adiciona coluna order_index na tabela routines"""
    conn = None
    try:
        conn = pg_connect()
        cursor = conn.cursor()
        
        logger.info("🔧 Iniciando migração para adicionar order_index em routines...")
        
        # Verificar se a coluna já existe
        logger.info("📝 Verificando estrutura atual...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='routines' AND column_name='order_index';
        """)
        
        if cursor.fetchone():
            logger.info("⚠️ Coluna order_index já existe na tabela routines. Nada a fazer.")
            return True

        # Adicionar a coluna
        logger.info("📝 Adicionando coluna order_index (INTEGER DEFAULT 0)...")
        cursor.execute("""
            ALTER TABLE routines 
            ADD COLUMN order_index INTEGER DEFAULT 0;
        """)
        
        # Update existing rows to have 0 if needed (DEFAULT handles new ones, but good to be safe)
        # Actually DEFAULT 0 in ADD COLUMN will popuplate existing rows with 0 in Postgres.
        
        # Commit
        conn.commit()
        logger.info("✅ Coluna adicionada com sucesso!")
        
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Erro ao aplicar migração: {e}")
        raise
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        add_order_index_column()
        print("\n✅ Migration aplicada com sucesso!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro ao aplicar migration: {e}")
        sys.exit(1)
