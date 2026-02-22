#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inspeção: Grv Process Map (0U)
Data: 2025-11-23
"""

import sys
import os
from pathlib import Path
from flask import Flask

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from config_database import get_db

def main():
    print("=" * 70)
    print("INSPEÇÃO: Grv Process Map")
    print("=" * 70)

    app = Flask(__name__)
    app.config.from_object(Config)
    
    try:
        db = get_db()
        if hasattr(db, "_get_connection"): conn = db._get_connection()
        elif hasattr(db, "engine"): conn = db.engine.raw_connection()
        else: conn = db
        cursor = conn.cursor()
        
        # Buscar por nome ou rota
        print("\n🔍 Buscando por nome 'Grv Process Map'...")
        cursor.execute("""
            SELECT id, screen_code, ui_code, name, route, is_active 
            FROM ui_catalog 
            WHERE name ILIKE '%Grv Process Map%'
        """)
        rows = cursor.fetchall()
        
        for r in rows:
            print(f"   ID: {r[0]}")
            print(f"   Screen Code: {r[1]}")
            print(f"   UI Code: {r[2]}")
            print(f"   Name: {r[3]}")
            print(f"   Route: {r[4]}")
            print(f"   Active: {r[5]}")
            print("-" * 30)
            
        if not rows:
            print("   ❌ Nenhum registro encontrado.")

        conn.close()

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
