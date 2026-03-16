
import os, sys
from sqlalchemy import create_engine, text

# URL obtida do .env de produção
db_url = "postgresql://app:%2AParaiso1978@localhost:5432/bdversusv2"
engine = create_engine(db_url)

try:
    with engine.connect() as conn:
        print("Connected to database.")
        
        # 1. Obter empresas
        companies = conn.execute(text("SELECT id, client_code, name FROM companies")).fetchall()
        
        for co_id, co_code, co_name in companies:
            prefix = co_code if co_code else "CO"
            print(f"Processing Company: {co_name} ({prefix})")
            
            # 2. Criar nós da árvore
            tree_nodes = [
                ("1", "Operacional"),
                ("2", "Financeiro"),
                ("3", "Comportamental")
            ]
            
            node_ids = {}
            for code, name in tree_nodes:
                # Check exists
                existing = conn.execute(
                    text("SELECT id FROM incentive_indicator_tree WHERE company_id = :cid AND code = :code"),
                    {"cid": co_id, "code": code}
                ).fetchone()
                
                if not existing:
                    res = conn.execute(
                        text("INSERT INTO incentive_indicator_tree (company_id, code, name, created_at, updated_at) VALUES (:cid, :code, :name, now(), now()) RETURNING id"),
                        {"cid": co_id, "code": code, "name": name}
                    )
                    node_id = res.fetchone()[0]
                    print(f"  Created tree node: {name} (ID: {node_id})")
                else:
                    node_id = existing[0]
                
                node_ids[code] = node_id
                
            # 3. Atualizar indicadores
            indicators = conn.execute(
                text("SELECT id, name FROM incentive_indicators WHERE company_id = :cid"),
                {"cid": co_id}
            ).fetchall()
            
            for ind_id, ind_name in indicators:
                full_code = f"{prefix}.I.1.{ind_id}"
                conn.execute(
                    text("UPDATE incentive_indicators SET tree_id = :tid, full_code = :fcode WHERE id = :id"),
                    {"tid": node_ids["1"], "fcode": full_code, "id": ind_id}
                )
                print(f"  Updated indicator: {ind_name} -> {full_code}")
                
        conn.commit()
        print("SUCCESS: Seeding and migration completed via Raw SQL (Engine-only).")

except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
