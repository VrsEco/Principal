#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database.postgres_helper import connect

def get_create_table_sql(table_name, sqlite_cursor):
    """Obter SQL CREATE TABLE do SQLite e converter para PostgreSQL"""
    
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = sqlite_cursor.fetchall()
    
    if not columns:
        return None
    
    # Construir CREATE TABLE para PostgreSQL
    pg_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    
    col_definitions = []
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        
        # Converter tipos
        pg_type = col_type.upper()
        if 'INT' in pg_type:
            if pk:
                pg_type = 'SERIAL PRIMARY KEY'
            else:
                pg_type = 'INTEGER'
        elif pg_type in ['TEXT', 'VARCHAR', 'CHAR']:
            pg_type = 'TEXT'
        elif pg_type in ['REAL', 'FLOAT', 'DOUBLE']:
            pg_type = 'REAL'
        elif 'BLOB' in pg_type:
            pg_type = 'BYTEA'
        elif 'DATE' in pg_type or 'TIME' in pg_type:
            if 'TIME' in pg_type and 'DATE' not in pg_type:
                pg_type = 'TIME'
            else:
                pg_type = 'TIMESTAMP'
        elif 'BOOL' in pg_type:
            pg_type = 'BOOLEAN'
        
        # Construir definicao da coluna
        col_def = f"    {col_name} {pg_type}"
        
        if not pk:  # PRIMARY KEY ja foi definido em SERIAL
            if not_null:
                col_def += " NOT NULL"
            
            if default_val:
                if default_val.upper() == 'CURRENT_TIMESTAMP':
                    col_def += " DEFAULT CURRENT_TIMESTAMP"
                elif default_val.upper() in ['TRUE', 'FALSE']:
                    col_def += f" DEFAULT {default_val.upper()}"
                elif isinstance(default_val, (int, float)):
                    col_def += f" DEFAULT {default_val}"
                elif isinstance(default_val, str):
                    # Se ja tem aspas, usar direto
                    if default_val.startswith("'") and default_val.endswith("'"):
                        col_def += f" DEFAULT {default_val}"
                    # Se for numero
                    elif default_val.replace('-', '').replace('.', '').isdigit():
                        col_def += f" DEFAULT {default_val}"
                    else:
                        col_def += f" DEFAULT '{default_val}'"
        
        col_definitions.append(col_def)
    
    pg_sql += ",\n".join(col_definitions)
    pg_sql += "\n);"
    
    return pg_sql

def create_missing_tables():
    """Criar todas as tabelas faltantes"""
    
    missing_tables = [
        'ai_agents',
        'okr_global_key_results',
        'okrs',
        'projects',
        'report_instances',
        'routine_tasks',
        'routine_triggers'
    ]
    
    sqlite_conn = sqlite3.connect('instance/pevapp22.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    pg_conn = connect()
    pg_cursor = pg_conn.cursor()
    
    print("=== CRIANDO TABELAS FALTANTES ===\n")
    
    for table_name in missing_tables:
        try:
            print(f"Criando tabela '{table_name}'...")
            
            # Obter estrutura
            create_sql = get_create_table_sql(table_name, sqlite_cursor)
            
            if create_sql:
                print(f"  SQL: {create_sql[:100]}...")
                
                # Criar no PostgreSQL
                pg_cursor.execute(create_sql)
                pg_conn.commit()
                
                # Verificar se tem dados para migrar
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = sqlite_cursor.fetchone()[0]
                
                if count > 0:
                    print(f"  Registros no SQLite: {count}")
                    
                    # Migrar dados
                    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
                    rows = sqlite_cursor.fetchall()
                    
                    # Obter nomes das colunas
                    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
                    cols_info = sqlite_cursor.fetchall()
                    col_names = [c[1] for c in cols_info if c[1] != 'id']  # Excluir id (auto-increment)
                    
                    # Inserir dados
                    placeholders = ", ".join(["%s"] * len(col_names))
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders})"
                    
                    for row in rows:
                        # Pular primeiro campo se for id
                        if cols_info[0][1] == 'id':
                            row_data = row[1:]
                        else:
                            row_data = row
                        
                        pg_cursor.execute(insert_sql, row_data)
                    
                    pg_conn.commit()
                    print(f"  Migrados {count} registros")
                else:
                    print(f"  Tabela vazia")
                
                print(f"  OK\n")
            else:
                print(f"  ERRO: Nao foi possivel obter estrutura\n")
                
        except Exception as e:
            print(f"  ERRO: {e}\n")
            pg_conn.rollback()
    
    sqlite_cursor.close()
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close()
    
    print("=== CONCLUIDO ===")

if __name__ == "__main__":
    create_missing_tables()
