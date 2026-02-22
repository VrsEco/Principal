#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config_database import get_db
import json as json_lib


def test_dict():
    """Testar conversao dict"""

    try:
        db = get_db()
        meeting = db.get_meeting(3)

        print("=== TESTE CONVERSAO DICT ===\n")
        print(f"Tipo do objeto: {type(meeting)}")
        print(f"E um dict? {isinstance(meeting, dict)}")

        print(f"\n--- Chaves no dicionario ---")
        if meeting:
            keys = list(meeting.keys())
            print(f"Total: {len(keys)}")

            print("\nChaves _json:")
            for key in keys:
                if "_json" in key:
                    print(f"  - {key}")

            print("\nChaves parseadas:")
            for key in [
                "guests",
                "agenda",
                "participants",
                "discussions",
                "activities",
            ]:
                existe = key in meeting
                print(f"  - {key}: {'EXISTE' if existe else 'NAO existe'}")
                if existe:
                    print(f"    Tipo: {type(meeting[key])}")
                    print(f"    Valor: {meeting[key]}")

        # Testar jsonify
        print("\n--- TESTE JSON.DUMPS ---")
        json_str = json_lib.dumps(meeting, default=str)
        parsed = json_lib.loads(json_str)

        print(f"Campos parseados no JSON final:")
        for key in ["guests", "agenda", "participants", "discussions", "activities"]:
            existe = key in parsed
            print(f"  - {key}: {'EXISTE' if existe else 'NAO existe'}")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_dict()
