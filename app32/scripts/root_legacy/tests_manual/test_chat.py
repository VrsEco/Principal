import requests
import json

url = "http://127.0.0.1:5010/api/v2/chat"
payload = {
    "message": "Quais empresas temos cadastradas?",
    "thread_id": "test_user_001"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    
    data = response.json()
    
    # Salvar em arquivo
    with open("test_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nResposta salva em test_response.json")
    
    if response.status_code == 200:
        print(f"\n=== RESPOSTA DO AGENTE ===")
        print(data.get('response', 'Sem resposta'))
        print(f"\n=== THREAD ID ===")
        print(data.get('thread_id', 'N/A'))
except Exception as e:
    print(f"Error: {e}")
