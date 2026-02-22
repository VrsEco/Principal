#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correção de banco de dados (Emergency Fix).
"""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgres_helper import connect as pg_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database_issues():
    conn = None
    try:
        conn = pg_connect()
        conn.autocommit = False # Usar transações explícitas
        cursor = conn.cursor()
        
        logger.info("🔧 Iniciando correções de banco de dados...")
        
        # 1. Corrigir routines.is_active (Integer -> Boolean)
        # Primeiro, verificar o tipo atual
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name='routines' AND column_name='is_active';
        """)
        row = cursor.fetchone()
        
        if row and row[0].lower() == 'integer':
            logger.info("⚠️ routines.is_active é INTEGER. Convertendo para BOOLEAN...")
            # Precisamos dropar default antigo se existir, ou apenas alterar o tipo com USING
            try:
                # Tenta converter direto. 1 -> true, 0 -> false.
                # Se tiver valores estranhos (null, etc), trataremos.
                cursor.execute("""
                   ALTER TABLE routines 
                   ALTER COLUMN is_active DROP DEFAULT,
                   ALTER COLUMN is_active TYPE request_boolean USING (
                       CASE 
                           WHEN is_active = 1 THEN TRUE 
                           WHEN is_active = 0 THEN FALSE 
                           ELSE NULL 
                       END
                   ),
                   ALTER COLUMN is_active SET DEFAULT TRUE;
                """.replace('request_boolean', 'BOOLEAN'))
                logger.info("✅ routines.is_active convertido com sucesso!")
            except Exception as e:
                logger.error(f"❌ Falha ao converter routines.is_active: {e}")
                conn.rollback() # Rollback parcial se falhar este bloco
                # Re-raise ou continuar? Melhor parar para não deixar estado inconsistente
                raise e
        elif row:
            logger.info(f"ℹ️ routines.is_active já é {row[0]}. Nenhuma ação necessária.")
        else:
            logger.warning("⚠️ routines.is_active não encontrada!")

        # 2. Adicionar agent_actions.original_file (Se não existir)
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='agent_actions' AND column_name='original_file';
        """)
        if not cursor.fetchone():
            logger.info("⚠️ agent_actions.original_file faltando. Adicionando...")
            try:
                cursor.execute("ALTER TABLE agent_actions ADD COLUMN original_file TEXT;")
                logger.info("✅ agent_actions.original_file adicionada com sucesso!")
            except Exception as e:
                logger.error(f"❌ Falha ao adicionar agent_actions.original_file: {e}")
                raise e
        else:
            logger.info("ℹ️ agent_actions.original_file já existe.")

        # Commit final
        conn.commit()
        logger.info("🎉 Todas as correções aplicadas com sucesso!")
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Erro fatal na migração: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = fix_database_issues()
    sys.exit(0 if success else 1)
