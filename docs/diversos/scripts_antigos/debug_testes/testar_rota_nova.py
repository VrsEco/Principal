#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testar se a nova rota esta respondendo"""

import requests
import time

print("Aguardando 3 segundos para servidor iniciar...")
time.sleep(3)

print("\nTestando rota /configs/system/audit...")
try:
    response = requests.get('http://localhost:5002/configs/system/audit', timeout=5, allow_redirects=False)
    
    if response.status_code == 404:
        print("[ERRO] Rota retornou 404!")
        print("O servidor ainda nao foi reiniciado ou nao carregou as mudancas.")
        print("\nSOLUCAO:")
        print("1. Pare o servidor atual (Ctrl+C no terminal onde esta rodando)")
        print("2. Execute: python app_pev.py")
        print("3. Verifique a mensagem: 'Sistema de auditoria de rotas integrado com sucesso!'")
        
    elif response.status_code == 302 or response.status_code == 401:
        print("[OK] Rota existe! Redirecionando para login (status {})".format(response.status_code))
        print("\nSUCESSO! A rota foi carregada corretamente.")
        print("Acesse: http://localhost:5002/configs/system/audit")
        print("Faca login com: admin@versus.com.br / 123456")
        
    elif response.status_code == 200:
        print("[OK] Rota acessivel! (status 200)")
        print("\nSUCESSO! A rota foi carregada corretamente.")
        
    else:
        print(f"Status inesperado: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("[ERRO] Servidor nao esta respondendo!")
    print("Execute: python app_pev.py")
    
except Exception as e:
    print(f"[ERRO] {e}")

