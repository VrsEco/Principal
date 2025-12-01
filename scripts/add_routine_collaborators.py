#!/usr/bin/env python3
"""
Helper script to populate routine collaborators after a database restore.

Usage:
  python scripts/add_routine_collaborators.py data.json

The JSON file must contain a list of objects like:

[
  {
    "routine_id": 123,
    "employee_id": 45,
    "hours_used": 8.0,
    "notes": "Executor principal"
  }
]

If a record for the same routine+employee already exists, the script updates
the hours and notes instead of inserting a duplicate row.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = int(os.environ.get("POSTGRES_PORT", 5432))
    database = os.environ.get("POSTGRES_DB", "bc_app_versus_03")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
    )


def upsert_collaborator(conn, record: Dict[str, Any]) -> tuple[int, bool]:
    routine_id = record["routine_id"]
    employee_id = record["employee_id"]
    hours_used = float(record.get("hours_used", 0))
    notes = record.get("notes", "")

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id FROM routine_collaborators
            WHERE routine_id = %s AND employee_id = %s
        """,
            (routine_id, employee_id),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE routine_collaborators
                SET hours_used = %s,
                    notes = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (hours_used, notes, existing[0]),
            )
            return existing[0], True

        cursor.execute(
            """
            INSERT INTO routine_collaborators
            (routine_id, employee_id, hours_used, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (routine_id, employee_id, hours_used, notes),
        )

        return cursor.fetchone()[0], False


def load_records(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of records.")
    return data


def main():
    parser = argparse.ArgumentParser(description="Add routine collaborators from JSON.")
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the JSON file containing routine collaborator records.",
    )
    args = parser.parse_args()

    records = load_records(args.file)
    if not records:
        print("No records found in the JSON workload.")
        return

    conn = get_connection()
    inserted = 0
    updated = 0

    try:
        for record in records:
            routine_id = record.get("routine_id")
            employee_id = record.get("employee_id")
            if routine_id is None or employee_id is None:
                print("Skipping record without routine_id/employee_id:", record)
                continue

            collab_id, already = upsert_collaborator(conn, record)
            if already:
                updated += 1
            else:
                inserted += 1

        conn.commit()
    finally:
        conn.close()

    print(f"Processed {len(records)} entries. Inserted/updated: {inserted}.")


if __name__ == "__main__":
    main()
