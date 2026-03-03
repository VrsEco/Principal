import os
import sys
import logging
from flask import current_app
from src.intelligence.tool_context import get_sapiens_context, SapiensIdentity
from src.intelligence.llm import llm_router
from langchain_core.messages import HumanMessage
from models import db, Company

logger = logging.getLogger(__name__)

def run_deep_diagnostics(user_id: int, company_id: int):
    """
    Executa um diagnóstico profundo do sistema de Agentes Sapiens V2 (@ARQUITETO).
    Verifica:
    1. Ambiente (Python, OS)
    2. Conectividade OpenAI
    3. Conectividade Banco de Dados
    4. Integridade do Contexto Sapiens (Multi-tenancy)
    5. Acesso ao Checkpointer (LangGraph Memory)
    """
    report = {
        "status": "success",
        "checks": {}
    }

    # 1. Check Python Environment
    report["checks"]["environment"] = {
        "python_version": sys.version,
        "os": os.name,
        "cwd": os.getcwd(),
        "env_vars": {
            "OPENAI_API_KEY": "PRESENT" if os.environ.get("OPENAI_API_KEY") else "MISSING",
            "DATABASE_URL": "PRESENT" if os.environ.get("DATABASE_URL") else "MISSING",
            "FLASK_ENV": os.environ.get("FLASK_ENV", "not set")
        }
    }

    # 2. Check Database
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        company = Company.query.get(company_id)
        report["checks"]["database"] = {
            "status": "OK",
            "test_company_found": company.name if company else "NOT FOUND (ID: " + str(company_id) + ")"
        }
    except Exception as e:
        report["checks"]["database"] = {"status": "ERROR", "message": str(e)}

    # 3. Check Context Inheritance (CRITICAL for "Oi" bug)
    identity = get_sapiens_context()
    report["checks"]["context"] = {
        "thread_user_id": identity.user_id,
        "thread_company_id": identity.company_id,
        "is_correct": (identity.user_id == user_id and identity.company_id == company_id)
    }

    # 4. Check OpenAI Connectivity
    try:
        test_resp = llm_router.invoke([HumanMessage(content="Responder apenas com a palavra 'PONG'")])
        report["checks"]["openai"] = {
            "status": "OK",
            "response": test_resp.content.strip()
        }
    except Exception as e:
        report["checks"]["openai"] = {"status": "ERROR", "message": str(e)}

    # 5. Check LangGraph Nodes & Tools (Simple invocation)
    try:
        from src.intelligence.work_agents.graph import create_work_agent_workflow
        from src.intelligence.memory import memory_checkpointer
        
        # Testamos a criação do grafo
        graph = create_work_agent_workflow(checkpointer=memory_checkpointer)
        report["checks"]["langgraph"] = {
            "status": "OK",
            "nodes": list(graph.nodes.keys())
        }
    except Exception as e:
        report["checks"]["langgraph"] = {"status": "ERROR", "message": str(e)}

    return report
