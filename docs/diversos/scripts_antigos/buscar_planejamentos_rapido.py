#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca RÁPIDA de planejamentos - Versão Otimizada
"""

import os
import sys

def buscar_rapido(arquivo_sql):
    """
    Busca otimizada apenas nas linhas com INSERT
    """
    nome = os.path.basename(arquivo_sql)
    print(f"\nAnalisando: {nome}")
    
    if not os.path.exists(arquivo_sql):
        print(f"Arquivo nao encontrado: {arquivo_sql}")
        return 0
    
    # Tamanho
    tamanho_mb = os.path.getsize(arquivo_sql) / (1024 * 1024)
    print(f"Tamanho: {tamanho_mb:.2f} MB")
    
    count = 0
    detalhes = []
    
    try:
        with open(arquivo_sql, 'r', encoding='utf-8', errors='ignore') as f:
            for linha in f:
                # Pular linhas que não são INSERT
                if 'INSERT INTO' not in linha:
                    continue
                
                # Procurar por tabela company_plans
                if 'company_plan' not in linha.lower():
                    continue
                
                # Procurar por company_id = 25
                # Formato típico: ...\t25\t... ou ...	25	...
                if '\t25\t' in linha or ' 25 ' in linha or ',25,' in linha:
                    count += 1
                    # Pegar primeiro 150 caracteres
                    detalhes.append(linha[:150])
        
        print(f"RESULTADO: {count} planejamento(s) encontrado(s)\n")
        
        if detalhes:
            print("Detalhes:")
            for i, det in enumerate(detalhes, 1):
                print(f"  {i}. {det}...")
        
        return count
        
    except Exception as e:
        print(f"Erro: {e}")
        return 0

# Arquivos
arquivos = [
    r"C:\gestaoversus\referencias\recuperacao_28out\backup_recuperacao_20251028_v2.sql",
    r"C:\gestaoversus\referencias\recuperacao_28out\dump_bd_app_versus.sql"
]

print("="*60)
print("BUSCA RAPIDA - PLANEJAMENTOS EUA MOVEIS")
print("="*60)

total = 0
for arq in arquivos:
    total += buscar_rapido(arq)

print("\n" + "="*60)
print(f"TOTAL GERAL: {total} planejamento(s)")
print("="*60)


