"""
Testar API de estruturas diretamente
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5003"
PLAN_ID = 45

# Dados de teste mínimos
test_data = {
    "area": "comercial",
    "block": "processos",
    "item_type": "Aquisição",
    "description": "Teste de estrutura",
    "value": "R$ 1.000,00",
    "repetition": "Única",
    "payment_form": "À vista",
    "status": "pending",
    "installments": [],
}

print("\n🧪 Testando API de Estruturas")
print("=" * 60)
print(f"URL: {BASE_URL}/api/implantacao/{PLAN_ID}/structures")
print(f"Dados: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
print("=" * 60)

try:
    response = requests.post(
        f"{BASE_URL}/api/implantacao/{PLAN_ID}/structures", json=test_data, timeout=10
    )

    print(f"\n📡 Status Code: {response.status_code}")
    print(f"📥 Headers: {dict(response.headers)}")

    try:
        result = response.json()
        print(f"\n✅ Response JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result.get("success"):
            print(f"\n🎉 SUCESSO! ID criado: {result.get('id')}")
        else:
            print(f"\n❌ ERRO: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Erro ao parsear JSON: {e}")
        print(f"\n📄 Response Text:")
        print(response.text[:500])

except requests.exceptions.ConnectionError:
    print("\n❌ ERRO: Não foi possível conectar ao servidor")
    print("   Verifique se o Docker está rodando:")
    print("   docker ps | findstr gestaoversus_app_dev")

except Exception as e:
    print(f"\n❌ ERRO: {e}")

print("\n" + "=" * 60)
