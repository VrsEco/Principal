#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migração: Aplicar criação da tabela ui_catalog
Data: 2025-11-23
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_database import get_db
from flask import Flask
from config import Config

def main():
    print("=" * 70)
    print("MIGRAÇÃO: Criar tabela ui_catalog")
    print("=" * 70)

    # Configurar app Flask para contexto (necessário para algumas configs de DB)
    app = Flask(__name__)
    app.config.from_object(Config)

    # Obter conexão
    try:
        db = get_db()
    except Exception as e:
        print(f"❌ Erro ao obter conexão com o banco: {e}")
        return False

    # Verificar se é PostgreSQL (recomendado, mas funciona em SQLite também se o SQL for compatível)
    # O SQL usa SERIAL, que é específico do PG, mas o script pode adaptar ou falhar.
    # Vamos assumir PG ou compatibilidade.

    try:
        # Tentar obter conexão direta (psycopg2 ou pg8000)
        if hasattr(db, "_get_connection"):
             conn = db._get_connection()
        elif hasattr(db, "engine"):
             conn = db.engine.raw_connection()
        else:
             # Fallback para SQLite ou outro
             print("⚠️  Aviso: Método de conexão não padrão. Tentando acesso direto...")
             conn = db

        cursor = conn.cursor()

        print("\n📋 Verificando se a tabela já existe...")
        
        # Verificar existência da tabela
        try:
            cursor.execute("SELECT count(*) FROM ui_catalog")
            cursor.fetchone()
            print("⚠️  A tabela 'ui_catalog' já existe!")
            
            resposta = input("\n🔹 Deseja recriar/atualizar (pode causar erros se já existir)? (sim/não): ").strip().lower()
            if resposta not in ["sim", "s", "yes", "y"]:
                print("\n❌ Migração cancelada.")
                conn.close()
                return False
        except Exception:
            print("   Tabela não encontrada (o que é bom, vamos criá-la).")
            # Rollback em caso de erro na verificação (necessário para PG)
            conn.rollback()

        print("\n🔧 Executando migração...")

        # Ler arquivo SQL
        sql_file = Path(__file__).parent.parent / "migrations" / "20251108_create_ui_catalog.sql"
        if not sql_file.exists():
            print(f"❌ ERRO: Arquivo SQL não encontrado: {sql_file}")
            conn.close()
            return False

        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Executar migração
        cursor.execute(sql_content)
        conn.commit()

        print("✅ Migração executada com sucesso!")
        
        conn.close()

        print("\n" + "=" * 70)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        
        return True

    except Exception as e:
        print(f"\n❌ ERRO durante a migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
