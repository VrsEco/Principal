#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de atualização: Formatar ui_code para XXX-XXX (ex: 001-001)
Data: 2025-11-23
"""

import sys
import os
import psycopg2

def update_db(db_url, name):
    print(f"\n🔌 Conectando em: {name}...")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("   🔨 Atualizando ui_code para formato '000-000'...")
        # PostgreSQL: TO_CHAR(val, 'FM000') garante zero padding
        sql = """
            UPDATE ui_catalog 
            SET ui_code = TO_CHAR(screen_code, 'FM000') || '-' || TO_CHAR(object_code, 'FM000')
        """
        cursor.execute(sql)
        rows = cursor.rowcount
        conn.commit()
        
        print(f"   ✅ Sucesso! {rows} registros atualizados.")
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False

def main():
    print("=" * 70)
    print("ATUALIZAÇÃO DE FORMATO: XXX-XXX")
    print("=" * 70)

    # 1. Atualizar Local
    local_url = "postgresql://postgres:*Paraiso1978@127.0.0.1:5432/bd_app_versus"
    update_db(local_url, "LOCAL (Porta 5432)")

    # 2. Atualizar Cloud (via Proxy)
    cloud_url = "postgresql://postgres:*Paraiso1978@127.0.0.1:5433/bd_app_versus"
    update_db(cloud_url, "CLOUD (Porta 5433)")

if __name__ == "__main__":
    main()
