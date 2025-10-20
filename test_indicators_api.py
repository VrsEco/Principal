#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

def test_api():
    """Testar API de indicadores"""
    
    company_id = 13
    url = f"http://127.0.0.1:5002/grv/api/company/{company_id}/indicators"
    
    try:
        print(f"=== TESTANDO API: {url} ===\n")
        
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"Success: {data.get('success')}")
            indicators = data.get('indicators', [])
            
            print(f"\nTotal de indicadores: {len(indicators)}")
            
            if indicators:
                print("\nDetalhes dos indicadores:")
                for ind in indicators:
                    print(f"\n  ID: {ind.get('id')}")
                    print(f"  Nome: {ind.get('name')}")
                    print(f"  Codigo: {ind.get('code')}")
                    print(f"  Unidade: {ind.get('unit')}")
                    print(f"  Grupo ID: {ind.get('group_id')}")
            else:
                print("\nNenhum indicador retornado pela API")
                print("\nVerificando diretamente no banco...")
                
                from database.postgres_helper import connect
                conn = connect()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, code, company_id 
                    FROM indicators 
                    WHERE company_id = %s
                """, (company_id,))
                rows = cursor.fetchall()
                
                print(f"Indicadores no banco para empresa {company_id}: {len(rows)}")
                for row in rows:
                    print(f"  ID {row[0]}: {row[1]} ({row[2]})")
                
                cursor.close()
                conn.close()
        else:
            print(f"ERRO HTTP: {response.status_code}")
            print(response.text)
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()
