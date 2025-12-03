#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar status da migração
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app_pev import app
from sqlalchemy import text, create_engine

with app.app_context():
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    
    with engine.connect() as conn:
        # Verificar versão do Alembic
        print("VERSÃO ALEMBIC:")
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.fetchone()
        if version:
            print(f"  Versão atual: {version[0]}")
        else:
            print("  Nenhuma versão encontrada")
        
        print("\nDISTRIBUIÇÃO DE ROLES:")
        result = conn.execute(text("""
            SELECT role, COUNT(*) as total
            FROM users
            GROUP BY role
            ORDER BY role
        """))
        for row in result:
            print(f"  {row[0]}: {row[1]} usuário(s)")
        
        # Consultant específico
        result = conn.execute(text("""
            SELECT COUNT(*) as total
            FROM users
            WHERE role = 'consultant'
        """))
        count = result.fetchone()[0]
        print(f"\nUsuários 'consultant': {count}")
        
        if count == 0:
            print("✅ MIGRAÇÃO APLICADA COM SUCESSO!")
        else:
            print("⚠️  MIGRAÇÃO AINDA NÃO APLICADA")

