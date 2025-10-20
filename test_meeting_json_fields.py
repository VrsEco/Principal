#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config_database import get_db

def test_meeting_json():
    """Testar se os campos JSON estão sendo parseados"""
    
    try:
        db = get_db()
        
        # Buscar reunião ID 3
        print("=== TESTE: get_meeting(3) ===")
        meeting = db.get_meeting(3)
        
        if meeting:
            print(f"\nReuniao encontrada: {meeting.get('title')}")
            print(f"ID: {meeting.get('id')}")
            print(f"Status: {meeting.get('status')}")
            
            # Verificar campos JSON parseados
            print("\n--- Campos JSON parseados ---")
            print(f"guests (tipo: {type(meeting.get('guests'))}): {meeting.get('guests')}")
            print(f"agenda (tipo: {type(meeting.get('agenda'))}): {meeting.get('agenda')}")
            print(f"participants (tipo: {type(meeting.get('participants'))}): {meeting.get('participants')}")
            print(f"discussions (tipo: {type(meeting.get('discussions'))}): {meeting.get('discussions')}")
            print(f"activities (tipo: {type(meeting.get('activities'))}): {meeting.get('activities')}")
            
            # Verificar campos JSON originais
            print("\n--- Campos JSON originais ---")
            print(f"guests_json existe? {('guests_json' in meeting)}")
            print(f"agenda_json existe? {('agenda_json' in meeting)}")
            
            print("\n=== SUCESSO ===")
            if meeting.get('guests') is not None:
                print("Os campos JSON estao sendo parseados corretamente!")
            else:
                print("AVISO: Os campos JSON estao None (pode ser normal se nao houver dados)")
        else:
            print("ERRO: Reuniao nao encontrada")
        
        # Testar list_company_meetings
        print("\n\n=== TESTE: list_company_meetings(13) ===")
        meetings = db.list_company_meetings(13)
        print(f"Total de reunioes: {len(meetings)}")
        
        if meetings:
            first = meetings[0]
            print(f"\nPrimeira reuniao: {first.get('title')}")
            print(f"Campo 'guests' existe? {('guests' in first)}")
            print(f"Campo 'guests' tipo: {type(first.get('guests'))}")
            
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_meeting_json()
