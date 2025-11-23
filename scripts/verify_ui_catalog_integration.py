#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificação: Testar integração do UiCatalog no app_pev
Data: 2025-11-23
"""

import sys
import os
from pathlib import Path
from flask import Flask, request

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from models import init_app, db
from models.ui_catalog import UiCatalog

def main():
    print("=" * 70)
    print("VERIFICAÇÃO: Integração UiCatalog")
    print("=" * 70)

    # Configurar app Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializar DB
    init_app(app)

    with app.app_context():
        print("\n1. Verificando conexão com banco e tabela ui_catalog...")
        try:
            count = UiCatalog.query.count()
            print(f"   ✅ Tabela acessível. Total de registros: {count}")
        except Exception as e:
            print(f"   ❌ Erro ao acessar tabela: {e}")
            return False

        print("\n2. Verificando resolução de rotas...")
        
        # Simular cache loading (copiado da lógica do app_pev)
        _UI_PAGE_CACHE = {}
        
        entries = UiCatalog.query.filter(
            UiCatalog.is_active == True,
            UiCatalog.route != None
        ).all()
        
        for entry in entries:
            route = entry.route
            screen_code = str(entry.screen_code)
            if route:
                # Normalização simples para teste
                norm_route = route.split("?", 1)[0].strip()
                if norm_route != "/" and norm_route.endswith("/"):
                    norm_route = norm_route[:-1]
                if norm_route.startswith("/pev"):
                    norm_route = norm_route[len("/pev"):]
                    if not norm_route.startswith("/"):
                        norm_route = f"/{norm_route}"
                
                _UI_PAGE_CACHE[norm_route] = screen_code
                print(f"   Mapped: {norm_route} -> {screen_code}")

        # Testar uma rota conhecida (do seed)
        test_route = "/implantacao/modelo/modefin"
        code = _UI_PAGE_CACHE.get(test_route)
        
        if code == "314":
            print(f"\n✅ Teste de rota '{test_route}' -> '{code}' SUCESSO!")
        else:
            print(f"\n❌ Teste de rota '{test_route}' -> '{code}' FALHOU (Esperado: 314)")
            
            # Debug
            print("   Cache dump:")
            for k, v in _UI_PAGE_CACHE.items():
                print(f"   {k}: {v}")

    print("\n" + "=" * 70)
    print("VERIFICAÇÃO CONCLUÍDA")
    print("=" * 70)
    return True

if __name__ == "__main__":
    main()
