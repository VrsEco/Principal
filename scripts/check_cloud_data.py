#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de consulta: Verificar dados no Cloud DB (ui_catalog)
Data: 2025-11-23
"""

import psycopg2

# Conexão com Cloud SQL via Proxy (Porta 5433)
CLOUD_DB_URL = "postgresql://postgres:*Paraiso1978@127.0.0.1:5433/bd_app_versus"

def main():
    print("=" * 70)
    print("CONSULTA CLOUD DB: Verificando Rotas")
    print("=" * 70)

    try:
        conn = psycopg2.connect(CLOUD_DB_URL)
        cursor = conn.cursor()
        
        # 1. Rotas de instâncias de processo
        print("\n🔍 1. Buscando rotas '%process/instances%'...")
        sql1 = """
            SELECT ui_code, name, route 
            FROM ui_catalog 
            WHERE route LIKE '%process/instances%'
        """
        cursor.execute(sql1)
        rows1 = cursor.fetchall()
        
        if rows1:
            for r in rows1:
                print(f"   - [{r[0]}] {r[1]} ({r[2]})")
        else:
            print("   (Nenhum registro encontrado)")

        # 2. Páginas sem rota
        print("\n🔍 2. Buscando páginas sem rota...")
        sql2 = """
            SELECT ui_code, name 
            FROM ui_catalog 
            WHERE route IS NULL OR route = ''
        """
        cursor.execute(sql2)
        rows2 = cursor.fetchall()
        
        if rows2:
            for r in rows2:
                print(f"   - [{r[0]}] {r[1]}")
        else:
            print("   (Nenhum registro encontrado)")

        conn.close()

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
