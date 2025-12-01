"""
Script para criar tabelas faltantes baseado nos models do SQLAlchemy
Compatível com Flask-SQLAlchemy 3.x
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar app e models
from flask import Flask
from config import Config
from models import init_app

print("Inicializando aplicação...")

# Criar app
app = Flask(__name__)
app.config.from_object(Config)

# Inicializar extensões
db, login_manager, migrate = init_app(app)

print("Criando tabelas faltantes...")

with app.app_context():
    # Importar todos os models para garantir que estão registrados
    from models import (user, company, plan, participant, company_data,
                       driver_topic, okr_global, okr_area, project, 
                       ai_agent, user_log, team, activity_work_log, 
                       activity_comment, product, product_rampup, note,
                       ui_catalog, employee, role)
    
    # Verificar quais tabelas existem
    from sqlalchemy import inspect, text
    
    with db.session.connection() as conn:
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())
        
        print(f"\nTabelas existentes no banco: {len(existing_tables)}")
        for table in sorted(existing_tables):
            print(f"  ✓ {table}")
        
        # Pegar todas as tabelas definidas nos models
        model_tables = set(db.Model.metadata.tables.keys())
        
        print(f"\nTabelas definidas nos models: {len(model_tables)}")
        for table in sorted(model_tables):
            print(f"  • {table}")
        
        # Identificar tabelas faltantes
        missing_tables = model_tables - existing_tables
        
        if missing_tables:
            print(f"\n⚠ Tabelas FALTANTES: {len(missing_tables)}")
            for table in sorted(missing_tables):
                print(f"  ✗ {table}")
            
            print("\n🔧 Criando tabelas faltantes...")
            
            # Usar db.create_all() que cria apenas as tabelas que não existem
            db.create_all()
            
            print("  ✓ Tabelas criadas!")
            
            print("\n✅ Processo concluído!")
        else:
            print("\n✅ Todas as tabelas já existem!")
        
        # Verificar novamente
        inspector = inspect(conn)
        final_tables = set(inspector.get_table_names())
        print(f"\nTotal de tabelas no banco agora: {len(final_tables)}")
        
        # Listar tabelas criadas
        newly_created = final_tables - existing_tables
        if newly_created:
            print(f"\nTabelas recém-criadas: {len(newly_created)}")
            for table in sorted(newly_created):
                print(f"  + {table}")
