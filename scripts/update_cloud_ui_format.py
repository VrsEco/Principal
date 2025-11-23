#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de atualização: Formatar ui_code para XXX-XXX no CLOUD
Data: 2025-11-23
"""

import psycopg2

CLOUD_URL = "postgresql://postgres:*Paraiso1978@127.0.0.1:5433/bd_app_versus"

def main():
    print("=" * 70)
    print("ATUALIZAÇÃO CLOUD: Formato XXX-XXX")
    print("=" * 70)

    try:
        conn = psycopg2.connect(CLOUD_URL)
        cursor = conn.cursor()
        
        print("\n🔨 Atualizando ui_code para formato '000-000'...")
        sql = """
            UPDATE ui_catalog 
            SET ui_code = TO_CHAR(screen_code, 'FM000') || '-' || TO_CHAR(object_code, 'FM000')
        """
        cursor.execute(sql)
        rows = cursor.rowcount
        conn.commit()
        
        print(f"✅ Sucesso! {rows} registros atualizados no CLOUD.")
        
        # Verificar alguns exemplos
        print("\n📋 Exemplos de códigos atualizados:")
        cursor.execute("SELECT ui_code, name FROM ui_catalog LIMIT 5")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {row[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ ATUALIZAÇÃO CLOUD CONCLUÍDA")
    print("=" * 70)
    return True

if __name__ == "__main__":
    main()
