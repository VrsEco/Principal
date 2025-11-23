#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste: Conexão com Cloud SQL
Data: 2025-11-23
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def test_connection():
    print("=" * 70)
    print("TESTE DE CONEXÃO: Google Cloud SQL")
    print("=" * 70)

    # Obter URL do ambiente
    env_url = os.environ.get("DATABASE_URL")
    
    # URL de fallback (TCP Local via Proxy)
    tcp_url = "postgresql://postgres:*Paraiso1978@127.0.0.1:5432/bd_app_versus"
    
    urls_to_try = []
    
    if env_url:
        # Limpar URL do ambiente para formato psycopg2
        clean_url = env_url.replace("postgresql+pg8000://", "postgresql://")
        clean_url = clean_url.replace("postgresql+psycopg2://", "postgresql://")
        urls_to_try.append(("Environment Variable", clean_url))
    
    urls_to_try.append(("TCP Local (Proxy)", tcp_url))
    
    success = False
    
    for source, db_url in urls_to_try:
        print(f"\n🔌 Tentando conectar via: {source}")
        # Mascarar senha para log
        safe_url = db_url
        if "@" in db_url:
            part1, part2 = db_url.split("@")
            if ":" in part1:
                user_pass = part1.split("//")[1]
                if ":" in user_pass:
                    u, p = user_pass.split(":")
                    safe_url = db_url.replace(p, "***")
        
        print(f"   URL: {safe_url}")
        
        if "unix_sock" in db_url and os.name == 'nt':
            print("   ⚠️  Aviso: URL com unix_sock detectada no Windows. Isso geralmente falha.")
            print("      Tentando mesmo assim...")

        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Teste simples
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            print("\n✅ CONEXÃO BEM SUCEDIDA!")
            print(f"   Versão do Banco: {version}")
            
            # Verificar tabela ui_catalog
            try:
                cursor.execute("SELECT count(*) FROM ui_catalog")
                count = cursor.fetchone()[0]
                print(f"   Tabela 'ui_catalog' acessível. Registros: {count}")
            except Exception as e:
                print(f"   ⚠️  Aviso: Não foi possível ler 'ui_catalog': {e}")
                
            conn.close()
            success = True
            break
            
        except Exception as e:
            print(f"   ❌ Falha: {e}")
            
    if not success:
        print("\n❌ TODAS AS TENTATIVAS FALHARAM")
        print("\n💡 DICAS:")
        print("   1. O Cloud SQL Proxy está rodando?")
        print("      Comando: ./cloud_sql_proxy -instances=vrs-eco-478714:southamerica-east1:gestaoversus-db-prod=tcp:5432")
        print("   2. As credenciais (usuário/senha) estão corretas?")
        return False
        
    return True

if __name__ == "__main__":
    test_connection()
