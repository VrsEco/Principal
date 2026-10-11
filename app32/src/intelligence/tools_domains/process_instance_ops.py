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


# Campos editáveis por ``update_process_instance`` e status que a edição pode atribuir. Concluir ou falhar a instância
# exige evidência e continua só em ``close_process_instance``; cancelar é permitido sem aprovação (decisão 2026-10-11).
_UPDATE_ALLOWED_FIELDS = frozenset(
    {
        "title", "description", "priority", "due_date", "notes", "append_notes", "status", "pause_reason",
        "estimated_hours", "worked_hours",
    }
)
_UPDATE_ALLOWED_STATUSES = ("pending", "in_progress", "paused", "waiting_external", "cancelled")
_CLOSED_STATUSES = ("completed", "failed", "cancelled")
_PRIORITIES = ("low", "normal", "high", "urgent")
_MAX_UPDATE_FIELDS = 8
_MAX_APPEND_NOTES_CHARS = 4000
_MAX_NOTES_CHARS = 50000
_MAX_HOURS = 10000


def _parse_hours(value, field: str):
    from decimal import Decimal, InvalidOperation

    if isinstance(value, bool) or value is None:
        return None, f"Erro: {field} deve ser um número de horas."
    try:
        hours = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None, f"Erro: {field} deve ser um número de horas."
    if not hours.is_finite() or hours < 0 or hours > _MAX_HOURS:
        return None, f"Erro: {field} deve estar entre 0 e {_MAX_HOURS} horas."
    return hours.quantize(Decimal("0.01")), None


def _serialize_edited_instance(instance) -> dict:
    """Resposta enxuta da edição (sem carregar relacionamentos)."""

    def _iso(value):
        return value.isoformat() if hasattr(value, "isoformat") else value

    return {
        "id": instance.id,
        "process_id": instance.process_id,
        "title": instance.title,
        "description": instance.description,
        "status": instance.status,
        "priority": instance.priority,
        "due_date": _iso(instance.due_date),
        "actual_end_date": _iso(instance.actual_end_date),
        "paused_at": _iso(instance.paused_at),
        "pause_reason": instance.pause_reason,
        "estimated_hours": float(instance.estimated_hours) if instance.estimated_hours is not None else 0.0,
        "worked_hours": float(instance.worked_hours) if instance.worked_hours is not None else 0.0,
        "notes": instance.notes,
    }


