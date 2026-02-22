import sqlite3
import json

conn = sqlite3.connect("pevapp22.db")
cursor = conn.cursor()

# Buscar registros relacionados a OKR
cursor.execute(
    "SELECT plan_id, section_name, notes FROM plan_sections WHERE section_name LIKE '%okr%'"
)
records = cursor.fetchall()

print("Registros de OKR encontrados:")
for record in records:
    plan_id, section_name, notes = record
    print(
        f"Plan {plan_id}, Section: {section_name}, Notes length: {len(notes) if notes else 0}"
    )

    if notes:
        try:
            notes_data = json.loads(notes)
            if isinstance(notes_data, dict):
                if "okrs" in notes_data:
                    print(f"  OKRs count: {len(notes_data['okrs'])}")
                    for i, okr in enumerate(notes_data["okrs"]):
                        print(f"    OKR {i+1}: {okr.get('objective', 'N/A')}")
                elif "analyses" in notes_data:
                    print(f"  Analyses count: {len(notes_data['analyses'])}")
        except Exception as e:
            print(f"  Error parsing notes: {e}")

conn.close()
