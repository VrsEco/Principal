import requests
import json
import pytest

def test_api_v2_chat_contract():
    """
    Teste de Caixa Preta: Valida o contrato da API v2 Chat e a integração com o RAG.
    O servidor deve estar rodando na porta 5010.
    """
    url = "http://localhost:5010/api/v2/chat"
    payload = {
        "message": "Qual a regra para notas de 15k?",
        "thread_id": "client-app-test-01"
    }
    headers = {'Content-Type': 'application/json'}

    print(f"\nTestando POST {url}...")
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        
        # 1. Validação de Status Code
        assert response.status_code == 200, f"Status esperado 200, recebido {response.status_code}"
        
        data = response.json()
        print(f"Resposta recebida: {data}")

        # 2. Validação de Chaves no JSON
        assert "response" in data, "Chave 'response' ausente na resposta"
        assert "thread_id" in data, "Chave 'thread_id' ausente na resposta"
        assert data["thread_id"] == payload["thread_id"], "Thread ID retornado é diferente do enviado"

        # 3. Validação de Conteúdo (Garante que o RAG funcionou)
        # Notas fiscais > 10.000 (15k) devem mencionar "aprovação"
        response_text = data["response"].lower()
        assert "aprovação" in response_text or "aprovacao" in response_text, \
            f"A resposta deveria conter a regra de aprovação. Recebido: {response_text}"

        print("\n[SUCESSO] Teste de contrato da API concluído com êxito!")

    except requests.exceptions.ConnectionError:
        pytest.skip("Servidor da API v2 não está ativo na porta 5010 durante esta execução.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        pytest.fail(f"Erro inesperado no teste: {str(e)}")

if __name__ == "__main__":
    test_api_v2_chat_contract()
