from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy import text

from models import db
from src.intelligence.rag import knowledge_base
from src.intelligence.tools_support import get_active_company_id, sanitize_output
from src.intelligence.tools_domains import task_ops as task_ops_domain


def consult_rules(query: str):
    """Consulta o manual de regras de negócio e procedimentos da empresa."""
    try:
        results = knowledge_base.search(query, k=3)
        if not results:
            return "Nenhuma regra encontrada para esta consulta."
        return "\n\n".join([f"Regra: {doc.page_content}" for doc in results])
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        return f"Erro ao consultar regras: {exc}"


def query_database(sql_query: str):
    """Executa SELECT operacional com bloqueio de tabelas sensíveis e filtro tenant."""
    clean_query = sql_query.strip()
    if not clean_query.lower().startswith("select"):
        return "Erro: Por segurança, apenas consultas SELECT são permitidas."

    sensitive_tables = [
        "users",
        "roles",
        "user_logs",
        "audit_log",
        "sessions",
        "alembic_version",
        "employees",
        "companies",
    ]
    for table in sensitive_tables:
        if re.search(rf"\b{table}\b", clean_query.lower()):
            return sanitize_output(
                f"Erro: Acesso à tabela '{table}' é restrito por motivos de segurança e privacidade."
            )

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Contexto de empresa nao identificado (Sessão ou ACTIVE_COMPANY_ID ausente)."

    if "where" in clean_query.lower():
        secure_query = re.sub(r"(?i)where", f"WHERE company_id = {company_id} AND", clean_query)
    elif "order by" in clean_query.lower():
        secure_query = re.sub(r"(?i)order by", f"WHERE company_id = {company_id} ORDER BY", clean_query)
    elif "limit" in clean_query.lower():
        secure_query = re.sub(r"(?i)limit", f"WHERE company_id = {company_id} LIMIT", clean_query)
    else:
        secure_query = f"{clean_query} WHERE company_id = {company_id}"

    try:
        with db.engine.connect() as connection:
            result = connection.execute(text(secure_query))
            rows = [dict(row._mapping) for row in result]
        if not rows:
            return "Nenhum resultado encontrado para esta consulta no contexto da sua empresa."
        return sanitize_output(json.dumps(rows, default=str))
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        return sanitize_output(f"Erro ao executar query SQL: {exc}")


def _normalize_issue_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _build_technical_issue_title(error_text: str, issue_context: str) -> str:
    combined = _normalize_issue_text(f"{error_text} {issue_context}").lower()
    signatures = [
        (("illegalstatechangeerror", "transaction is closed", "this transaction is closed"), "[BUG][SQLALCHEMY_TX] Transacao fechada ao concluir atividade"),
        (("relation", "does not exist"), "[BUG][SQL] Relacao inexistente em consulta operacional"),
        (("column", "does not exist"), "[BUG][SQL] Coluna inexistente em consulta operacional"),
        (("jinja", "undefined"), "[BUG][JINJA] Variavel indefinida em renderizacao"),
    ]
    for markers, title in signatures:
        if all(marker in combined for marker in markers):
            return title
    compact_error = _normalize_issue_text(error_text)
    if compact_error:
        return f"[BUG] {compact_error[:120]}"
    return "[BUG] Erro tecnico detectado automaticamente"


def escalate_technical_issue(error_description: str, context: str):
    """Escalona erro técnico para o Squad via task_ops."""
    try:
        result = task_ops_domain.squad_create_intervention(
            title=_build_technical_issue_title(error_description, context),
            due_date=str(datetime.utcnow().date()),
            how="Contexto do erro e logs para análise investigativa.",
            notes=f"Descrição do Erro:\n{error_description}\n\nContexto da IA:\n{context}",
            assignee_name="Agente Sapiens",
        )
        return f"Escalonamento realizado com sucesso. A tarefa foi criada no Kanban da Squad de Engenharia: {result}"
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        return f"Erro ao processar escalonamento para a Squad: {exc}"


__all__ = ["consult_rules", "query_database", "escalate_technical_issue"]
