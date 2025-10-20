#!/usr/bin/env python3

import sys
sys.path.append('.')
from database.sqlite_db import SQLiteDatabase
import json

def test_retrieve_discussions():
    db = SQLiteDatabase()
    
    print("=== TESTE DE RECUPERAÇÃO DE DISCUSSÕES ===")
    
    plan_id = 1
    
    # Testar recuperação exata como na função plan_okr_global
    workshop_discussions = ''
    workshop_status = db.get_section_status(int(plan_id), 'workshop-final-okr')
    print(f"Status workshop encontrado: {workshop_status is not None}")
    
    if workshop_status and workshop_status.get('notes'):
        print(f"Notes encontradas: {workshop_status.get('notes')}")
        try:
            workshop_data = json.loads(workshop_status['notes'])
            print(f"Dados workshop carregados: {workshop_data}")
            workshop_discussions = workshop_data.get('discussions', '') if isinstance(workshop_data, dict) else ''
            print(f"Discussões workshop recuperadas: '{workshop_discussions}'")
        except Exception as e:
            print(f'Erro na recuperação workshop: {e}')
            workshop_discussions = ''

    approval_discussions = ''
    approvals_status = db.get_section_status(int(plan_id), 'okr-approvals')
    print(f"Status approval encontrado: {approvals_status is not None}")
    
    if approvals_status and approvals_status.get('notes'):
        print(f"Notes approval encontradas: {approvals_status.get('notes')}")
        try:
            approvals_data = json.loads(approvals_status['notes'])
            print(f"Dados approval carregados: {approvals_data}")
            approval_discussions = approvals_data.get('discussions', '') if isinstance(approvals_data, dict) else ''
            print(f"Discussões approval recuperadas: '{approval_discussions}'")
        except Exception as e:
            print(f'Erro na recuperação approval: {e}')
            approval_discussions = ''
    
    print(f"\nRESULTADO FINAL:")
    print(f"Workshop discussions: '{workshop_discussions}'")
    print(f"Approval discussions: '{approval_discussions}'")

if __name__ == '__main__':
    test_retrieve_discussions()
