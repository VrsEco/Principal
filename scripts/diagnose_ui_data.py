#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico: Verificar dados em ui_pages e ui_catalog
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
from models import init_app

def main():
    print("=" * 70)
    print("DIAGNÓSTICO: Tabelas de UI")
    print("=" * 70)

    # Configurar app Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializar DB
    # init_app(app) # Não precisamos inicializar tudo, apenas pegar a conexão
    
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
        
        # 1. Verificar ui_pages (Antigo)
        print("\n1. Verificando tabela 'ui_pages' (Sistema Antigo)...")
        try:
            cursor.execute("SELECT count(*) FROM ui_pages")
            count_pages = cursor.fetchone()[0]
            print(f"   ✅ Tabela encontrada. Registros: {count_pages}")
            
            if count_pages > 0:
                print("   Amostra de dados (top 5):")
                cursor.execute("SELECT page_code, page_name, page_route FROM ui_pages LIMIT 5")
                for row in cursor.fetchall():
                    print(f"   - [{row[0]}] {row[1]} ({row[2]})")
        except Exception as e:
            print(f"   ❌ Tabela 'ui_pages' não encontrada ou erro: {e}")

        # 2. Verificar ui_catalog (Novo)
        print("\n2. Verificando tabela 'ui_catalog' (Sistema Novo)...")
        try:
            cursor.execute("SELECT count(*) FROM ui_catalog")
            count_catalog = cursor.fetchone()[0]
            print(f"   ✅ Tabela encontrada. Registros: {count_catalog}")
            
            if count_catalog > 0:
                print("   Amostra de dados (top 5):")
                cursor.execute("SELECT screen_code, ui_code, name, route FROM ui_catalog LIMIT 5")
                for row in cursor.fetchall():
                    print(f"   - [{row[0]}] {row[1]} - {row[2]} ({row[3]})")
        except Exception as e:
            print(f"   ❌ Tabela 'ui_catalog' não encontrada ou erro: {e}")

        conn.close()

    except Exception as e:
        print(f"❌ Erro geral de conexão: {e}")
        return False

    print("\n" + "=" * 70)
    return True

if __name__ == "__main__":
    main()
