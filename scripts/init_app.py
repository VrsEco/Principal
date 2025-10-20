#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Inicialização da Aplicação
Verifica dependências, cria estruturas e prepara ambiente
"""

import os
import sys
from pathlib import Path

def print_header():
    """Imprime cabeçalho"""
    print("=" * 60)
    print("🚀 GestaoVersus - Inicialização da Aplicação")
    print("=" * 60)

def check_python_version():
    """Verifica versão do Python"""
    print("\n🐍 Verificando versão do Python...")
    
    required_version = (3, 9)
    current_version = sys.version_info[:2]
    
    if current_version >= required_version:
        print(f"✅ Python {current_version[0]}.{current_version[1]} OK")
        return True
    else:
        print(f"❌ Python {required_version[0]}.{required_version[1]}+ necessário")
        print(f"   Versão atual: {current_version[0]}.{current_version[1]}")
        return False

def check_environment_variables():
    """Verifica variáveis de ambiente essenciais"""
    print("\n🔐 Verificando variáveis de ambiente...")
    
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "FLASK_APP"
    ]
    
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var} configurada")
        else:
            print(f"❌ {var} não configurada")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Variáveis faltando: {', '.join(missing_vars)}")
        print("   Configure no arquivo .env")
        return False
    
    return True

def create_required_directories():
    """Cria diretórios necessários"""
    print("\n📁 Criando diretórios necessários...")
    
    dirs = [
        Path("uploads"),
        Path("temp_pdfs"),
        Path("logs"),
        Path("backups"),
        Path("instance"),
    ]
    
    for dir_path in dirs:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ {dir_path}")
        except Exception as e:
            print(f"❌ Erro ao criar {dir_path}: {e}")
            return False
    
    return True

def check_database_connection():
    """Verifica conexão com banco de dados"""
    print("\n💾 Verificando conexão com banco de dados...")
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL não configurada")
        return False
    
    try:
        # Tentar importar SQLAlchemy
        from sqlalchemy import create_engine
        
        # Criar engine
        engine = create_engine(database_url, echo=False)
        
        # Testar conexão
        with engine.connect() as connection:
            print("✅ Conexão com banco de dados OK")
            return True
            
    except ImportError:
        print("❌ SQLAlchemy não instalada")
        print("   Execute: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Erro ao conectar no banco: {e}")
        print("   Verifique DATABASE_URL e se o PostgreSQL está rodando")
        return False

def check_redis_connection():
    """Verifica conexão com Redis (opcional)"""
    print("\n⚡ Verificando conexão com Redis...")
    
    redis_url = os.getenv("REDIS_URL")
    
    if not redis_url:
        print("⚠️ REDIS_URL não configurada (opcional)")
        return True
    
    try:
        import redis
        
        # Extrair host e porta do URL
        # redis://localhost:6379/0
        import re
        match = re.match(r'redis://(?::(.+)@)?([^:]+):(\d+)/(\d+)', redis_url)
        
        if match:
            password = match.group(1)
            host = match.group(2)
            port = int(match.group(3))
            db = int(match.group(4))
            
            # Conectar
            r = redis.Redis(host=host, port=port, db=db, password=password, socket_timeout=5)
            r.ping()
            
            print("✅ Conexão com Redis OK")
            return True
        else:
            print("⚠️ REDIS_URL inválida")
            return True
            
    except ImportError:
        print("⚠️ Redis não instalado (opcional)")
        return True
    except Exception as e:
        print(f"⚠️ Erro ao conectar no Redis: {e}")
        print("   Redis é opcional, continuando...")
        return True

def run_database_migrations():
    """Executa migrações do banco de dados"""
    print("\n🔄 Executando migrações do banco...")
    
    try:
        # Importar Flask app
        from app_pev import app, db
        
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            print("✅ Migrações aplicadas")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao executar migrações: {e}")
        return False

def create_default_admin_user():
    """Cria usuário admin padrão se não existir"""
    print("\n👤 Verificando usuário administrador...")
    
    try:
        from app_pev import app, db
        from models.user import User
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            # Verificar se já existe admin
            admin = User.query.filter_by(email='admin@gestaoversos.com').first()
            
            if admin:
                print("✅ Usuário administrador já existe")
                return True
            
            # Criar usuário admin
            admin = User(
                username='admin',
                email='admin@gestaoversos.com',
                password=generate_password_hash('admin123'),  # TROCAR EM PRODUÇÃO!
                is_active=True,
                is_admin=True
            )
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Usuário administrador criado")
            print("   Email: admin@gestaoversos.com")
            print("   Senha: admin123 (TROCAR IMEDIATAMENTE!)")
            
            return True
            
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível criar usuário admin: {e}")
        return True  # Não é crítico

def print_summary(checks):
    """Imprime resumo das verificações"""
    print("\n" + "=" * 60)
    print("📊 Resumo da Inicialização")
    print("=" * 60)
    
    all_passed = all(checks.values())
    
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
    
    print("=" * 60)
    
    if all_passed:
        print("✅ Aplicação pronta para iniciar!")
        print("\nPara iniciar:")
        print("  Desenvolvimento: python app_pev.py")
        print("  Produção: gunicorn app_pev:app")
    else:
        print("❌ Corrija os problemas acima antes de iniciar")
    
    print("=" * 60)
    
    return all_passed

def main():
    """Função principal"""
    print_header()
    
    checks = {
        "Python Version": check_python_version(),
        "Environment Variables": check_environment_variables(),
        "Required Directories": create_required_directories(),
        "Database Connection": check_database_connection(),
        "Redis Connection": check_redis_connection(),
        "Database Migrations": run_database_migrations(),
        "Admin User": create_default_admin_user(),
    }
    
    success = print_summary(checks)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Inicialização cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

