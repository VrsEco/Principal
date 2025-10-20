#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.postgres_helper import connect
from config_database import get_db

def test_meetings_route():
    """Testar rota de reunioes"""
    
    company_id = 13
    
    try:
        # Teste 1: list_company_meetings via DatabaseInterface
        print("=== TESTE 1: db.list_company_meetings ===")
        db = get_db()
        meetings = db.list_company_meetings(company_id)
        print(f"Reunioes encontradas via db.list_company_meetings: {len(meetings)}")
        if meetings:
            for m in meetings:
                print(f"  - {m.get('title', 'Sem titulo')}")
        
        # Teste 2: Query direta com ?
        print("\n=== TESTE 2: Query direta com ? ===")
        conn = connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, email, whatsapp 
            FROM employees 
            WHERE company_id = ? 
            ORDER BY name
        ''', (company_id,))
        employees = [dict(row) for row in cursor.fetchall()]
        print(f"Colaboradores encontrados: {len(employees)}")
        
        # Teste 3: Query meeting_agenda_items com ?
        print("\n=== TESTE 3: Query meeting_agenda_items com ? ===")
        cursor.execute('''
            SELECT id, title, description, usage_count
            FROM meeting_agenda_items
            WHERE company_id = ?
            ORDER BY usage_count DESC, title
        ''', (company_id,))
        agenda_items = [dict(row) for row in cursor.fetchall()]
        print(f"Itens de pauta encontrados: {len(agenda_items)}")
        
        # Teste 4: Projetos
        print("\n=== TESTE 4: db.get_company_projects ===")
        projects = db.get_company_projects(company_id)
        print(f"Projetos encontrados: {len(projects)}")
        
        conn.close()
        
        print("\n=== SUCESSO ===")
        print(f"Dados que seriam passados para o template:")
        print(f"  - meetings: {len(meetings)}")
        print(f"  - employees: {len(employees)}")
        print(f"  - agenda_items: {len(agenda_items)}")
        print(f"  - projects: {len(projects)}")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_meetings_route()