def update_process_instance(company_id: int | None, instance_id: int, changes: dict):
    """
    Edita os dados de uma instância de processo (card): título, descrição, prioridade, prazo, notas, horas e status.

    Mutação de risco médio, tenant-safe (company_id + id juntos). Campos de ``changes``: title, description,
    priority (low/normal/high/urgent), due_date (YYYY-MM-DD; vazio limpa), notes (SUBSTITUI o texto), append_notes
    (ACRESCENTA registro com data e autor, preserva o histórico), status (pending, in_progress, paused,
    waiting_external, cancelled), pause_reason, estimated_hours, worked_hours. Concluir ou falhar a instância NÃO
    é feito aqui: exige evidência e usa ``close_process_instance``. Instância já encerrada só aceita append_notes.

    :param company_id: Obrigatório quando o canal não tiver contexto tenant autenticado.
    :param instance_id: ID da instância de processo, na empresa ativa.
    :param changes: Objeto com os campos a alterar (até 8 por chamada).
    """
    from models.process import ProcessInstance

    company_id, error = _resolve_effective_company_id(company_id)
    if error:
        return {"success": False, "error": error}
    try:
        instance_id = int(instance_id)
    except (TypeError, ValueError):
        return {"success": False, "error": "Erro: instance_id é inválido."}
    if not isinstance(changes, dict) or not changes:
        return {"success": False, "error": "Erro: informe um objeto não vazio em changes."}
    invalid = sorted(set(changes) - _UPDATE_ALLOWED_FIELDS)
    if invalid:
        return {"success": False, "error": f"Erro: campos não permitidos na atualização: {', '.join(invalid)}."}
    if len(changes) > _MAX_UPDATE_FIELDS:
        return {"success": False, "error": f"Erro: atualização excede o limite de {_MAX_UPDATE_FIELDS} campos por chamada."}

    normalized: dict = {}
    if "title" in changes:
        title = str(changes["title"] or "").strip()
        if not title or len(title) > 255:
            return {"success": False, "error": "Erro: title deve ter de 1 a 255 caracteres."}
        normalized["title"] = title
    if "description" in changes:
        normalized["description"] = str(changes["description"] or "").strip() or None
    if "priority" in changes:
        priority = str(changes["priority"] or "").strip().lower()
        if priority not in _PRIORITIES:
            return {"success": False, "error": f"Erro: priority inválida. Use {', '.join(_PRIORITIES)}."}
        normalized["priority"] = priority
    if "due_date" in changes:
        raw_due = changes["due_date"]
        if raw_due in (None, ""):
            normalized["due_date"] = None
        else:
            try:
                normalized["due_date"] = datetime.strptime(str(raw_due).strip()[:10], "%Y-%m-%d").date()
            except ValueError:
                return {"success": False, "error": "Erro: due_date deve estar no formato YYYY-MM-DD."}
    if "notes" in changes and "append_notes" in changes:
        return {"success": False, "error": "Erro: use notes (substitui o texto) ou append_notes (acrescenta), não os dois."}
    if "notes" in changes:
        normalized["notes"] = str(changes["notes"] or "").strip() or None
    if "append_notes" in changes:
        text = changes["append_notes"]
        if not isinstance(text, str) or not text.strip():
            return {"success": False, "error": "Erro: append_notes não pode ser vazio."}
        if len(text.strip()) > _MAX_APPEND_NOTES_CHARS:
            return {"success": False, "error": f"Erro: append_notes excede {_MAX_APPEND_NOTES_CHARS} caracteres."}
        normalized["append_notes"] = text.strip()
    if "status" in changes:
        status = str(changes["status"] or "").strip().lower()
        if status in ("completed", "failed"):
            return {
                "success": False,
                "error": "Erro: concluir ou falhar a instância exige evidência; use close_process_instance.",
            }
        if status not in _UPDATE_ALLOWED_STATUSES:
            return {"success": False, "error": f"Erro: status inválido. Use {', '.join(_UPDATE_ALLOWED_STATUSES)}."}
        normalized["status"] = status
    if "pause_reason" in changes:
        normalized["pause_reason"] = str(changes["pause_reason"] or "").strip() or None
    for hours_field in ("estimated_hours", "worked_hours"):
        if hours_field in changes:
            value, hours_error = _parse_hours(changes[hours_field], hours_field)
            if hours_error:
                return {"success": False, "error": hours_error}
            normalized[hours_field] = value

    try:
        instance = ProcessInstance.query.filter_by(id=instance_id, company_id=company_id).first()
        if instance is None:
            return {"success": False, "error": "Erro: instância de processo não encontrada nesta empresa."}

        previous_status = instance.status
        if previous_status in _CLOSED_STATUSES and set(normalized) - {"append_notes"}:
            return {
                "success": False,
                "error": f"Erro: instância já encerrada ({previous_status}); só é possível acrescentar notas (append_notes).",
            }

        # Tudo que pode recusar é calculado antes de qualquer atribuição.
        actor_user_id = get_active_user_id()
        new_notes = instance.notes
        if "notes" in normalized:
            new_notes = normalized["notes"]
        if "append_notes" in normalized:
            from services.project_task_mcp_service import ProjectTaskMCPService

            new_notes = ProjectTaskMCPService._append_note_entry(
                new_notes, normalized["append_notes"], ProjectTaskMCPService._actor_label(actor_user_id)
            )
        edited_fields = sorted(set(normalized) - {"append_notes"})
        if edited_fields:
            audit_note = (
                f"[MCP update_process_instance] campos: {', '.join(edited_fields)}; "
                f"actor_user_id={actor_user_id or 'desconhecido'}"
            )
            if "status" in normalized and normalized["status"] != previous_status:
                audit_note += f"; status {previous_status!r} -> {normalized['status']!r}"
            audit_note += "."
            new_notes = f"{new_notes}\n{audit_note}" if new_notes else audit_note
        if new_notes and len(new_notes) > _MAX_NOTES_CHARS:
            return {"success": False, "error": "Erro: as notas excederiam o limite; resuma o histórico antes de acrescentar."}

        for field in ("title", "description", "priority", "due_date", "pause_reason", "estimated_hours", "worked_hours"):
            if field in normalized:
                setattr(instance, field, normalized[field])
        if "notes" in normalized or "append_notes" in normalized or edited_fields:
            instance.notes = new_notes
        if "status" in normalized:
            new_status = normalized["status"]
            instance.status = new_status
            now = datetime.utcnow()
            if new_status == "paused":
                instance.paused_at = now
            elif previous_status == "paused":
                instance.paused_at = None
            if new_status == "in_progress" and instance.started_at is None:
                instance.started_at = now
            if new_status == "cancelled":
                instance.actual_end_date = date.today()
                instance.completed_at = now

        db.session.commit()
        persisted = ProcessInstance.query.filter_by(id=instance_id, company_id=company_id).first()
        if persisted is None:
            db.session.rollback()
            return {"success": False, "error": "Erro: falha na validação pós-escrita da atualização no tenant informado."}
        return {"success": True, "company_id": company_id, "instance": _serialize_edited_instance(persisted)}
    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "Falha ao atualizar instância de processo (company_id=%s, instance_id=%s)", company_id, instance_id
        )
        return {"success": False, "error": f"Erro ao atualizar instância de processo: {str(exc)}"}
