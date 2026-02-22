#!/usr/bin/env python3
"""
Importação inteligente de dados do backup para o banco atual
"""
import sys
import os
import re

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from config import Config
from sqlalchemy import create_engine, text

def extract_copy_data(content, table_name):
    """Extrair dados de um bloco COPY específico"""
    # Procurar pelo bloco COPY da tabela
    copy_pattern = rf'COPY (?:public\.)?{table_name}\s*\((.*?)\)\s*FROM stdin;(.*?)(?=COPY|\Z)'
    match = re.search(copy_pattern, content, re.IGNORECASE | re.DOTALL)

    if not match:
        return None, []

    columns_str, data_block = match.groups()
    columns = [col.strip() for col in columns_str.split(',')]

    # Extrair linhas de dados (até encontrar \.)
    data_lines = []
    in_data = True

    for line in data_block.split('\n'):
        line = line.strip()
        if line == '\\.' or not line:
            break
        if line and in_data:
            data_lines.append(line)

    return columns, data_lines

def get_table_columns(engine, table_name):
    """Obter colunas da tabela no banco atual"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}' AND table_schema = 'public'
                ORDER BY ordinal_position
            """))
            return {row[0]: row[1] for row in result.fetchall()}
    except:
        return {}

def import_table_data(engine, table_name, columns, data_lines):
    """Importar dados para uma tabela específica"""
    print(f"🔄 Importando {table_name}...")

    # Obter estrutura da tabela atual
    current_columns = get_table_columns(engine, table_name)
    if not current_columns:
        print(f"❌ Tabela {table_name} não encontrada no banco")
        return 0

    # Verificar compatibilidade de colunas
    compatible_columns = []
    for col in columns:
        if col in current_columns:
            compatible_columns.append(col)
        else:
            print(f"⚠️ Coluna {col} não existe na tabela atual")

    if not compatible_columns:
        print(f"❌ Nenhuma coluna compatível para {table_name}")
        return 0

    print(f"📋 Colunas compatíveis: {', '.join(compatible_columns)}")

    imported = 0
    errors = 0

    with engine.connect() as conn:
        for line in data_lines:
            try:
                # Parse dos valores (TSV)
                values = line.split('\t')

                if len(values) != len(columns):
                    errors += 1
                    continue

                # Mapear valores para colunas compatíveis
                insert_values = []
                insert_columns = []

                for i, col in enumerate(columns):
                    if col in compatible_columns:
                        value = values[i]
                        # Tratar valores especiais
                        if value == '\\N':  # NULL
                            value = None
                        elif current_columns[col] in ['timestamp', 'date'] and value:
                            # PostgreSQL timestamps
                            if value.startswith('2025-'):
                                pass  # manter como string
                        insert_columns.append(col)
                        insert_values.append(value)

                if insert_columns:
                    # Verificar se registro já existe (por ID se disponível)
                    where_clause = ""
                    if 'id' in insert_columns:
                        id_value = insert_values[insert_columns.index('id')]
                        if id_value and id_value != 'NULL':
                            where_clause = f"WHERE id = {id_value}"

                    # Se não existe where clause, tentar INSERT direto (pode falhar por duplicata)
                    if not where_clause:
                        placeholders = ', '.join(['%s'] * len(insert_values))
                        cols_str = ', '.join(insert_columns)
                        sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
                        conn.execute(text(sql), insert_values)
                        imported += 1
                    else:
                        # Verificar se já existe
                        exists_result = conn.execute(text(f"SELECT 1 FROM {table_name} {where_clause}"))
                        if not exists_result.fetchone():
                            placeholders = ', '.join(['%s'] * len(insert_values))
                            cols_str = ', '.join(insert_columns)
                            sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
                            conn.execute(text(sql), insert_values)
                            imported += 1
                        else:
                            print(f"⚠️ Registro já existe em {table_name} {where_clause}")

            except Exception as e:
                errors += 1
                if errors <= 3:  # Mostrar apenas primeiros erros
                    print(f"❌ Erro linha {imported+errors}: {str(e)[:50]}...")

        conn.commit()

    print(f"✅ {imported} registros importados, {errors} erros para {table_name}")
    return imported

def main():
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Arquivo não encontrado: {backup_file}")
        return

    print("🚀 IMPORTAÇÃO INTELIGENTE DE DADOS")
    print("=" * 50)
    print(f"📂 Backup: {backup_file}")
    print()

    # Ler backup
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Encontrar tabelas no backup
    copy_pattern = r'COPY (?:public\.)?(\w+)\s*\((.*?)\)\s*FROM stdin;'
    copy_matches = re.findall(copy_pattern, content, re.IGNORECASE | re.DOTALL)

    # Conectar ao banco
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    # Obter tabelas existentes
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        existing_tables = {row[0] for row in result.fetchall()}

    print(f"📊 Tabelas no backup: {len(copy_matches)}")
    print(f"🏗️  Tabelas no banco atual: {len(existing_tables)}")
    print()

    # Importar tabelas compatíveis
    total_imported = 0
    tables_processed = 0

    # Priorizar tabelas essenciais
    priority_tables = ['users', 'companies', 'employees', 'projects', 'plans']
    other_tables = []

    for table_name, _ in copy_matches:
        if table_name in priority_tables:
            continue
        other_tables.append(table_name)

    # Processar na ordem: prioridade + outras
    tables_to_process = [(t, True) for t in priority_tables if t in [m[0] for m in copy_matches]]
    tables_to_process.extend([(t, False) for t in other_tables])

    for table_name, is_priority in tables_to_process:
        if table_name not in existing_tables:
            continue

        print(f"\n{'⭐' if is_priority else '📋'} Processando: {table_name}")

        # Extrair dados
        columns, data_lines = extract_copy_data(content, table_name)

        if not columns or not data_lines:
            print(f"⚠️ Sem dados para {table_name}")
            continue

        # Importar
        imported = import_table_data(engine, table_name, columns, data_lines)
        total_imported += imported
        tables_processed += 1

        print(f"📈 Progresso: {tables_processed}/{len([t for t, _ in tables_to_process])} tabelas")

    print(f"\n🎉 IMPORTAÇÃO CONCLUÍDA!")
    print(f"📊 Total de registros importados: {total_imported}")
    print(f"🏗️  Tabelas processadas: {tables_processed}")

if __name__ == "__main__":
    main()














