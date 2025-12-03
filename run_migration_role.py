#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar a migração de role consultant -> collaborator
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

def main():
    print("="*60)
    print("MIGRAÇÃO: Consultant → Collaborator")
    print("="*60)
    
    try:
        # Importar aplicação Flask
        from app_pev import app
        
        with app.app_context():
            # Configurar Alembic
            alembic_cfg = Config("migrations/alembic.ini")
            alembic_cfg.set_main_option("script_location", "migrations")
            
            # 1. Verificar versão atual
            print("\n📋 Passo 1: Verificando versão atual...")
            command.current(alembic_cfg, verbose=True)
            
            # 2. Aplicar migração
            print("\n🚀 Passo 2: Aplicando migração...")
            command.upgrade(alembic_cfg, "head")
            
            # 3. Verificar nova versão
            print("\n✅ Passo 3: Verificando nova versão...")
            command.current(alembic_cfg, verbose=True)
            
            # 4. Verificar dados
            print("\n📊 Passo 4: Verificando distribuição de roles...")
            
            # Get database URL
            engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT role, COUNT(*) as total
                    FROM users
                    GROUP BY role
                    ORDER BY role
                """))
                
                print("\n" + "="*60)
                print("Distribuição de Roles:")
                print("="*60)
                rows = result.fetchall()
                for row in rows:
                    print(f"  {row[0]}: {row[1]} usuário(s)")
                print("="*60)
                
                # Verificar se ainda existem 'consultant'
                result_consultant = conn.execute(text("""
                    SELECT COUNT(*) as total
                    FROM users
                    WHERE role = 'consultant'
                """))
                consultant_count = result_consultant.fetchone()[0]
                
                if consultant_count == 0:
                    print("\n✅ SUCESSO: Nenhum usuário 'consultant' encontrado!")
                else:
                    print(f"\n⚠️  ATENÇÃO: Ainda existem {consultant_count} usuários 'consultant'")
            
            print("\n" + "="*60)
            print("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*60)
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
