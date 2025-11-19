#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config_database import get_db
import json

def test_api_response():
    """Testar resposta da API"""
    
    try:
        db = get_db()
        meeting = db.get_meeting(3)
        
        print("=== OBJETO MEETING DO BANCO ===")
        print(f"Chaves no dicionario: {meeting.keys()}")
        print(f"\nCampo 'guests' existe? {('guests' in meeting)}")
        print(f"Valor de 'guests': {meeting.get('guests')}")
        
        # Simular jsonify
        print("\n=== SIMULANDO JSONIFY ===")
        json_str = json.dumps({'success': True, 'meeting': meeting}, default=str)
        parsed = json.loads(json_str)
        
        print(f"Chaves em parsed['meeting']: {parsed['meeting'].keys()}")
        print(f"Campo 'guests' existe no JSON? {('guests' in parsed['meeting'])}")
        
        if 'guests' in parsed['meeting']:
            print("SUCESSO: Campo 'guests' esta presente no JSON!")
            print(f"Valor: {parsed['meeting']['guests']}")
        else:
            print("ERRO: Campo 'guests' NAO esta presente no JSON!")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_response()
