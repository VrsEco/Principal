from __future__ import annotations

import logging
from datetime import date, datetime

from models import db
from src.intelligence.tools_support import get_active_company_id, get_active_user_id

logger = logging.getLogger(__name__)

# Instâncias consideradas "abertas" por padrão quando `status` não é informado.
_DEFAULT_OPEN_STATUSES = ("pending", "in_progress", "overdue")

# Estados de encerramento aceitos por `close_process_instance`.
_ALLOWED_CLOSURE_STATUSES = ("completed", "cancelled", "failed")


def _resolve_effective_company_id(requested_company_id: int | None = None) -> tuple[int | None, str | None]:
    """Espelha o resolvedor de `process_ops.py`: nunca aceita tenant divergente do contexto ativo."""

    active_company_id = get_active_company_id()

    if requested_company_id is not None:
        try:
            requested_company_id = int(requested_company_id)
        except (TypeError, ValueError):
            return None, "Erro: company_id informado é inválido."

    if active_company_id and requested_company_id and int(active_company_id) != int(requested_company_id):
        return None, "Erro: company_id solicitado não pertence ao contexto de empresa ativa."

    effective_company_id = requested_company_id or active_company_id
    if not effective_company_id:
        return None, "Erro: Nenhuma empresa ativa identificada (sessão, contexto Sapiens ou company_id explícito)."

    return int(effective_company_id), None


