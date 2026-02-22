#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inspeção de clunas problemáticas.
"""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgres_helper import connect as pg_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inspect_tables():
    conn = None
    try:
        conn = pg_connect()
        cursor = conn.cursor()
        
        # 1. Check routines.is_active
        cursor.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name='routines' AND column_name='is_active';
        """)
        row = cursor.fetchone()
        if row:
            logger.info(f"🔍 routines.is_active: {row[0]} (Type: {row[1]}, UDT: {row[2]})")
        else:
            logger.warning("⚠️ routines.is_active NÃO encontrada!")

        # 2. Check agent_actions.original_file
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='agent_actions' AND column_name='original_file';
        """)
        row = cursor.fetchone()
        if row:
            logger.info(f"✅ agent_actions.original_file existe: {row[0]} ({row[1]})")
        else:
            logger.warning("❌ agent_actions.original_file NÃO existe!")
            
    except Exception as e:
        logger.error(f"❌ Erro ao inspecionar: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    inspect_tables()
