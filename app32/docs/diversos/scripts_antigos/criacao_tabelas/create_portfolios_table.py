# -*- coding: utf-8 -*-
"""
Script para criar a tabela de portfolios
"""
import sqlite3

conn = sqlite3.connect("instance/pevapp22.db")
cursor = conn.cursor()

# Criar tabela de portfolios
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        responsible_id INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (responsible_id) REFERENCES employees(id)
    )
"""
)

conn.commit()
conn.close()

print("✅ Tabela 'portfolios' criada com sucesso!")
print("\nEstrutura:")
print("  - id (INTEGER PRIMARY KEY)")
print("  - company_id (INTEGER NOT NULL)")
print("  - code (TEXT NOT NULL)")
print("  - name (TEXT NOT NULL)")
print("  - responsible_id (INTEGER)")
print("  - notes (TEXT)")
print("  - created_at (TIMESTAMP)")
print("  - updated_at (TIMESTAMP)")
