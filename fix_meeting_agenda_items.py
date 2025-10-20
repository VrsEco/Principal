#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database.postgres_helper import connect

def get_table_structure():
    """Obter estrutura da tabela meeting_agenda_items do SQLite"""
    
    print("=== ESTRUTURA DA TABELA meeting_agenda_items ===")
    
    try:
        sqlite_conn = sqlite3.connect('instance/pevapp22.db')
        sqlite_cursor = sqlite_conn.cursor()
        
        # Obter estrutura da tabela
        sqlite_cursor.execute("PRAGMA table_info(meeting_agenda_items)")
        columns = sqlite_cursor.fetchall()
        
        print("Colunas:")
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'} {'DEFAULT ' + str(col[4]) if col[4] else ''}")
        
        # Obter dados da tabela
        sqlite_cursor.execute("SELECT COUNT(*) FROM meeting_agenda_items")
        count = sqlite_cursor.fetchone()[0]
        print(f"\nRegistros: {count}")
        
        if count > 0:
            sqlite_cursor.execute("SELECT * FROM meeting_agenda_items LIMIT 3")
            rows = sqlite_cursor.fetchall()
            print("\nPrimeiros registros:")
            for row in rows:
                print(f"  {row}")
        
        sqlite_conn.close()
        
        return columns
        
    except Exception as e:
        print(f"Erro: {e}")
        return None

def create_table_in_postgresql(columns):
    """Criar tabela meeting_agenda_items no PostgreSQL"""
    
    print("\n=== CRIANDO TABELA NO POSTGRESQL ===")
    
    try:
        pg_conn = connect()
        pg_cursor = pg_conn.cursor()
        
        # Construir CREATE TABLE
        create_sql = "CREATE TABLE meeting_agenda_items (\n"
        
        for i, col in enumerate(columns):
            col_name = col[1]
            col_type = col[2]
            not_null = "NOT NULL" if col[3] else ""
            default = f"DEFAULT {col[4]}" if col[4] else ""
            
            # Converter tipos SQLite para PostgreSQL
            if col_type.upper() == "INTEGER":
                col_type = "INTEGER"
            elif col_type.upper() == "TEXT":
                col_type = "TEXT"
            elif col_type.upper() == "REAL":
                col_type = "REAL"
            
            create_sql += f"    {col_name} {col_type} {not_null} {default}"
            if i < len(columns) - 1:
                create_sql += ","
            create_sql += "\n"
        
        create_sql += ");"
        
        print("SQL CREATE TABLE:")
        print(create_sql)
        
        # Executar CREATE TABLE
        pg_cursor.execute(create_sql)
        pg_conn.commit()
        
        print("Tabela criada com sucesso!")
        
        pg_cursor.close()
        pg_conn.close()
        
    except Exception as e:
        print(f"Erro ao criar tabela: {e}")

def migrate_data():
    """Migrar dados da tabela meeting_agenda_items"""
    
    print("\n=== MIGRANDO DADOS ===")
    
    try:
        # Conectar SQLite
        sqlite_conn = sqlite3.connect('instance/pevapp22.db')
        sqlite_cursor = sqlite_conn.cursor()
        
        # Conectar PostgreSQL
        pg_conn = connect()
        pg_cursor = pg_conn.cursor()
        
        # Obter dados do SQLite
        sqlite_cursor.execute("SELECT * FROM meeting_agenda_items")
        rows = sqlite_cursor.fetchall()
        
        print(f"Migrando {len(rows)} registros...")
        
        # Inserir no PostgreSQL
        for row in rows:
            placeholders = ", ".join(["%s"] * len(row))
            insert_sql = f"INSERT INTO meeting_agenda_items VALUES ({placeholders})"
            pg_cursor.execute(insert_sql, row)
        
        pg_conn.commit()
        print(f"Migrados {len(rows)} registros com sucesso!")
        
        sqlite_cursor.close()
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()
        
    except Exception as e:
        print(f"Erro na migração: {e}")

if __name__ == "__main__":
    # Obter estrutura
    columns = get_table_structure()
    
    if columns:
        # Criar tabela
        create_table_in_postgresql(columns)
        
        # Migrar dados
        migrate_data()
