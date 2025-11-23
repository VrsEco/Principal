#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migração: Importar dados de ui_pages para ui_catalog
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
    """
    Tenta converter código para int.
    Suporta Hex (0-9, A-F) e Base36 (0-9, A-Z) se necessário.
    """
    if not code_str:
        return None
        
    # Tenta Hex padrão primeiro
    try:
        return int(code_str, 16)
    except ValueError:
        pass
        
    # Tenta Base36 (0-9, A-Z)
    # Isso cobre casos como 1I, 1Z, etc.
    try:
        return int(code_str, 36)
    except ValueError:
        pass
        
    # Se falhar, retorna None
    return None

def main():
    print("=" * 70)
    print("MIGRAÇÃO: ui_pages -> ui_catalog (V2 - Base36 Support)")
    print("=" * 70)

    # Configurar app Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    
    try:
        db = get_db()
        
        # Tentar obter conexão direta
        if hasattr(db, "_get_connection"):
             conn = db._get_connection()
        elif hasattr(db, "engine"):
             conn = db.engine.raw_connection()
        else:
             conn = db

        cursor = conn.cursor()
        
        # 1. Ler dados antigos
        print("\n📥 Lendo dados de 'ui_pages'...")
        cursor.execute("SELECT page_code, page_name, page_route, description FROM ui_pages")
        old_pages = cursor.fetchall()
        print(f"   Encontrados {len(old_pages)} registros.")

        migrated_count = 0
        skipped_count = 0
        
        print("\n🚀 Iniciando migração...")
        
        for row in old_pages:
            page_code_str = row[0]
            name = row[1]
            route = row[2]
            description = row[3] or f"Importado de ui_pages: {name}"
            
            # Converter código
            screen_code = decode_code(page_code_str)
            
            if screen_code is None:
                # Fallback final: Hash simples para garantir unicidade numérica
                # Mas cuidado com colisões. Para 2 chars, melhor usar ord()
                try:
                    # Ex: 'XY' -> ord(X)*100 + ord(Y)
                    if len(page_code_str) == 2:
                        screen_code = ord(page_code_str[0]) * 100 + ord(page_code_str[1])
                    else:
                        print(f"   ⚠️  Pular: Código irrecuperável '{page_code_str}'")
                        skipped_count += 1
                        continue
                except:
                    skipped_count += 1
                    continue
            
            # Gerar ui_code no formato novo (ex: 10-00 para a página em si)
            object_code = 0
            ui_code = f"{screen_code}-{object_code:02d}"
            
            # Verificar se já existe
            cursor.execute("SELECT id FROM ui_catalog WHERE ui_code = %s", (ui_code,))
            if cursor.fetchone():
                # print(f"   ℹ️  Já existe: {ui_code} ({name})")
                skipped_count += 1
                continue
            
            try:
                cursor.execute("""
                    INSERT INTO ui_catalog 
                    (screen_code, object_code, ui_code, name, description, object_type, route, is_active)
                    VALUES (%s, %s, %s, %s, %s, 'page', %s, TRUE)
                """, (screen_code, object_code, ui_code, name, description, route))
                migrated_count += 1
                # print(f"   ✅ Migrado: {ui_code} ({page_code_str}) -> {name}")
            except Exception as e:
                print(f"   ❌ Erro ao migrar {name}: {e}")
                conn.rollback() 
                
        conn.commit()
        
        print(f"\n📊 Resumo:")
        print(f"   - Total lido: {len(old_pages)}")
        print(f"   - Migrados: {migrated_count}")
        print(f"   - Pulados/Existentes: {skipped_count}")

        conn.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("MIGRAÇÃO CONCLUÍDA")
    print("=" * 70)
    return True

if __name__ == "__main__":
    main()
