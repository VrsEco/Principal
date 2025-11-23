#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de consulta JSON: Process Instances
Data: 2025-11-23
"""

import json
import os
import psycopg2

def main():
    # Configurar conexão (prioriza variável de ambiente, fallback para proxy 5433)
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:*Paraiso1978@127.0.0.1:5433/bd_app_versus")
    
    # Ajuste para psycopg2 se necessário
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Query adaptada para ui_catalog
        sql = """
            SELECT ui_code, name, route, description
            FROM ui_catalog 
            WHERE route LIKE '%process/instances%'
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # Formatar como dicionário para JSON
        results = []
        for r in rows:
            results.append({
                "page_code": r[0],  # ui_code
                "page_name": r[1],  # name
                "page_route": r[2], # route
                "description": r[3]
            })
            
        # Output JSON exato como solicitado
        print(json.dumps(results, ensure_ascii=False, indent=2))

        conn.close()

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
