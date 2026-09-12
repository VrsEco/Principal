from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy import text

from models import db
from src.intelligence.tools_support import get_active_company_id, sanitize_output
from src.intelligence.tools_domains import task_ops as task_ops_domain


def consult_rules(query: str):
    """Bloqueia RAG legado global sem filtro de tenant.

    O RAG histórico não recebe ``company_id`` nem aplica filtro de metadados;
    portanto não pode ser fonte de regras para sessões multiempresa. A consulta
    deve migrar para a ferramenta de conhecimento organizacional autorizada.
    """
    del query
    return (
        "Consulta de regras legada desabilitada por segurança. Use a ferramenta "
        "de conhecimento organizacional autorizada e escopada por empresa."
    )


def query_database(sql_query: str):
    """Bloqueia SQL livre legado; leituras devem usar read models tenant-safe.

    Inserir ``company_id`` por expressão regular não é uma barreira de tenant:
    comentários SQL, CTEs, UNIONs e subconsultas podem deslocar ou anular o
    predicado. Não execute texto SQL produzido por LLM ou usuário até existir um
    contrato allowlisted por read model, com parâmetros e escopo explícito.
    """
    del sql_query
    return (
        "Consulta SQL livre desabilitada por segurança. Use uma ferramenta/read model "
        "autorizado e com escopo explícito de empresa."
    )


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
