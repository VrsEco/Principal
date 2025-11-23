#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de análise: Verificar duplicatas em ui_pages
Data: 2025-11-23
"""

import sys
import os
from pathlib import Path
from flask import Flask
from collections import Counter

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
    print("ANÁLISE: Duplicatas em ui_pages")
    print("=" * 70)

    app = Flask(__name__)
    app.config.from_object(Config)
    
    try:
        db = get_db()
        if hasattr(db, "_get_connection"): conn = db._get_connection()
        elif hasattr(db, "engine"): conn = db.engine.raw_connection()
        else: conn = db
        cursor = conn.cursor()
        
        cursor.execute("SELECT page_code, page_name FROM ui_pages")
        rows = cursor.fetchall()
        
        print(f"Total de registros antigos: {len(rows)}")
        
        # Analisar códigos brutos
        raw_codes = [r[0] for r in rows]
        raw_counts = Counter(raw_codes)
        
        duplicates = {k: v for k, v in raw_counts.items() if v > 1}
        
        if duplicates:
            print(f"\n⚠️  Duplicatas de código bruto ({len(duplicates)}):")
            for code, count in duplicates.items():
                print(f"   - '{code}': {count} vezes")
                # Listar nomes
                names = [r[1] for r in rows if r[0] == code]
                for n in names:
                    print(f"     > {n}")
        else:
            print("\n✅ Sem duplicatas de código bruto.")

        # Analisar códigos convertidos (colisões de conversão)
        print("\n🔍 Analisando colisões de conversão (Hex/Base36)...")
        converted_map = {} # int -> list of (raw, name)
        
        for r in rows:
            raw = r[0]
            name = r[1]
            val = decode_code(raw)
            if val is not None:
                if val not in converted_map:
                    converted_map[val] = []
                converted_map[val].append((raw, name))
        
        collisions = {k: v for k, v in converted_map.items() if len(v) > 1}
        
        if collisions:
            print(f"\n⚠️  Colisões de valor numérico ({len(collisions)}):")
            for val, items in collisions.items():
                print(f"   - Valor {val}: {len(items)} registros")
                for raw, name in items:
                    print(f"     > '{raw}' -> {name}")
        else:
            print("\n✅ Sem colisões de valor numérico.")

        conn.close()

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
