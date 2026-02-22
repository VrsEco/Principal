#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificação de Configuração - APP26
Verifica se todas as configurações necessárias estão corretas
"""

import os
import sys
from pathlib import Path


def print_header(title):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(item, status, message=""):
    """Imprime status de verificação"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {item:<40} {message}")


def verificar_estrutura():
    """Verifica estrutura de diretórios"""
    print_header("ESTRUTURA DE DIRETÓRIOS")

    diretorios_necessarios = [
        "instance",
        "uploads",
        "temp_pdfs",
        "database",
        "models",
        "services",
        "templates",
        "static",
        "modules",
    ]

    tudo_ok = True
    for diretorio in diretorios_necessarios:
        existe = Path(diretorio).exists()
        print_status(diretorio + "/", existe)
        if not existe:
            tudo_ok = False

    return tudo_ok


def verificar_arquivos():
    """Verifica arquivos essenciais"""
    print_header("ARQUIVOS ESSENCIAIS")

    arquivos_necessarios = [
        "app_pev.py",
        "config.py",
        "config_database.py",
        "requirements.txt",
        "env.example",
    ]

    tudo_ok = True
    for arquivo in arquivos_necessarios:
        existe = Path(arquivo).exists()
        print_status(arquivo, existe)
        if not existe:
            tudo_ok = False

    return tudo_ok


def verificar_env():
    """Verifica arquivo .env"""
    print_header("VARIÁVEIS DE AMBIENTE")

    env_existe = Path(".env").exists()
    print_status("Arquivo .env", env_existe)

    if not env_existe:
        print("\n⚠️  ATENÇÃO: Arquivo .env não encontrado!")
        print("   Execute: copy env.example .env")
        print("   Depois edite o arquivo .env com suas configurações")
        return False

    # Carrega .env
    from dotenv import load_dotenv

    load_dotenv()

    # Variáveis essenciais
    variaveis = {
        "FLASK_APP": "app_pev.py",
        "DB_TYPE": "sqlite ou postgresql",
        "SECRET_KEY": "chave de segurança",
    }

    tudo_ok = True
    for var, descricao in variaveis.items():
        valor = os.environ.get(var)
        if valor:
            # Oculta valores sensíveis
            if "KEY" in var or "PASSWORD" in var:
                valor_exibir = valor[:10] + "..." if len(valor) > 10 else "***"
            else:
                valor_exibir = valor
            print_status(var, True, f"= {valor_exibir}")
        else:
            print_status(var, False, f"({descricao})")
            tudo_ok = False

    return tudo_ok and env_existe


def verificar_banco():
    """Verifica banco de dados"""
    print_header("BANCO DE DADOS")

    try:
        from config_database import get_db

        db = get_db()
        print_status("Conexão com banco", True)

        # Tenta listar empresas
        empresas = db.get_companies()
        print_status("Estrutura do banco", True, f"({len(empresas)} empresas)")

        return True
    except Exception as e:
        print_status("Conexão com banco", False, str(e))
        print("\n⚠️  Execute: python setup.py")
        return False


def verificar_dependencias():
    """Verifica dependências instaladas"""
    print_header("DEPENDÊNCIAS PYTHON")

    dependencias = ["flask", "sqlalchemy", "dotenv", "requests", "reportlab"]

    tudo_ok = True
    for dep in dependencias:
        try:
            if dep == "dotenv":
                __import__("dotenv")
            else:
                __import__(dep)
            print_status(dep, True)
        except ImportError:
            print_status(dep, False, "não instalado")
            tudo_ok = False

    return tudo_ok


def verificar_integracao():
    """Verifica configuração de integrações"""
    print_header("INTEGRAÇÕES (OPCIONAL)")

    from dotenv import load_dotenv

    load_dotenv()

    # IA
    ai_provider = os.environ.get("AI_PROVIDER", "não configurado")
    ai_key = os.environ.get("AI_API_KEY")
    ai_ok = ai_provider == "local" or (ai_key and len(ai_key) > 0)
    print_status("Inteligência Artificial", ai_ok, f"({ai_provider})")

    # E-mail
    mail_server = os.environ.get("MAIL_SERVER")
    mail_ok = mail_server and len(mail_server) > 0
    print_status("Envio de E-mail", mail_ok, f"({mail_server or 'não configurado'})")

    # WhatsApp
    whatsapp_provider = os.environ.get("WHATSAPP_PROVIDER", "não configurado")
    whatsapp_key = os.environ.get("WHATSAPP_API_KEY")
    whatsapp_ok = whatsapp_provider == "local" or (
        whatsapp_key and len(whatsapp_key) > 0
    )
    print_status("WhatsApp", whatsapp_ok, f"({whatsapp_provider})")

    return True  # Integrações são opcionais


def main():
    """Função principal"""
    print("\n")
    print("🔍 VERIFICAÇÃO DE CONFIGURAÇÃO - APP26")
    print("=" * 60)

    resultados = []

    # Verificações
    resultados.append(("Estrutura", verificar_estrutura()))
    resultados.append(("Arquivos", verificar_arquivos()))
    resultados.append(("Dependências", verificar_dependencias()))
    resultados.append(("Ambiente", verificar_env()))
    resultados.append(("Banco de Dados", verificar_banco()))
    verificar_integracao()  # Opcional

    # Resumo
    print_header("RESUMO")

    todas_ok = all(ok for _, ok in resultados)

    for nome, ok in resultados:
        print_status(nome, ok)

    print("\n" + "=" * 60)

    if todas_ok:
        print("✅ CONFIGURAÇÃO COMPLETA!")
        print("\nPróximos passos:")
        print("1. Execute: python app_pev.py")
        print("2. Acesse: http://127.0.0.1:5002")
        return 0
    else:
        print("❌ CONFIGURAÇÃO INCOMPLETA!")
        print("\nCorrija os problemas acima antes de executar a aplicação.")
        print("\nConsulte: CONFIGURACAO_AMBIENTE.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
