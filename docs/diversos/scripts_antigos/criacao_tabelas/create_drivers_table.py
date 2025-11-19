#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.postgres_helper import connect

def create_drivers_table():
    """Criar tabela drivers no PostgreSQL"""
    
    try:
        conn = connect()
        cursor = conn.cursor()
        
        print("=== CRIANDO TABELA DRIVERS ===")
        
        # Criar tabela
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id SERIAL PRIMARY KEY,
                plan_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT,
                priority TEXT,
                owner TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("Tabela 'drivers' criada com sucesso!")
        
        # Verificar
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'drivers' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print(f"\nColunas criadas ({len(columns)}):")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        cursor.close()
        conn.close()
        
        print("\n=== SUCESSO ===")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_drivers_table()
