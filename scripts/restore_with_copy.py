#!/usr/bin/env python3
"""
Restaurar backup usando comandos COPY do PostgreSQL
"""
import sys
import os
import re

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

try:
    from config import Config
    from sqlalchemy import create_engine, text
    from werkzeug.security import generate_password_hash
    print("✅ Módulos OK")
except ImportError as e:
    print(f"❌ Erro módulos: {e}")
    sys.exit(1)

def create_admin():
    """Criar admin se não existir"""
    print("👤 Verificando/criando admin...")
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id FROM users WHERE email = 'versus@gestaoversus.com.br'"))
            if result.fetchone():
                print("✅ Admin já existe")
                return

            password_hash = generate_password_hash('abc123')
            conn.execute(text(f"""
                INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
                VALUES ('versus@gestaoversus.com.br', '{password_hash}', 'Administrador', 'admin', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """))
            conn.commit()
            print("✅ Admin criado: versus@gestaoversus.com.br / abc123")

    except Exception as e:
        print(f"❌ Erro admin: {e}")

def parse_copy_command(copy_text):
    """Parse um comando COPY e retorna dados"""
    lines = copy_text.strip().split('\n')

    # Primeira linha deve ser COPY table_name (columns) FROM stdin;
    if not lines or not lines[0].upper().startswith('COPY '):
        return None, []

    # Extrair nome da tabela e colunas
    copy_match = re.match(r'COPY (\w+)\s*\((.*?)\)\s*FROM stdin;', lines[0], re.IGNORECASE)
    if not copy_match:
        return None, []

    table_name = copy_match.group(1)
    columns = [col.strip() for col in copy_match.group(2).split(',')]

    # Dados começam após a linha COPY e terminam com \.
    data_lines = []
    in_data = False

    for line in lines[1:]:
        line = line.strip()
        if line == '\\.':
            break
        if in_data:
            data_lines.append(line)
        elif line.upper().startswith('COPY '):
            in_data = True

    return table_name, columns, data_lines

def restore_table_copy(table_name, backup_file):
    """Restaurar uma tabela usando COPY"""
    print(f"🔄 Restaurando {table_name}...")

    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    try:
        with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Erro lendo backup: {e}")
        return 0

    # Encontrar o bloco COPY para esta tabela
    copy_pattern = rf'(COPY {table_name} .*?FROM stdin;.*?)\\.'
    match = re.search(copy_pattern, content, re.IGNORECASE | re.DOTALL)

    if not match:
        print(f"⚠️ Nenhum COPY encontrado para {table_name}")
        return 0

    copy_text = match.group(1) + '\\.'
    parsed_table, columns, data_lines = parse_copy_command(copy_text)

    if not parsed_table or parsed_table != table_name:
        print(f"❌ Erro parse COPY para {table_name}")
        return 0

    print(f"📊 {len(data_lines)} linhas de dados encontradas")

    if not data_lines:
        print(f"⚠️ Sem dados para {table_name}")
        return 0

    # Preparar dados para inserção
    restored = 0
    with engine.connect() as conn:
        for line in data_lines[:5]:  # Limitar para teste
            try:
                # Parse dos valores (formato TSV do COPY)
                values = line.split('\t')

                # Criar INSERT baseado nas colunas
                if len(values) == len(columns):
                    placeholders = ', '.join(['%s'] * len(values))
                    columns_str = ', '.join(columns)
                    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

                    conn.execute(text(insert_sql), values)
                    restored += 1
                else:
                    print(f"❌ Colunas mismatch: {len(columns)} vs {len(values)}")

            except Exception as e:
                print(f"❌ Erro insert: {str(e)[:50]}...")

        conn.commit()

    print(f"✅ {restored} registros restaurados para {table_name}")
    return restored

def main():
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Backup não encontrado: {backup_file}")
        return

    print("🚀 Iniciando restauração com COPY...")
    print(f"📂 Backup: {backup_file}")

    # Passo 1: Criar admin
    create_admin()

    # Passo 2: Restaurar tabelas essenciais
    tables_to_restore = ['companies', 'users', 'employees', 'projects']

    total_restored = 0
    for table in tables_to_restore:
        restored = restore_table_copy(table, backup_file)
        total_restored += restored

    print(f"\n📈 TOTAL RESTAURADO: {total_restored} registros")
    print("🎉 Restauração concluída!")

if __name__ == "__main__":
    main()


