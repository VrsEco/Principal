#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migração: Local (ui_pages) -> Cloud (ui_catalog)
Data: 2025-11-23
"""

import sys
import os
import psycopg2
from pathlib import Path

# Configurações Hardcoded para garantir
LOCAL_DB_URL = "postgresql://postgres:*Paraiso1978@127.0.0.1:5432/bd_app_versus"
CLOUD_DB_URL = "postgresql://postgres:*Paraiso1978@127.0.0.1:5433/bd_app_versus"

def decode_code(code_str):
    if not code_str: return None
    try: return int(code_str, 16)
    except: pass
    try: return int(code_str, 36)
    except: pass
    return None

def main():
    print("=" * 70)
    print("MIGRAÇÃO: Local (ui_pages) -> Cloud (ui_catalog)")
    print("=" * 70)

    try:
        # 1. Conectar no Local (Origem)
        print("\n🔌 Conectando no Banco LOCAL (Origem)...")
        conn_local = psycopg2.connect(LOCAL_DB_URL)
        cursor_local = conn_local.cursor()
        
        cursor_local.execute("SELECT page_code, page_name, page_route, description FROM ui_pages")
        local_pages = cursor_local.fetchall()
        print(f"   ✅ Lidos {len(local_pages)} registros de 'ui_pages'.")
        
        # 2. Conectar no Cloud (Destino)
        print("\n☁️  Conectando no Banco CLOUD (Destino)...")
        conn_cloud = psycopg2.connect(CLOUD_DB_URL)
        cursor_cloud = conn_cloud.cursor()
        
        # Verificar se ui_catalog existe (já deve ter sido criado)
        cursor_cloud.execute("SELECT count(*) FROM ui_catalog")
        count_cloud = cursor_cloud.fetchone()[0]
        print(f"   ✅ Tabela 'ui_catalog' encontrada com {count_cloud} registros.")
        
        # 3. Migrar
        print("\n🚀 Iniciando transferência...")
        migrated_count = 0
        skipped_count = 0
        
        # Preparar IDs para colisões (começando de 315, baseado na análise anterior)
        next_collision_id = 315
        
        for row in local_pages:
            page_code_str = row[0]
            name = row[1]
            route = row[2]
            description = row[3] or f"Migrado de Local: {name}"
            
            # Tentar decodificar
            screen_code = decode_code(page_code_str)
            
            # Lógica de colisão (simplificada baseada no script anterior)
            # Se o código decodificado já existe ou é inválido, usamos o ID sequencial
            is_collision = False
            
            # Verificar se esse screen_code já existe no destino (para evitar PK dup)
            if screen_code is not None:
                object_code = 0
                ui_code = f"{screen_code}-{object_code:02d}"
                
                # Check simples na memória seria melhor, mas vamos query por segurança
                cursor_cloud.execute("SELECT 1 FROM ui_catalog WHERE ui_code = %s", (ui_code,))
                if cursor_cloud.fetchone():
                    is_collision = True
            else:
                is_collision = True
                
            if is_collision:
                screen_code = next_collision_id
                next_collision_id += 1
                
            # Montar dados finais
            object_code = 0
            ui_code = f"{screen_code}-{object_code:02d}"
            
            # Inserir no Cloud
            try:
                cursor_cloud.execute("""
                    INSERT INTO ui_catalog 
                    (screen_code, object_code, ui_code, name, description, object_type, route, is_active)
                    VALUES (%s, %s, %s, %s, %s, 'page', %s, TRUE)
                    ON CONFLICT (ui_code) DO NOTHING
                """, (screen_code, object_code, ui_code, name, description, route))
                
                if cursor_cloud.rowcount > 0:
                    migrated_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"   ❌ Erro ao inserir {name}: {e}")
                conn_cloud.rollback()
                continue
                
        conn_cloud.commit()
        
        print(f"\n📊 Resumo:")
        print(f"   - Total Origem: {len(local_pages)}")
        print(f"   - Migrados/Inseridos: {migrated_count}")
        print(f"   - Pulados (Já existiam): {skipped_count}")
        
        conn_local.close()
        conn_cloud.close()

    except Exception as e:
        print(f"\n❌ Erro Crítico: {e}")
        return False

    print("\n" + "=" * 70)
    print("MIGRAÇÃO LOCAL -> CLOUD CONCLUÍDA")
    print("=" * 70)
    return True

if __name__ == "__main__":
    main()
