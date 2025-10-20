#!/usr/bin/env python3
"""
Verificar relação entre projetos e portfólios
"""

import sqlite3

def check_project_portfolio_relation():
    """Verifica como projetos estão relacionados com portfólios."""
    
    print("Verificando relação entre projetos e portfólios...")
    
    try:
        conn = sqlite3.connect('instance/pevapp22.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela company_projects
        cursor.execute("PRAGMA table_info(company_projects)")
        columns = cursor.fetchall()
        print("Colunas da tabela company_projects:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}) - Nullable: {not col[3]}")
        
        print()
        
        # Verificar se há campo plan_id na tabela company_projects
        cursor.execute("SELECT name FROM pragma_table_info('company_projects') WHERE name='plan_id'")
        plan_id_exists = cursor.fetchone() is not None
        print(f"Campo 'plan_id' existe em company_projects: {plan_id_exists}")
        
        # Verificar dados existentes
        cursor.execute("SELECT COUNT(*) FROM company_projects")
        project_count = cursor.fetchone()[0]
        print(f"Total de projetos: {project_count}")
        
        if project_count > 0 and plan_id_exists:
            # Mostrar alguns exemplos de projetos com plan_id
            cursor.execute("SELECT id, code, title, plan_id FROM company_projects WHERE plan_id IS NOT NULL LIMIT 5")
            projects_with_plan = cursor.fetchall()
            print(f"Projetos com plan_id (primeiros 5):")
            for proj in projects_with_plan:
                print(f"  - ID: {proj['id']}, Code: {proj['code']}, Title: {proj['title']}, Plan ID: {proj['plan_id']}")
            
            # Verificar quantos projetos estão associados a cada portfólio
            cursor.execute("""
                SELECT p.id as portfolio_id, p.name as portfolio_name, COUNT(cp.id) as project_count
                FROM portfolios p
                LEFT JOIN company_projects cp ON cp.plan_id = p.id
                WHERE p.company_id = 14
                GROUP BY p.id, p.name
                ORDER BY p.name
            """)
            portfolio_projects = cursor.fetchall()
            print(f"\nPortfólios da empresa 14 com contagem de projetos:")
            for pp in portfolio_projects:
                print(f"  - Portfólio: {pp['portfolio_name']} (ID: {pp['portfolio_id']}) - Projetos: {pp['project_count']}")
        
        conn.close()
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_project_portfolio_relation()
