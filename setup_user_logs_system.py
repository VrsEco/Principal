#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup User Logs System
Creates database tables and default admin user for the logging system
"""

import os
import sys
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import DevelopmentConfig
from models import init_app as init_models, db
from services.auth_service import auth_service
from services.log_service import log_service

def create_app():
    """Create Flask application"""
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)
    
    # Initialize models
    init_models(app)
    
    return app

def setup_database():
    """Setup database tables"""
    print("🔧 Configurando banco de dados...")
    
    try:
        with app.app_context():
            # Check if tables exist first
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['users', 'user_logs']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"⚠️ Tabelas ausentes: {missing_tables}")
                # Only create missing tables
                db.create_all()
                print("✅ Tabelas criadas com sucesso")
            else:
                print(f"✅ Todas as tabelas necessárias já estão presentes: {required_tables}")
            
            return True
                
    except Exception as e:
        print(f"❌ Erro ao configurar banco de dados: {str(e)}")
        return False

def create_default_admin():
    """Create default admin user"""
    print("👤 Criando usuário administrador padrão...")
    
    try:
        with app.app_context():
            admin_user = auth_service.create_admin_user()
            
            if admin_user:
                print(f"✅ Usuário administrador criado:")
                print(f"   Email: {admin_user.email}")
                print(f"   Nome: {admin_user.name}")
                print(f"   Role: {admin_user.role}")
                print(f"   Senha: 123456")
                return True
            else:
                print("❌ Falha ao criar usuário administrador")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao criar usuário administrador: {str(e)}")
        return False

def test_logging_system():
    """Test the logging system"""
    print("🧪 Testando sistema de logs...")
    
    try:
        with app.app_context():
            # Get admin user for testing
            from models.user import User
            admin_user = User.query.filter_by(email='admin@versus.com.br').first()
            
            if not admin_user:
                print("❌ Usuário administrador não encontrado para teste")
                return False
            
            # Create a test log with admin user
            test_log = log_service.create_log(
                action='CREATE',
                entity_type='test',
                entity_id='1',
                entity_name='Teste do Sistema',
                description='Teste inicial do sistema de logs'
            )
            
            if test_log:
                print("✅ Sistema de logs funcionando corretamente")
                
                # Get logs count
                logs = log_service.get_logs(limit=1)
                print(f"✅ Logs encontrados: {len(logs)}")
                
                return True
            else:
                print("❌ Falha ao criar log de teste")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao testar sistema de logs: {str(e)}")
        return False

def setup_blueprints():
    """Setup API blueprints"""
    print("🔗 Configurando blueprints da API...")
    
    try:
        from api.auth import auth_bp
        from api.logs import logs_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(logs_bp)
        
        print("✅ Blueprints registrados com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao registrar blueprints: {str(e)}")
        return False

def main():
    """Main setup function"""
    global app
    
    print("🚀 Iniciando configuração do Sistema de Logs de Usuários")
    print("=" * 60)
    
    # Create Flask app
    app = create_app()
    
    # Setup database
    if not setup_database():
        print("❌ Falha na configuração do banco de dados")
        return False
    
    # Create default admin user
    if not create_default_admin():
        print("❌ Falha ao criar usuário administrador")
        return False
    
    # Setup blueprints
    if not setup_blueprints():
        print("❌ Falha ao configurar blueprints")
        return False
    
    # Test logging system
    if not test_logging_system():
        print("❌ Falha no teste do sistema de logs")
        return False
    
    print("=" * 60)
    print("🎉 Sistema de Logs de Usuários configurado com sucesso!")
    print("")
    print("📋 Resumo da configuração:")
    print("   ✅ Tabelas de banco de dados criadas")
    print("   ✅ Usuário administrador criado")
    print("   ✅ Blueprints de API registrados")
    print("   ✅ Sistema de logs testado")
    print("")
    print("🔐 Credenciais de acesso:")
    print("   Email: admin@gestaoverus.com.br")
    print("   Senha: 123456")
    print("")
    print("🌐 Rotas disponíveis:")
    print("   /auth/login - Página de login")
    print("   /logs/ - Dashboard de logs")
    print("   /logs/stats - Estatísticas de logs")
    print("   /auth/users - Listar usuários (admin)")
    print("")
    print("📝 Próximos passos:")
    print("   1. Integre o middleware de auditoria nas suas rotas")
    print("   2. Adicione decoradores de log nas operações CRUD")
    print("   3. Configure o sistema de login na aplicação principal")
    print("   4. Teste todas as funcionalidades")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
