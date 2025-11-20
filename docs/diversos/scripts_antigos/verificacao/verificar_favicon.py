#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificação do Favicon
Verifica se o favicon está configurado corretamente
"""

import os
import sys


def verificar_favicon():
    """Verifica se os arquivos de favicon existem"""
    print("=" * 60)
    print("VERIFICAÇÃO DO FAVICON - Gestão Versus App28")
    print("=" * 60)
    print()

    # Verificar arquivos
    arquivos = {
        "favicon.ico": "static/favicon.ico",
        "favicon.png": "static/img/favicon.png",
    }

    todos_ok = True

    for nome, caminho in arquivos.items():
        existe = os.path.exists(caminho)
        status = "✓ OK" if existe else "✗ FALTANDO"
        tamanho = ""

        if existe:
            tamanho_bytes = os.path.getsize(caminho)
            tamanho = f"({tamanho_bytes:,} bytes)".replace(",", ".")

        print(f"  {status} - {nome}: {caminho} {tamanho}")

        if not existe:
            todos_ok = False

    print()

    # Verificar app_pev.py
    print("Verificando rota no app_pev.py...")
    try:
        with open("app_pev.py", "r", encoding="utf-8") as f:
            conteudo = f.read()
            if "@app.route('/favicon.ico')" in conteudo:
                print("  ✓ OK - Rota do favicon encontrada")
            else:
                print("  ✗ FALTANDO - Rota do favicon não encontrada")
                todos_ok = False
    except Exception as e:
        print(f"  ✗ ERRO ao ler app_pev.py: {e}")
        todos_ok = False

    print()

    # Verificar template base
    print("Verificando templates/base.html...")
    try:
        with open("templates/base.html", "r", encoding="utf-8") as f:
            conteudo = f.read()
            if "favicon.ico" in conteudo:
                print("  ✓ OK - Referência ao favicon encontrada")
            else:
                print("  ✗ FALTANDO - Referência ao favicon não encontrada")
                todos_ok = False
    except Exception as e:
        print(f"  ✗ ERRO ao ler templates/base.html: {e}")
        todos_ok = False

    print()
    print("=" * 60)

    if todos_ok:
        print("✓ TUDO OK! O favicon está configurado corretamente.")
        print()
        print("O erro 'GET /favicon.ico HTTP/1.1 404' não deve mais aparecer.")
        print()
        return 0
    else:
        print("✗ ATENÇÃO! Alguns problemas foram encontrados.")
        print("Revise as mensagens acima.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(verificar_favicon())
