#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correção: Resolver colisões de código UI
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
    print("CORREÇÃO: Resolver Colisões")
    print("=" * 70)

    app = Flask(__name__)
    app.config.from_object(Config)
    
    try:
        db = get_db()
        if hasattr(db, "_get_connection"): conn = db._get_connection()
        elif hasattr(db, "engine"): conn = db.engine.raw_connection()
        else: conn = db
        cursor = conn.cursor()
        
        # 1. Identificar páginas que não estão no catálogo (pela rota)
        print("\n🔍 Identificando páginas faltantes via rota...")
        
        cursor.execute("SELECT route FROM ui_catalog")
        existing_routes = {row[0] for row in cursor.fetchall() if row[0]}
        
        cursor.execute("SELECT page_code, page_name, page_route, description FROM ui_pages")
        old_pages = cursor.fetchall()
        
        missing_pages = []
        for row in old_pages:
            if row[2] not in existing_routes:
                missing_pages.append(row)
                
        print(f"   Encontradas {len(missing_pages)} páginas sem rota no catálogo.")
        
        if not missing_pages:
            print("   ✅ Nenhuma página faltando! (As contagens diferentes podem ser páginas sem rota ou inativas)")
            return True

        # 2. Migrar páginas faltantes com novos IDs
        print("\n🚀 Migrando páginas faltantes com novos IDs...")
        migrated_count = 0
        
        # Encontrar o maior screen_code atual para começar a adicionar
        cursor.execute("SELECT MAX(screen_code) FROM ui_catalog")
        max_id = cursor.fetchone()[0] or 1000
        next_id = max_id + 1
        
        for row in missing_pages:
            page_code_str = row[0]
            name = row[1]
            route = row[2]
            description = row[3] or f"Importado (Colisão resolvida): {name}"
            
            # Usar próximo ID disponível
            screen_code = next_id
            next_id += 1
            
            object_code = 0
            ui_code = f"{screen_code}-{object_code:02d}"
            
            try:
                cursor.execute("""
                    INSERT INTO ui_catalog 
                    (screen_code, object_code, ui_code, name, description, object_type, route, is_active)
                    VALUES (%s, %s, %s, %s, %s, 'page', %s, TRUE)
                """, (screen_code, object_code, ui_code, name, description, route))
                migrated_count += 1
                print(f"   ✅ Migrado: {ui_code} ({page_code_str}) -> {name}")
            except Exception as e:
                print(f"   ❌ Erro ao migrar {name}: {e}")
                conn.rollback()
        
        conn.commit()
        print(f"\n✅ Total recuperado: {migrated_count}")
        conn.close()

    except Exception as e:
        print(f"Erro: {e}")
        return False

    return True

if __name__ == "__main__":
    main()
