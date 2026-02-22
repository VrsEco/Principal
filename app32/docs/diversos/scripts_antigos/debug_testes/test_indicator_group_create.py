#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json as json_lib


def test_create_group():
    """Testar criacao de grupo de indicadores"""

    company_id = 13
    url = f"http://127.0.0.1:5002/grv/api/company/{company_id}/indicator-groups"

    # Dados do grupo
    data = {
        "name": "Teste Grupo Indicador",
        "description": "Grupo de teste para migração PostgreSQL",
        "parent_id": None,
    }

    try:
        print(f"=== TESTANDO POST: {url} ===\n")
        print(f"Dados a enviar: {json_lib.dumps(data, indent=2)}")

        response = requests.post(url, json=data)
        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nSuccess: {result.get('success')}")

            if result.get("success"):
                created_data = result.get("data", {})
                print(f"\nGrupo criado:")
                print(f"  ID: {created_data.get('id')}")
                print(f"  Codigo: {created_data.get('code')}")
                print(f"  Nome: {created_data.get('name')}")
                print(f"  Descricao: {created_data.get('description')}")

                print("\n=== SUCESSO ===")

                # Limpar - deletar grupo criado
                group_id = created_data.get("id")
                if group_id:
                    delete_url = f"{url}/{group_id}"
                    print(f"\nLimpando - deletando grupo ID {group_id}...")
                    delete_response = requests.delete(delete_url)
                    if delete_response.status_code == 200:
                        print("Grupo deletado com sucesso")
            else:
                print(f"\nERRO: {result.get('message')}")
        else:
            print(f"\nERRO HTTP: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"\nErro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import time

    print("Aguardando servidor iniciar...")
    time.sleep(4)
    test_create_group()