def _normalize_statuses(status: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if status is None:
        return _DEFAULT_OPEN_STATUSES
    if isinstance(status, str):
        values = [item.strip() for item in status.split(",") if item.strip()]
    else:
        values = [str(item).strip() for item in status if str(item).strip()]
    return tuple(values) if values else _DEFAULT_OPEN_STATUSES


def _parse_due_before(due_before: str | None):
    if not due_before:
        return None, None
    raw = str(due_before).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date(), None
        except ValueError:
            continue
    return None, "Erro: due_before deve estar no formato YYYY-MM-DD."


def list_open_process_instances(
    company_id: int | None = None,
    status: str | list[str] | None = None,
    due_before: str | None = None,
    assigned_to: int | None = None,
):
    """
    Lista instâncias de processo abertas/atrasadas da empresa ativa.

    Leitura tenant-safe (risco LOW, sem gate humano): usa o índice composto
    `ix_process_instances_open_overdue` (company_id, status, due_date) para
    evitar full scan. Para cada instância, resolve também o
    `manual_reference_json` do contrato de execução de atividade vinculado
    (quando existir), para orientar o agente sobre onde consultar o manual da
    atividade em andamento.

    :param company_id: Opcional. Se ausente, usa a empresa ativa da sessão.
    :param status: Opcional. Um status ou lista/CSV de status. Default:
        pending, in_progress, overdue.
    :param due_before: Opcional. Data limite (YYYY-MM-DD) para due_date.
    :param assigned_to: Opcional. Filtra por responsável/executor/dono
        (employee_id).
    """
    from models.process import ProcessInstance

    company_id, error = _resolve_effective_company_id(company_id)
    if error:
        return {"success": False, "error": error}

    statuses = _normalize_statuses(status)
    due_before_date, error = _parse_due_before(due_before)
    if error:
        return {"success": False, "error": error}

    try:
        query = ProcessInstance.query.filter(
            ProcessInstance.company_id == company_id,
            ProcessInstance.status.in_(statuses),
        )
        if due_before_date is not None:
            query = query.filter(ProcessInstance.due_date <= due_before_date)

        if assigned_to is not None:
            try:
                assigned_to_id = int(assigned_to)
            except (TypeError, ValueError):
                return {"success": False, "error": "Erro: assigned_to deve ser um ID de colaborador válido."}
            query = query.filter(
                db.or_(
                    ProcessInstance.responsible_id == assigned_to_id,
                    ProcessInstance.executor_id == assigned_to_id,
                    ProcessInstance.owner_employee_id == assigned_to_id,
                )
            )

        instances = query.order_by(
            ProcessInstance.due_date.asc().nulls_last(),
            ProcessInstance.id.asc(),
        ).all()

        today = date.today()
        payload = [_serialize_open_instance(instance, company_id=company_id, today=today) for instance in instances]

        return {
            "success": True,
            "company_id": company_id,
            "count": len(payload),
            "instances": payload,
        }
    except Exception as exc:
        logger.exception("Falha ao listar instâncias de processo abertas (company_id=%s)", company_id)
        return {"success": False, "error": f"Erro ao listar instâncias de processo abertas: {str(exc)}"}


def _serialize_open_instance(instance, *, company_id: int, today: date) -> dict:
    from models.employee import Employee
    from services.process_execution_contract_service import resolve_activity_execution_contract

    employee_id = instance.responsible_id or instance.executor_id or instance.owner_employee_id
    employee_name = None
    if employee_id:
        employee = Employee.query.filter_by(id=int(employee_id), company_id=int(company_id)).first()
        employee_name = employee.name if employee else None

    days_overdue = 0
    if instance.due_date and instance.due_date < today:
        days_overdue = (today - instance.due_date).days

    manual_reference: dict = {}
    if instance.current_bpmn_element_id:
        contract = resolve_activity_execution_contract(
            company_id=company_id,
            process_id=instance.process_id,
            bpmn_element_id=instance.current_bpmn_element_id,
        )
        if contract is not None:
            manual_reference = contract.manual_reference_json or {}

    return {
        "id": instance.id,
        "process_id": instance.process_id,
        "process_name": instance.process_rel.name if instance.process_rel else None,
        "process_code": instance.process_rel.code if instance.process_rel else None,
        "routine_id": instance.routine_id,
        "status": instance.status,
        "due_date": instance.due_date.isoformat() if instance.due_date else None,
        "days_overdue": days_overdue,
        "responsible_employee_id": employee_id,
        "responsible_name": employee_name,
        "manual_reference": manual_reference,
    }


def close_process_instance(
    company_id: int | None,
    instance_id: int,
    evidence: int | dict,
    closure_status: str = "completed",
):
    """
    Encerra uma instância de processo, exigindo evidência de conclusão já existente.

    Mutação sensível (risco HIGH, human_gate=True no catálogo de capacidades):
    encerramento de instância impacta execução operacional e trilha de
    auditoria. Esta tool NUNCA fabrica evidência — `evidence` deve referenciar
    um `ProcessActivityArtifactExecution` já existente, com status
    `completed` e vinculado à instância via um artefato de
    `execution_scope='process_instance'`. Sem esse artefato, o encerramento é
    recusado. Todo acesso filtra sempre `company_id` + `id` juntos, nunca só
    o id do objeto.

    :param company_id: Obrigatório quando o canal não tiver contexto tenant autenticado.
    :param instance_id: ID da instância de processo a encerrar (na empresa ativa).
    :param evidence: ID do `ProcessActivityArtifactExecution` (artefato concluído,
        execution_scope='process_instance') que comprova o encerramento. Também
        aceita `{"artifact_execution_id": <id>}`.
    :param closure_status: Status final da instância: completed, cancelled ou failed.
    """
    from models.process import ProcessInstance
    from models.process_artifact import ProcessActivityArtifactDefinition, ProcessActivityArtifactExecution

    company_id, error = _resolve_effective_company_id(company_id)
    if error:
        return {"success": False, "error": error}

    try:
        instance_id = int(instance_id)
    except (TypeError, ValueError):
        return {"success": False, "error": "Erro: instance_id é inválido."}

    closure_status = str(closure_status or "completed").strip().lower()
    if closure_status not in _ALLOWED_CLOSURE_STATUSES:
        return {
            "success": False,
            "error": f"Erro: closure_status inválido. Use um de {', '.join(_ALLOWED_CLOSURE_STATUSES)}.",
        }

    evidence_id = evidence.get("artifact_execution_id") if isinstance(evidence, dict) else evidence
    try:
        evidence_id = int(evidence_id)
    except (TypeError, ValueError):
        return {
            "success": False,
            "error": "Erro: evidence deve referenciar o ID de um artefato concluído (ProcessActivityArtifactExecution).",
        }

    try:
        # Sempre company_id + id juntos: nunca confiar somente no id do objeto.
        instance = ProcessInstance.query.filter_by(id=instance_id, company_id=company_id).first()
        if instance is None:
            return {"success": False, "error": "Erro: instância de processo não encontrada nesta empresa."}

        artifact_execution = (
            ProcessActivityArtifactExecution.query.join(
                ProcessActivityArtifactDefinition,
                ProcessActivityArtifactExecution.artifact_definition_id == ProcessActivityArtifactDefinition.id,
            )
            .filter(
                ProcessActivityArtifactExecution.id == evidence_id,
                ProcessActivityArtifactExecution.company_id == company_id,
                ProcessActivityArtifactExecution.process_instance_id == instance.id,
                ProcessActivityArtifactExecution.status == "completed",
                ProcessActivityArtifactDefinition.execution_scope == "process_instance",
            )
            .first()
        )
        if artifact_execution is None:
            return {
                "success": False,
                "error": (
                    "Erro: encerramento recusado. Nenhum artefato concluído "
                    "(execution_scope='process_instance') foi encontrado para esta "
                    "instância com o evidence informado. A tool não fabrica evidência."
                ),
            }

        actor_user_id = get_active_user_id()
        previous_status = instance.status
        instance.status = closure_status
        instance.actual_end_date = date.today()
        instance.completed_at = datetime.utcnow()
        audit_note = (
            f"[MCP close_process_instance] status {previous_status!r} -> {closure_status!r}; "
            f"evidence=artifact_execution:{artifact_execution.id}; actor_user_id={actor_user_id or 'desconhecido'}."
        )
        instance.notes = f"{instance.notes}\n{audit_note}" if instance.notes else audit_note

        db.session.commit()

        persisted = ProcessInstance.query.filter_by(id=instance_id, company_id=company_id).first()
        if persisted is None or persisted.status != closure_status:
            db.session.rollback()
            return {"success": False, "error": "Erro: falha na validação pós-escrita do encerramento no tenant informado."}

        return {
            "success": True,
            "company_id": company_id,
            "instance_id": instance.id,
            "status": instance.status,
            "evidence_artifact_execution_id": artifact_execution.id,
        }
    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "Falha ao encerrar instância de processo (company_id=%s, instance_id=%s)", company_id, instance_id
        )
        return {"success": False, "error": f"Erro ao encerrar instância de processo: {str(exc)}"}
