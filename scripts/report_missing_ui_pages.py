#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de relatório: Identificar páginas não migradas
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

def decode_code(code_str):
    if not code_str: return None
    try: return int(code_str, 16)
    except: pass
    try: return int(code_str, 36)
    except: pass
    return None

def main():
    print("=" * 70)
    print("RELATÓRIO: Páginas Faltantes")
    print("=" * 70)

    app = Flask(__name__)
    app.config.from_object(Config)
    
    try:
        db = get_db()
        if hasattr(db, "_get_connection"): conn = db._get_connection()
        elif hasattr(db, "engine"): conn = db.engine.raw_connection()
        else: conn = db
        cursor = conn.cursor()
        
        # 1. Carregar todos os ui_codes existentes no catálogo
        cursor.execute("SELECT ui_code, screen_code FROM ui_catalog")
        catalog_entries = cursor.fetchall()
        existing_ui_codes = {row[0] for row in catalog_entries}
        existing_screen_codes = {row[1] for row in catalog_entries}
        
        print(f"Catálogo Novo: {len(existing_ui_codes)} registros")

        # 2. Carregar páginas antigas
        cursor.execute("SELECT page_code, page_name, page_route FROM ui_pages")
        old_pages = cursor.fetchall()
        print(f"Páginas Antigas: {len(old_pages)} registros")
        
        print("\n--- PÁGINAS NÃO MIGRADAS ---")
        missing_count = 0
        
        for row in old_pages:
            page_code_str = row[0]
            name = row[1]
            route = row[2]
            
            screen_code = decode_code(page_code_str)
            
            # Tenta reconstruir o ui_code esperado
            if screen_code is not None:
                expected_ui_code = f"{screen_code}-00"
                
                # Verifica se existe pelo UI Code OU pelo Screen Code
                if expected_ui_code in existing_ui_codes:
                    status = "OK (UI Code)"
                elif screen_code in existing_screen_codes:
                    status = "OK (Screen Code)"
                else:
                    status = "MISSING"
            else:
                status = "INVALID CODE"
                
            if status != "OK (UI Code)" and status != "OK (Screen Code)":
                missing_count += 1
                print(f"❌ [{page_code_str}] {name} -> {status}")
                if screen_code:
                    print(f"   Esperado: {screen_code}-00")

        print(f"\nTotal Faltante: {missing_count}")
        conn.close()

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
