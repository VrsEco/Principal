#!/usr/bin/env python3

import sys

sys.path.append(".")
from config_database import get_db
import json


def test_save_discussions():
    db = get_db()

    print("=== TESTE DE SALVAMENTO DE DISCUSSÕES ===")

    # Testar salvamento de workshop discussions
    plan_id = 1
    section_name = "workshop-final-okr"
    test_discussions = "TESTE: Discussões do workshop - " + str(datetime.now())

    print(f"Tentando salvar: '{test_discussions}'")

    # Simular exatamente o que a função save_workshop_discussions faz
    existing_status = db.get_section_status(int(plan_id), section_name)
    existing_data = {}

    if existing_status and existing_status.get("notes"):
        try:
            existing_data = json.loads(existing_status["notes"])
            print(f"Dados existentes encontrados: {existing_data}")
        except:
            existing_data = {}
            print("Erro ao carregar dados existentes, usando dados vazios")

    # Add discussions to existing data
    existing_data["discussions"] = test_discussions
    print(f"Dados a serem salvos: {existing_data}")

    # Save updated data
    result = db.update_section_consultant_notes(
        int(plan_id), section_name, json.dumps(existing_data)
    )
    print(f"Resultado do salvamento: {result}")

    # Verificar se foi salvo
    status_after = db.get_section_status(int(plan_id), section_name)
    if status_after and status_after.get("notes"):
        try:
            saved_data = json.loads(status_after["notes"])
            saved_discussions = saved_data.get("discussions", "")
            print(f"Discussões salvas verificadas: '{saved_discussions}'")
            print(f"Salvamento funcionou: {saved_discussions == test_discussions}")
        except Exception as e:
            print(f"Erro ao verificar dados salvos: {e}")
    else:
        print("Nenhum dado encontrado após salvamento")


if __name__ == "__main__":
    from datetime import datetime

    test_save_discussions()
