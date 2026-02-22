import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def query_db():
    conn_str = os.getenv("DATABASE_URL")
    if "host.docker.internal" in conn_str:
        conn_str = conn_str.replace("host.docker.internal", "localhost")
    
    report_file = "c:/GestaoVersus/app32/scripts/structure_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")

        try:
            conn = psycopg2.connect(conn_str)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. Find Company
            search_term = "Versus"
            cur.execute("SELECT id, name FROM companies WHERE name ILIKE %s", (f'%{search_term}%',))
            companies = cur.fetchall()
            
            if not companies:
                log("Empresa não encontrada.")
                return

            log("Empresas encontradas:")
            company = None
            for c in companies:
                log(f"- {c['name']} (ID: {c['id']})")
                if "AA -" in c['name'] or "Versus Gestão Corporativa" in c['name'] or "Versus Gestao Corporativa" in c['name']:
                    company = c
            
            if not company:
                log("Selecione uma empresa manualmente.")
                return

            company_id = company['id']
            log(f"\nResultados para: {company['name']} (ID: {company_id})")
            log("-" * 50)

            # 2. Get Areas
            cur.execute("SELECT id, name FROM process_areas WHERE company_id = %s ORDER BY order_index", (company_id,))
            areas = cur.fetchall()
            
            if not areas:
                log("Nenhuma área encontrada.")
                return

            for area in areas:
                log(f"\n[ÁREA] {area['name']} (ID: {area['id']})")
                
                # 3. Get Macroprocesses
                cur.execute("SELECT id, name FROM macro_processes WHERE area_id = %s AND company_id = %s ORDER BY order_index", 
                            (area['id'], company_id))
                macros = cur.fetchall()
                
                for macro in macros:
                    log(f"  [MACRO] {macro['name']} (ID: {macro['id']})")
                    
                    # 4. Get Processes
                    cur.execute("SELECT id, name FROM processes WHERE macro_id = %s AND company_id = %s ORDER BY order_index", 
                                (macro['id'], company_id))
                    processes = cur.fetchall()
                    
                    for process in processes:
                        log(f"    [PROCESSO] {process['name']} (ID: {process['id']})")

        except Exception as e:
            log(f"Erro: {e}")
        finally:
            if 'conn' in locals():
                conn.close()


if __name__ == "__main__":
    query_db()
