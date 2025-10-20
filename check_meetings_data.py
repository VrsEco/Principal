#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.postgres_helper import connect
import json

def check_meetings():
    """Verificar dados de reunioes"""
    
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Verificar reunioes da empresa 13
        print("=== REUNIOES DA EMPRESA 13 ===")
        cursor.execute("SELECT * FROM meetings WHERE company_id = 13")
        meetings = cursor.fetchall()
        
        print(f"Total de reunioes encontradas: {len(meetings)}")
        
        if meetings:
            print("\nDetalhes das reunioes:")
            for meeting in meetings:
                meeting_dict = dict(meeting)
                print(f"\n  ID: {meeting_dict.get('id')}")
                print(f"  Titulo: {meeting_dict.get('title')}")
                print(f"  Data Agendada: {meeting_dict.get('scheduled_date')}")
                print(f"  Data Real: {meeting_dict.get('actual_date')}")
                print(f"  Status: {meeting_dict.get('status')}")
                print(f"  Project ID: {meeting_dict.get('project_id')}")
        
        # Verificar todas as reunioes
        print("\n\n=== TODAS AS REUNIOES NO SISTEMA ===")
        cursor.execute("SELECT id, company_id, title, scheduled_date, status FROM meetings ORDER BY company_id, id")
        all_meetings = cursor.fetchall()
        
        print(f"Total geral: {len(all_meetings)}")
        for meeting in all_meetings:
            meeting_dict = dict(meeting)
            print(f"  ID: {meeting_dict.get('id')}, Company: {meeting_dict.get('company_id')}, Titulo: {meeting_dict.get('title')}")
        
        # Verificar estrutura da tabela
        print("\n\n=== ESTRUTURA DA TABELA MEETINGS ===")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'meetings'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        for col in columns:
            col_dict = dict(col)
            print(f"  {col_dict.get('column_name')}: {col_dict.get('data_type')} {'NULL' if col_dict.get('is_nullable') == 'YES' else 'NOT NULL'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_meetings()
