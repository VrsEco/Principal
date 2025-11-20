#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.postgres_helper import connect
import json


def check_meeting():
    """Verificar dados especificos da reuniao"""

    try:
        conn = connect()
        cursor = conn.cursor()

        # Buscar reuniao especifica
        print("=== REUNIAO: Reuniao Semanal Gerencial ===")
        cursor.execute(
            """
            SELECT * FROM meetings 
            WHERE title = %s 
            AND scheduled_date = %s
        """,
            ("Reunião Semanal Gerencial", "2025-10-14"),
        )

        meeting = cursor.fetchone()

        if meeting:
            meeting_dict = dict(meeting)
            print(f"\nID: {meeting_dict.get('id')}")
            print(f"Titulo: {meeting_dict.get('title')}")
            print(f"Empresa ID: {meeting_dict.get('company_id')}")
            print(f"Data Agendada: {meeting_dict.get('scheduled_date')}")
            print(f"Hora Agendada: {meeting_dict.get('scheduled_time')}")
            print(f"Status: {meeting_dict.get('status')}")
            print(f"Projeto ID: {meeting_dict.get('project_id')}")

            # Verificar campos JSON
            print("\n--- CAMPOS JSON (conteudo) ---")

            json_fields = [
                "guests_json",
                "agenda_json",
                "participants_json",
                "discussions_json",
                "activities_json",
            ]

            for field in json_fields:
                value = meeting_dict.get(field)
                if value:
                    try:
                        parsed = json.loads(value) if isinstance(value, str) else value
                        print(f"\n{field}:")

                        if field == "guests_json":
                            internal = parsed.get("internal", [])
                            external = parsed.get("external", [])
                            print(f"  Convidados internos: {len(internal)}")
                            for guest in internal:
                                print(
                                    f"    - {guest.get('name', 'Sem nome')} (ID: {guest.get('id')})"
                                )
                            print(f"  Convidados externos: {len(external)}")

                        elif field == "agenda_json":
                            print(f"  Total de itens: {len(parsed)}")
                            for item in parsed:
                                print(f"    - {item.get('title', 'Sem titulo')}")

                        elif field == "participants_json":
                            internal = parsed.get("internal", [])
                            external = parsed.get("external", [])
                            print(f"  Participantes internos: {len(internal)}")
                            for p in internal:
                                print(f"    - {p.get('name', 'Sem nome')}")
                            print(f"  Participantes externos: {len(external)}")

                        elif field == "discussions_json":
                            print(f"  Total de discussoes: {len(parsed)}")
                            for disc in parsed:
                                title = disc.get("title", "Sem titulo")
                                discussion = disc.get("discussion", "")
                                print(f"    - {title}")
                                print(f"      Tamanho: {len(discussion)} caracteres")

                        elif field == "activities_json":
                            print(f"  Total de atividades: {len(parsed)}")
                            for act in parsed:
                                print(f"    - {act.get('title', 'Sem titulo')}")
                                print(
                                    f"      Responsavel: {act.get('responsible', 'Nao definido')}"
                                )
                                print(
                                    f"      Prazo: {act.get('deadline', 'Sem prazo')}"
                                )

                    except Exception as e:
                        print(f"  ERRO ao parsear: {e}")
                else:
                    print(f"\n{field}: (vazio)")

            print("\n=== RESUMO ===")
            print("SUCESSO: Todos os dados da reuniao estao no PostgreSQL!")

        else:
            print("\nERRO: Reuniao nao encontrada no PostgreSQL!")

            # Verificar se existe com titulo similar
            cursor.execute(
                """
                SELECT id, title, scheduled_date, status 
                FROM meetings 
                WHERE title LIKE %s
            """,
                ("%Semanal%",),
            )

            similar = cursor.fetchall()
            if similar:
                print("\nReunioes similares encontradas:")
                for row in similar:
                    row_dict = dict(row)
                    print(
                        f"  ID {row_dict['id']}: {row_dict['title']} - {row_dict['scheduled_date']}"
                    )

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_meeting()
