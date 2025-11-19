#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

def test_page():
    """Testar pagina de reunioes"""
    
    url = "http://127.0.0.1:5002/meetings/company/13/list"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.text)}")
        
        # Verificar se as reunioes estao no HTML
        if "Reunião Semanal Gerencial" in response.text:
            print("SUCESSO: 'Reuniao Semanal Gerencial' encontrada no HTML")
        else:
            print("ERRO: 'Reuniao Semanal Gerencial' NAO encontrada no HTML")
        
        if "Teste Fabiano Reunião 02" in response.text or "Teste Fabiano Reuni" in response.text:
            print("SUCESSO: 'Teste Fabiano Reuniao 02' encontrada no HTML")
        else:
            print("ERRO: 'Teste Fabiano Reuniao 02' NAO encontrada no HTML")
        
        # Verificar se o grid de reunioes esta la
        if 'id="meetings-grid"' in response.text:
            print("SUCESSO: Grid de reunioes encontrado")
        else:
            print("ERRO: Grid de reunioes NAO encontrado")
        
        # Verificar se ha reunioes renderizadas
        if 'class="meeting-card"' in response.text:
            count = response.text.count('class="meeting-card"')
            print(f"SUCESSO: {count} cards de reuniao encontrados no HTML")
        else:
            print("ERRO: Nenhum card de reuniao encontrado no HTML")
        
        # Verificar mensagem de vazio
        if "Nenhuma reunião cadastrada" in response.text or "Nenhuma reuni" in response.text:
            print("AVISO: Mensagem de 'vazio' encontrada")
        
        # Salvar HTML para inspecao
        with open("meetings_page_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("\nHTML salvo em: meetings_page_debug.html")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_page()
