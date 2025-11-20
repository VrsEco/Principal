#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APP25 - Script de Instalação de Dependências
Instala todas as dependências necessárias
"""

import subprocess
import sys
import os


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
    """Função principal de instalação"""
    print("=" * 60)
    print("APP25 - INSTALAÇÃO DE DEPENDÊNCIAS")
    print("=" * 60)

    # Lista de dependências principais
    packages = [
        "Flask==2.3.3",
        "Flask-SQLAlchemy==3.0.5",
        "Flask-Migrate==4.0.5",
        "Flask-Login==0.6.3",
        "Flask-WTF==1.1.1",
        "Flask-Mail==0.9.1",
        "Flask-CORS==4.0.0",
        "SQLAlchemy==2.0.21",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "Werkzeug==2.3.7",
        "WTForms==3.0.1",
        "bcrypt==4.0.1",
    ]

    print(f"\nInstalando {len(packages)} dependências...")

    success_count = 0
    failed_packages = []

    for package in packages:
        if install_package(package):
            success_count += 1
        else:
            failed_packages.append(package)

    print("\n" + "=" * 60)
    print("RESUMO DA INSTALAÇÃO")
    print("=" * 60)
    print(f"✅ Sucessos: {success_count}")
    print(f"❌ Falhas: {len(failed_packages)}")

    if failed_packages:
        print("\nPacotes que falharam:")
        for package in failed_packages:
            print(f"  - {package}")

    # Testa importações básicas
    print("\nTestando importações básicas...")
    try:
        import flask

        print("✅ Flask importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar Flask: {e}")

    try:
        import flask_sqlalchemy

        print("✅ Flask-SQLAlchemy importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar Flask-SQLAlchemy: {e}")

    try:
        import requests

        print("✅ Requests importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar Requests: {e}")

    try:
        from dotenv import load_dotenv

        print("✅ python-dotenv importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar python-dotenv: {e}")

    print("\n" + "=" * 60)
    print("INSTALAÇÃO CONCLUÍDA!")
    print("=" * 60)


if __name__ == "__main__":
    main()
