#!/usr/bin/env python3
"""
Script para instalar todas as dependências do PEVAPP24
"""
import subprocess
import sys

def install_package(package):
    """Instala um pacote usando pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} instalado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar {package}: {e}")
        return False

def main():
    """Instala todas as dependências necessárias"""
    packages = [
        "requests",
        "flask",
        "flask-sqlalchemy",
        "flask-migrate", 
        "flask-login",
        "flask-wtf",
        "flask-mail",
        "flask-cors",
        "sqlalchemy",
        "psycopg2-binary",
        "alembic",
        "bcrypt",
        "werkzeug",
        "wtforms",
        "flask-restful",
        "marshmallow",
        "marshmallow-sqlalchemy",
        "weasyprint",
        "reportlab",
        "celery",
        "redis",
        "python-dotenv",
        "pillow",
        "python-dateutil",
        "pytest",
        "pytest-flask",
        "black",
        "flake8"
    ]
    
    print("🚀 Instalando dependências do PEVAPP24...")
    print(f"Python: {sys.executable}")
    print("-" * 50)
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print("-" * 50)
    print(f"✅ {success_count}/{len(packages)} pacotes instalados com sucesso")
    
    if success_count == len(packages):
        print("🎉 Todas as dependências foram instaladas!")
        print("Agora você pode executar: python app_pev.py")
    else:
        print("⚠️  Algumas dependências falharam. Verifique os erros acima.")

if __name__ == "__main__":
    main()

