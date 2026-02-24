
import psycopg2
from psycopg2 import sql

def get_schema(db_name):
    conn = psycopg2.connect(
        dbname=db_name,
        user='postgres',
        password='*Paraiso1978',
        host='localhost',
        port='5432'
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        ORDER BY table_name, column_name;
    """)
    schema = {}
    for table, column, dtype in cur.fetchall():
        if table not in schema:
            schema[table] = {}
        schema[table][column] = dtype
    cur.close()
    conn.close()
    return schema

def compare():
    print("Capturando schema do APP31 (Temp)...")
    app31 = get_schema('bd_app31_temp')
    print("Capturando schema do APP32 (Oficial)...")
    app32 = get_schema('bdversusv2')

    all_tables = set(app31.keys()) | set(app32.keys())
    
    report = []
    report.append("=== RELATÓRIO DE COMPARAÇÃO DE BANCO DE DADOS (APP31 vs APP32) ===")
    
    for table in sorted(all_tables):
        if table not in app31:
            report.append(f"\n[TABELA NOVA] {table} (Existe apenas no APP32)")
            continue
        if table not in app32:
            report.append(f"\n[TABELA REMOVIDA/RENOMEADA] {table} (Existe apenas no APP31)")
            continue
            
        report.append(f"\n[TABELA] {table}")
        cols31 = app31[table]
        cols32 = app32[table]
        
        # Colunas novas no APP32
        new_cols = set(cols32.keys()) - set(cols31.keys())
        for c in sorted(new_cols):
            report.append(f"  + [COLUNA NOVA] {c} ({cols32[c]})")
            
        # Colunas removidas no APP32
        old_cols = set(cols31.keys()) - set(cols32.keys())
        for c in sorted(old_cols):
            report.append(f"  - [COLUNA REMOVIDA] {c} ({cols31[c]})")
            
        # Colunas com tipos diferentes
        common_cols = set(cols31.keys()) & set(cols32.keys())
        for c in sorted(common_cols):
            if cols31[c] != cols32[c]:
                report.append(f"  ! [TIPO ALTERADO] {c}: {cols31[c]} -> {cols32[c]}")

    with open('migration_comparison_report.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    print("Relatório gerado em migration_comparison_report.txt")

if __name__ == "__main__":
    compare()
