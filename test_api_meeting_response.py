#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_api():
    """Testar API que retorna dados da reuniao"""
    
    meeting_id = 3
    url = f"http://127.0.0.1:5002/meetings/api/meeting/{meeting_id}"
    
    try:
        print(f"=== TESTANDO API: {url} ===\n")
        
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nSuccess: {data.get('success')}")
            
            if data.get('success'):
                meeting = data.get('meeting', {})
                
                print(f"\n--- DADOS BASICOS ---")
                print(f"ID: {meeting.get('id')}")
                print(f"Titulo: {meeting.get('title')}")
                print(f"Data: {meeting.get('scheduled_date')}")
                print(f"Hora: {meeting.get('scheduled_time')}")
                print(f"Status: {meeting.get('status')}")
                
                print(f"\n--- CAMPOS PARSEADOS (que o JS espera) ---")
                
                # Verificar se os campos parseados existem
                campos_esperados = ['guests', 'agenda', 'participants', 'discussions', 'activities']
                
                for campo in campos_esperados:
                    existe = campo in meeting
                    valor = meeting.get(campo)
                    tipo = type(valor).__name__
                    
                    print(f"{campo}:")
                    print(f"  Existe? {existe}")
                    print(f"  Tipo: {tipo}")
                    
                    if valor:
                        if isinstance(valor, dict):
                            print(f"  Conteudo: {len(valor)} chaves")
                            print(f"  Chaves: {list(valor.keys())}")
                        elif isinstance(valor, list):
                            print(f"  Conteudo: {len(valor)} itens")
                            if len(valor) > 0:
                                print(f"  Primeiro item: {valor[0]}")
                        else:
                            print(f"  Conteudo: {valor}")
                    else:
                        print(f"  Conteudo: None ou vazio")
                    print()
                
                # Verificar campos _json
                print(f"\n--- CAMPOS JSON BRUTOS (nao parseados) ---")
                json_fields = ['guests_json', 'agenda_json', 'participants_json', 'discussions_json', 'activities_json']
                
                for campo in json_fields:
                    existe = campo in meeting
                    print(f"{campo}: {'Existe' if existe else 'NAO existe'}")
                
                # Mostrar JSON completo
                print(f"\n--- JSON COMPLETO (resumo) ---")
                print(f"Total de chaves: {len(meeting.keys())}")
                print(f"Chaves disponiveis: {list(meeting.keys())}")
                
            else:
                print(f"ERRO: {data.get('message')}")
        else:
            print(f"ERRO HTTP: {response.status_code}")
            print(response.text)
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()
