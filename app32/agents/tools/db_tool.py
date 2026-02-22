import os
import json
import logging
from typing import Dict, Any
from sqlalchemy import create_engine, text
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_db_engine():
    """Cria o engine de conexão usando a DATABASE_URL do .env"""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fallback para SQLite local se não houver URL
        db_url = "sqlite:///instance/project.db"
    return create_engine(db_url)

@tool
def atualizar_perfil_empresa(field_name: str, value: str, company_id: int) -> str:
    """
    Atualiza informações cadastrais da empresa no banco de dados.
    Campos permitidos: 'mission', 'vision', 'values', 'segment', 'description'.
    """
    allowed_fields = {
        "mission": "mvv_mission",
        "vision": "mvv_vision",
        "values": "mvv_values",
        "segment": "industry",
        "description": "description"
    }

    if field_name not in allowed_fields:
        return f"Erro: O campo '{field_name}' não é permitido para atualização direta."

    try:
        engine = get_db_engine()
        db_column = allowed_fields[field_name]
        
        with engine.connect() as conn:
            # Query parametrizada para evitar SQL Injection
            query = text(f"UPDATE companies SET {db_column} = :val, updated_at = :now WHERE id = :cid")
            conn.execute(query, {"val": value, "now": datetime.utcnow(), "cid": company_id})
            conn.commit()

        return f"Sucesso: Campo '{field_name}' atualizado para a empresa ID {company_id}."
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {e}")
        return f"Erro técnico ao atualizar: {str(e)}"

@tool
def consultar_metricas_empresa(topico: str) -> str:
    """
    ESSENCIAL para validar viabilidade. 
    Acessa dados reais do banco de dados sobre Financeiro, Projetos ou Equipe.
    Input: 'financeiro', 'projetos' ou 'equipe'.
    """
    try:
        engine = get_db_engine()
        results = {}

        with engine.connect() as conn:
            if topico == "financeiro":
                # Busca indicadores financeiros (KPIs com unidade R$)
                query = text("""
                    SELECT i.name, id.value, id.record_date 
                    FROM indicators i
                    JOIN indicator_goals ig ON i.id = ig.indicator_id
                    JOIN indicator_data id ON ig.id = id.goal_id
                    WHERE i.unit LIKE 'R%' 
                    ORDER BY id.record_date DESC LIMIT 10
                """)
                rows = conn.execute(query).fetchall()
                data = [{"indicador": r[0], "valor": float(r[1]), "data": str(r[2])} for r in rows]
                
                # Se não houver dados, retorna um sumário de orçamentos de projetos
                if not data:
                    query_projs = text("SELECT title, budget FROM projects WHERE budget IS NOT NULL")
                    rows_projs = conn.execute(query_projs).fetchall()
                    data = [{"projeto": r[0], "orcamento": r[1]} for r in rows_projs]
                
                results = {
                    "tipo": "Financeiro (Real)",
                    "dados": data or "Nenhum dado financeiro encontrado no momento."
                }

            elif topico == "projetos":
                # Sumário de status de projetos
                query = text("""
                    SELECT status, COUNT(*) as total 
                    FROM projects 
                    GROUP BY status
                """)
                rows = conn.execute(query).fetchall()
                results = {
                    "tipo": "Status de Projetos",
                    "distribuicao": {r[0]: r[1] for r in rows}
                }

            elif topico == "equipe":
                # Headcount por departamento
                query = text("""
                    SELECT department, COUNT(*) as total 
                    FROM employees 
                    WHERE status = 'active'
                    GROUP BY department
                """)
                rows = conn.execute(query).fetchall()
                results = {
                    "tipo": "Headcount por Departamento",
                    "departamentos": {r[0] or "Geral": r[1] for r in rows}
                }
            
            else:
                return f"Tópico '{topico}' não suportado. Use 'financeiro', 'projetos' ou 'equipe'."

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Erro ao consultar banco de dados: {e}")
        return json.dumps({"error": f"Erro técnico ao acessar o banco: {str(e)}"}, ensure_ascii=False)
