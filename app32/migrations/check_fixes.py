#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificação pós-fix.
"""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgres_helper import connect as pg_connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check():
    conn = None
    try:
        conn = pg_connect()
        cursor = conn.cursor()
        
        # 1. Routines.is_active
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='routines' AND column_name='is_active';")
        row = cursor.fetchone()
        if row and row[1] == 'boolean':
            print("✅ routines.is_active agora é de tipo BOOLEAN.")
        else:
            print(f"❌ routines.is_active ainda é {row[1] if row else 'DESCONHECIDO'}. FIX NEEDED!")

        # 2. Agent_actions.original_file
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='agent_actions' AND column_name='original_file';")
        if cursor.fetchone():
            print("✅ agent_actions.original_file existe.")
        else:
            print("❌ agent_actions.original_file NÃO existe. FIX NEEDED!")

    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check()
