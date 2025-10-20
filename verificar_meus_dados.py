#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script simples para verificar SEUS dados no APP26"""

import sqlite3

def verificar():
    print("\n" + "="*70)
    print("  VERIFICACAO RAPIDA - SEUS DADOS NO APP26")
    print("="*70 + "\n")
    
    conn = sqlite3.connect('instance/pevapp22.db')
    cursor = conn.cursor()
    
    # Contar dados
    cursor.execute("SELECT COUNT(*) FROM participants")
    participantes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM drivers")
    drivers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM okrs")
    okrs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM projects")
    projetos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM company_data")
    company_data = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM companies")
    empresas = cursor.fetchone()[0]
    
    # Mostrar resumo
    print("RESUMO DOS DADOS:")
    print("-" * 70)
    print(f"  Participantes:    {participantes:>3}")
    print(f"  Drivers:          {drivers:>3}")
    print(f"  OKRs:             {okrs:>3}")
    print(f"  Projetos:         {projetos:>3}")
    print(f"  Company Data:     {company_data:>3}")
    print(f"  Empresas:         {empresas:>3}")
    print("-" * 70)
    
    total = participantes + drivers + okrs + projetos + company_data
    
    print(f"\nTOTAL DE REGISTROS: {total}")
    
    # Verificação
    print("\n" + "="*70)
    
    if participantes >= 5 and drivers >= 5 and okrs >= 5 and projetos >= 5:
        print("  STATUS: OK - TODOS OS DADOS ESTAO PRESENTES!")
        print("="*70 + "\n")
        print("Se nao estao aparecendo na tela:")
        print("  1. Limpe cache do navegador (Ctrl+F5)")
        print("  2. Reinicie o servidor")
        print("  3. Verifique qual plano esta selecionado")
        print("  4. Acesse: http://127.0.0.1:5002/plan/1")
    else:
        print("  AVISO: Alguns dados podem estar faltando")
        print("="*70)
    
    # Listar participantes
    print("\n" + "-"*70)
    print("SEUS PARTICIPANTES:")
    print("-"*70)
    cursor.execute("SELECT id, name, role FROM participants ORDER BY id")
    for pid, name, role in cursor.fetchall():
        print(f"  {pid}. {name} ({role})")
    
    # Listar projetos
    print("\n" + "-"*70)
    print("SEUS PROJETOS:")
    print("-"*70)
    cursor.execute("SELECT id, title, status FROM projects ORDER BY id")
    for pid, title, status in cursor.fetchall():
        print(f"  {pid}. {title} ({status})")
    
    conn.close()
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    verificar()




