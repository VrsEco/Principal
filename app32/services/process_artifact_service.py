from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Iterable
from uuid import uuid4

from models import (
    Process,
    ProcessActivityArtifactDefinition,
    ProcessActivityArtifactExecution,
    ProcessActivityArtifactLink,
    ProcessInstanceExecution,
    ProcessRoutine,
    db,
)
from models.process_artifact import (
    PROCESS_ARTIFACT_DEFINITION_STATUSES,
    PROCESS_ARTIFACT_EXECUTION_STATUSES,
    PROCESS_ARTIFACT_TYPES,
)


FORM_FIELD_TYPES = (
    "text",
    "textarea",
    "number",
    "date",
    "datetime",
    "select",
    "multiselect",
    "checkbox",
    "email",
    "phone",
    "file",
)


class ProcessArtifactValidationError(ValueError):
    """Erro funcional tenant-safe da camada de artefatos de processo."""


def _clean_text(value: Any, *, field: str = "campo", required: bool = False) -> str | None:
    text = str(value or "").strip()
    if required and not text:
        raise ProcessArtifactValidationError(f"{field} é obrigatório.")
    return text or None


def normalize_artifact_type(value: Any) -> str:
    artifact_type = _clean_text(value, field="tipo do artefato", required=True)
    if artifact_type not in PROCESS_ARTIFACT_TYPES:
        raise ProcessArtifactValidationError("Tipo de artefato inválido.")
    return artifact_type


def normalize_definition_status(value: Any) -> str:
    status = _clean_text(value, field="status", required=True)
    if status not in PROCESS_ARTIFACT_DEFINITION_STATUSES:
        raise ProcessArtifactValidationError("Status da definição de artefato inválido.")
    return status


def normalize_execution_status(value: Any) -> str:
    status = _clean_text(value, field="status", required=True)
    if status not in PROCESS_ARTIFACT_EXECUTION_STATUSES:
        raise ProcessArtifactValidationError("Status da execução de artefato inválido.")
    return status


def _ensure_unique_ids(items: list[dict[str, Any]], *, scope: str) -> None:
    identifiers = []
    for item in items:
        if not isinstance(item, dict):
            raise ProcessArtifactValidationError(f"Cada item de {scope} deve ser um objeto.")
        identifiers.append(_clean_text(item.get("id"), field=f"id de {scope}", required=True))
    if len(identifiers) != len(set(identifiers)):
        raise ProcessArtifactValidationError(f"IDs duplicados em {scope}.")


def validate_artifact_configuration(artifact_type: str, configuration: Any) -> dict[str, Any]:
    artifact_type = normalize_artifact_type(artifact_type)
    if not isinstance(configuration, dict):
        raise ProcessArtifactValidationError("configuration_json deve ser um objeto.")

    normalized = dict(configuration)
    if artifact_type == "form":
        sections = normalized.get("sections") or []
        if not isinstance(sections, list):
            raise ProcessArtifactValidationError("sections deve ser uma lista.")
        _ensure_unique_ids(sections, scope="seções")
        all_field_ids: list[str] = []
        for section in sections:
            if not isinstance(section, dict):
                raise ProcessArtifactValidationError("Cada seção deve ser um objeto.")
            _clean_text(section.get("title"), field="título da seção", required=True)
            fields = section.get("fields") or []
            if not isinstance(fields, list):
                raise ProcessArtifactValidationError("fields deve ser uma lista.")
            _ensure_unique_ids(fields, scope="campos da seção")
            for field in fields:
                if not isinstance(field, dict):
                    raise ProcessArtifactValidationError("Cada campo deve ser um objeto.")
                field_id = _clean_text(field.get("id"), field="id do campo", required=True)
                _clean_text(field.get("label"), field="rótulo do campo", required=True)
                field_type = _clean_text(field.get("type"), field="tipo do campo", required=True)
                if field_type not in FORM_FIELD_TYPES:
                    raise ProcessArtifactValidationError(f"Tipo de campo inválido: {field_type}.")
                options = field.get("options") or []
                if field_type in {"select", "multiselect"} and not isinstance(options, list):
                    raise ProcessArtifactValidationError("options deve ser uma lista.")
                all_field_ids.append(field_id)
        if len(all_field_ids) != len(set(all_field_ids)):
            raise ProcessArtifactValidationError("IDs de campos devem ser únicos no formulário.")

    if artifact_type == "check":
        items = normalized.get("items") or []
        if not isinstance(items, list):
            raise ProcessArtifactValidationError("items deve ser uma lista.")
        _ensure_unique_ids(items, scope="itens do checklist")
        for item in items:
            if not isinstance(item, dict):
                raise ProcessArtifactValidationError("Cada item deve ser um objeto.")
            _clean_text(item.get("label"), field="descrição do item", required=True)

    return normalized


def _get_process(company_id: int, process_id: int) -> Process:
    process = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if not process:
        raise ProcessArtifactValidationError("Processo não encontrado para este tenant.")
    return process


def _get_definition(company_id: int, process_id: int, definition_id: int) -> ProcessActivityArtifactDefinition:
    definition = ProcessActivityArtifactDefinition.query.filter_by(
        id=definition_id,
        company_id=company_id,
        process_id=process_id,
    ).first()
    if not definition:
        raise ProcessArtifactValidationError("Definição de artefato não encontrada para este tenant/processo.")
    return definition


def _get_legacy_pop(company_id: int, process_id: int, routine_id: Any) -> ProcessRoutine:
    try:
        normalized_id = int(routine_id)
    except (TypeError, ValueError):
        raise ProcessArtifactValidationError("legacy_process_routine_id inválido.")
    routine = ProcessRoutine.query.filter_by(
        id=normalized_id,
        company_id=company_id,
        process_id=process_id,
    ).first()
    if not routine:
        raise ProcessArtifactValidationError("POP legado não encontrado para este tenant/processo.")
    return routine


def create_artifact_definition(
    company_id: int,
    process_id: int,
    payload: dict[str, Any],
    *,
    user_id: int | None = None,
    commit: bool = True,
) -> ProcessActivityArtifactDefinition:
    _get_process(company_id, process_id)
    if not isinstance(payload, dict):
        raise ProcessArtifactValidationError("Payload inválido.")

    version = int(payload.get("version") or 1)
    if version <= 0:
        raise ProcessArtifactValidationError("A versão deve ser maior que zero.")
    status = normalize_definition_status(payload.get("status") or "draft")
    artifact_type = normalize_artifact_type(payload.get("artifact_type"))
    configuration = validate_artifact_configuration(artifact_type, payload.get("configuration_json") or {})
    if status == "published" and artifact_type == "form" and not configuration.get("sections"):
        raise ProcessArtifactValidationError("Formulário precisa ter ao menos uma seção para publicação.")
    if status == "published" and artifact_type == "check" and not configuration.get("items"):
        raise ProcessArtifactValidationError("Checklist precisa ter ao menos um item para publicação.")

    legacy_process_routine_id = payload.get("legacy_process_routine_id")
    if legacy_process_routine_id not in (None, ""):
        if artifact_type != "pop":
            raise ProcessArtifactValidationError("Somente artefato POP pode referenciar ProcessRoutine.")
        legacy_process_routine_id = _get_legacy_pop(
            company_id,
            process_id,
            legacy_process_routine_id,
        ).id
    else:
        legacy_process_routine_id = None

    definition = ProcessActivityArtifactDefinition(
        company_id=company_id,
        process_id=process_id,
        artifact_key=_clean_text(payload.get("artifact_key")) or uuid4().hex,
        artifact_type=artifact_type,
        name=_clean_text(payload.get("name"), field="nome", required=True),
        description=_clean_text(payload.get("description")),
        version=version,
        status=status,
        configuration_json=configuration,
        legacy_process_routine_id=legacy_process_routine_id,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
        published_at=datetime.utcnow() if status == "published" else None,
    )
    db.session.add(definition)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return definition


def get_artifact_definition(company_id: int, definition_id: int) -> ProcessActivityArtifactDefinition:
    definition = ProcessActivityArtifactDefinition.query.filter_by(
        id=definition_id,
        company_id=company_id,
    ).first()
    if not definition:
        raise ProcessArtifactValidationError("Definição de artefato não encontrada para este tenant.")
    return definition


def update_artifact_definition(
    company_id: int,
    definition_id: int,
    payload: dict[str, Any],
    *,
    user_id: int | None = None,
    commit: bool = True,
) -> ProcessActivityArtifactDefinition:
    definition = get_artifact_definition(company_id, definition_id)
    if definition.status != "draft":
        raise ProcessArtifactValidationError("Somente versões em rascunho podem ser editadas.")
    if "artifact_type" in payload and normalize_artifact_type(payload.get("artifact_type")) != definition.artifact_type:
        raise ProcessArtifactValidationError("O tipo do artefato não pode ser alterado.")
    if "name" in payload:
        definition.name = _clean_text(payload.get("name"), field="nome", required=True)
    if "description" in payload:
        definition.description = _clean_text(payload.get("description"))
    if "configuration_json" in payload:
        definition.configuration_json = validate_artifact_configuration(
            definition.artifact_type,
            payload.get("configuration_json") or {},
        )
    definition.updated_by_user_id = user_id
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return definition


def publish_artifact_definition(
    company_id: int,
    definition_id: int,
    *,
    user_id: int | None = None,
) -> ProcessActivityArtifactDefinition:
    definition = get_artifact_definition(company_id, definition_id)
    if definition.status == "archived":
        raise ProcessArtifactValidationError("Versão arquivada não pode ser publicada.")
    validate_artifact_configuration(definition.artifact_type, definition.configuration_json or {})
    if definition.artifact_type == "form" and not (definition.configuration_json or {}).get("sections"):
        raise ProcessArtifactValidationError("Formulário precisa ter ao menos uma seção para publicação.")
    if definition.artifact_type == "check" and not (definition.configuration_json or {}).get("items"):
        raise ProcessArtifactValidationError("Checklist precisa ter ao menos um item para publicação.")
    definition.status = "published"
    definition.published_at = datetime.utcnow()
    definition.updated_by_user_id = user_id
    db.session.commit()
    return definition


def archive_artifact_definition(company_id: int, definition_id: int) -> ProcessActivityArtifactDefinition:
    definition = get_artifact_definition(company_id, definition_id)
    definition.status = "archived"
    for link in definition.activity_links.all():
        link.is_active = False
    db.session.commit()
    return definition


def list_process_artifact_definitions(
    company_id: int,
    process_id: int,
    *,
    artifact_type: str | None = None,
    bpmn_element_id: str | None = None,
) -> list[dict[str, Any]]:
    _get_process(company_id, process_id)
    if bpmn_element_id:
        artifacts = list_activity_artifacts(company_id, process_id, bpmn_element_id)
        if artifact_type:
            normalized_type = normalize_artifact_type(artifact_type)
            artifacts = [item for item in artifacts if item.get("artifact_type") == normalized_type]
        return artifacts
    query = ProcessActivityArtifactDefinition.query.filter_by(company_id=company_id, process_id=process_id)
    if artifact_type:
        query = query.filter(ProcessActivityArtifactDefinition.artifact_type == normalize_artifact_type(artifact_type))
    definitions = query.order_by(
        ProcessActivityArtifactDefinition.artifact_type.asc(),
        ProcessActivityArtifactDefinition.name.asc(),
        ProcessActivityArtifactDefinition.version.desc(),
    ).all()
    return [build_definition_snapshot(definition) for definition in definitions]


def list_published_process_artifacts(
    company_id: int,
    process_id: int,
    *,
    artifact_types: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Lista a versao publicada mais recente de cada artefato do processo.

    Esta leitura e destinada a superficies operacionais/publicadas. Rascunhos e
    versoes arquivadas nunca devem chegar ao Portal do Processo ou ao POP.
    """
    _get_process(company_id, process_id)
    normalized_types = None
    if artifact_types is not None:
        normalized_types = {normalize_artifact_type(value) for value in artifact_types}

    query = ProcessActivityArtifactDefinition.query.filter_by(
        company_id=company_id,
        process_id=process_id,
        status="published",
    )
    if normalized_types:
        query = query.filter(ProcessActivityArtifactDefinition.artifact_type.in_(normalized_types))

    definitions = query.order_by(
        ProcessActivityArtifactDefinition.artifact_key.asc(),
        ProcessActivityArtifactDefinition.version.desc(),
        ProcessActivityArtifactDefinition.id.desc(),
    ).all()
    latest_by_key: dict[str, ProcessActivityArtifactDefinition] = {}
    for definition in definitions:
        latest_by_key.setdefault(str(definition.artifact_key), definition)

    selected = sorted(
        latest_by_key.values(),
        key=lambda item: (item.artifact_type, item.name.lower(), -item.version, -item.id),
    )
    return [build_definition_snapshot(definition) for definition in selected]


def link_artifact_to_activity(
    company_id: int,
    process_id: int,
    definition_id: int,
    payload: dict[str, Any],
    *,
    commit: bool = True,
) -> ProcessActivityArtifactLink:
    _get_process(company_id, process_id)
    definition = _get_definition(company_id, process_id, definition_id)
    bpmn_element_id = _clean_text(
        payload.get("bpmn_element_id"),
        field="bpmn_element_id",
        required=True,
    )
    completion_policy = payload.get("completion_policy_json") or {}
    if not isinstance(completion_policy, dict):
        raise ProcessArtifactValidationError("completion_policy_json deve ser um objeto.")
    display_order = int(payload.get("display_order") or 0)
    if display_order < 0:
        raise ProcessArtifactValidationError("display_order não pode ser negativo.")

    existing = ProcessActivityArtifactLink.query.filter_by(
        company_id=company_id,
        process_id=process_id,
        bpmn_element_id=bpmn_element_id,
        artifact_definition_id=definition.id,
    ).first()
    if existing:
        existing.display_order = display_order
        existing.is_required = bool(payload.get("is_required", existing.is_required))
        existing.completion_policy_json = completion_policy or existing.completion_policy_json or {}
        existing.is_active = bool(payload.get("is_active", True))
        link = existing
    else:
        link = ProcessActivityArtifactLink(
            company_id=company_id,
            process_id=process_id,
            bpmn_element_id=bpmn_element_id,
            artifact_definition_id=definition.id,
            display_order=display_order,
            is_required=bool(payload.get("is_required", False)),
            completion_policy_json=completion_policy,
            is_active=bool(payload.get("is_active", True)),
        )
        db.session.add(link)

    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return link


def build_definition_snapshot(definition: ProcessActivityArtifactDefinition) -> dict[str, Any]:
    """Gera o snapshot imutável usado por uma instância futura."""
    payload = definition.to_dict()
    activity_links = getattr(definition, "activity_links", None)
    if activity_links is not None:
        active_links = activity_links.filter_by(
            is_active=True,
            company_id=definition.company_id,
            process_id=definition.process_id,
        ).order_by(
            ProcessActivityArtifactLink.display_order.asc(),
            ProcessActivityArtifactLink.id.asc(),
        ).all()
        payload["activity_links"] = [link.to_dict(include_definition=False) for link in active_links]
    else:
        payload["activity_links"] = []
    legacy_routine = getattr(definition, "legacy_process_routine", None)
    if definition.artifact_type == "pop" and legacy_routine:
        payload["name"] = legacy_routine.name
        payload["description"] = legacy_routine.description
        payload["legacy_pop"] = {
            "process_routine_id": legacy_routine.id,
            "code": legacy_routine.code,
            "name": legacy_routine.name,
            "description": legacy_routine.description,
            "bpmn_element_id": legacy_routine.bpmn_element_id,
            "bpmn_element_type": legacy_routine.bpmn_element_type,
            "bpmn_data_objects": legacy_routine.bpmn_data_objects or [],
        }
    return payload


def serialize_artifact_link(link: ProcessActivityArtifactLink) -> dict[str, Any]:
    payload = link.to_dict(include_definition=False)
    payload["artifact"] = build_definition_snapshot(link.artifact_definition)
    return payload


def ensure_pop_artifact_for_routine(
    routine: ProcessRoutine,
    *,
    commit: bool = True,
) -> tuple[ProcessActivityArtifactDefinition, ProcessActivityArtifactLink | None, bool]:
    """Adapta um ProcessRoutine existente ao catálogo genérico sem duplicá-lo."""
    if not routine or not routine.id:
        raise ProcessArtifactValidationError("POP persistido é obrigatório.")
    if not routine.company_id or not routine.process_id:
        raise ProcessArtifactValidationError("POP sem tenant/processo válido.")

    definition = ProcessActivityArtifactDefinition.query.filter_by(
        company_id=routine.company_id,
        process_id=routine.process_id,
        legacy_process_routine_id=routine.id,
        version=1,
    ).first()
    created = False
    if not definition:
        definition = create_artifact_definition(
            routine.company_id,
            routine.process_id,
            {
                "artifact_key": f"legacy-pop-{routine.id}",
                "artifact_type": "pop",
                "name": routine.name,
                "description": routine.description,
                "version": 1,
                "status": "published",
                "legacy_process_routine_id": routine.id,
                "configuration_json": {
                    "adapter": "process_routine",
                    "process_routine_id": routine.id,
                    "code": routine.code,
                    "bpmn_element_type": routine.bpmn_element_type,
                },
            },
            commit=False,
        )
        created = True

    link = None
    if _clean_text(routine.bpmn_element_id):
        link = link_artifact_to_activity(
            routine.company_id,
            routine.process_id,
            definition.id,
            {
                "bpmn_element_id": routine.bpmn_element_id,
                "display_order": routine.order_index or 0,
                "is_required": False,
                "completion_policy_json": {
                    "mode": "available",
                    "acknowledgement_required": False,
                },
            },
            commit=False,
        )

    if commit:
        db.session.commit()
    return definition, link, created


def list_activity_artifacts(company_id: int, process_id: int, bpmn_element_id: str) -> list[dict[str, Any]]:
    _get_process(company_id, process_id)
    element_id = _clean_text(bpmn_element_id, field="bpmn_element_id", required=True)
    links = (
        ProcessActivityArtifactLink.query.join(
            ProcessActivityArtifactDefinition,
            ProcessActivityArtifactDefinition.id == ProcessActivityArtifactLink.artifact_definition_id,
        )
        .filter(
            ProcessActivityArtifactLink.company_id == company_id,
            ProcessActivityArtifactLink.process_id == process_id,
            ProcessActivityArtifactLink.bpmn_element_id == element_id,
            ProcessActivityArtifactLink.is_active.is_(True),
            ProcessActivityArtifactDefinition.company_id == company_id,
            ProcessActivityArtifactDefinition.process_id == process_id,
            ProcessActivityArtifactDefinition.status == "published",
        )
        .order_by(ProcessActivityArtifactLink.display_order.asc(), ProcessActivityArtifactLink.id.asc())
        .all()
    )
    return [serialize_artifact_link(link) for link in links]


def materialize_activity_artifacts(
    company_id: int,
    activity_execution_id: int,
    *,
    commit: bool = True,
) -> list[ProcessActivityArtifactExecution]:
    activity = ProcessInstanceExecution.query.filter_by(
        id=activity_execution_id,
        company_id=company_id,
    ).first()
    if not activity:
        raise ProcessArtifactValidationError("Execução de atividade não encontrada para este tenant.")

    links = (
        ProcessActivityArtifactLink.query.join(
            ProcessActivityArtifactDefinition,
            ProcessActivityArtifactDefinition.id == ProcessActivityArtifactLink.artifact_definition_id,
        )
        .filter(
            ProcessActivityArtifactLink.company_id == company_id,
            ProcessActivityArtifactLink.process_id == activity.process_id,
            ProcessActivityArtifactLink.bpmn_element_id == activity.bpmn_element_id,
            ProcessActivityArtifactLink.is_active.is_(True),
            ProcessActivityArtifactDefinition.company_id == company_id,
            ProcessActivityArtifactDefinition.process_id == activity.process_id,
            ProcessActivityArtifactDefinition.status == "published",
        )
        .order_by(ProcessActivityArtifactLink.display_order.asc(), ProcessActivityArtifactLink.id.asc())
        .all()
    )

    materialized: list[ProcessActivityArtifactExecution] = []
    for link in links:
        definition = link.artifact_definition
        execution = ProcessActivityArtifactExecution.query.filter_by(
            company_id=company_id,
            activity_execution_id=activity.id,
            artifact_definition_id=definition.id,
        ).first()
        if not execution:
            snapshot = build_definition_snapshot(definition)
            snapshot["link"] = {
                "link_id": link.id,
                "display_order": link.display_order,
                "is_required": bool(link.is_required),
                "completion_policy_json": link.completion_policy_json or {},
            }
            execution = ProcessActivityArtifactExecution(
                company_id=company_id,
                process_instance_id=activity.process_instance_id,
                activity_execution_id=activity.id,
                artifact_definition_id=definition.id,
                artifact_key=definition.artifact_key,
                artifact_type=definition.artifact_type,
                artifact_version=definition.version,
                definition_snapshot_json=snapshot,
                status="pending",
                input_json={},
                output_json={},
                evidence_json={},
                error_json={},
            )
            db.session.add(execution)
        materialized.append(execution)

    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return materialized


def build_activity_artifacts_runtime_payload(
    company_id: int,
    process_id: int,
    bpmn_element_id: str | None,
    *,
    activity_execution_id: int | None = None,
) -> dict[str, Any]:
    element_id = _clean_text(bpmn_element_id)
    if not element_id:
        return {
            "items": [],
            "completion": evaluate_required_artifacts([]),
        }

    if activity_execution_id:
        executions = (
            ProcessActivityArtifactExecution.query
            .filter_by(company_id=company_id, activity_execution_id=activity_execution_id)
            .order_by(ProcessActivityArtifactExecution.id.asc())
            .all()
        )
        items = []
        for execution in executions:
            snapshot = execution.definition_snapshot_json or {}
            link_snapshot = snapshot.get("link") or {}
            items.append({
                **execution.to_dict(),
                "name": snapshot.get("name") or execution.artifact_type.upper(),
                "description": snapshot.get("description"),
                "configuration_json": snapshot.get("configuration_json") or {},
                "is_required": bool(link_snapshot.get("is_required")),
                "completion_policy_json": link_snapshot.get("completion_policy_json") or {},
            })
        return {
            "items": items,
            "completion": evaluate_required_artifacts(executions),
        }

    links = (
        ProcessActivityArtifactLink.query.join(
            ProcessActivityArtifactDefinition,
            ProcessActivityArtifactDefinition.id == ProcessActivityArtifactLink.artifact_definition_id,
        )
        .filter(
            ProcessActivityArtifactLink.company_id == company_id,
            ProcessActivityArtifactLink.process_id == process_id,
            ProcessActivityArtifactLink.bpmn_element_id == element_id,
            ProcessActivityArtifactLink.is_active.is_(True),
            ProcessActivityArtifactDefinition.company_id == company_id,
            ProcessActivityArtifactDefinition.process_id == process_id,
            ProcessActivityArtifactDefinition.status == "published",
        )
        .order_by(ProcessActivityArtifactLink.display_order.asc(), ProcessActivityArtifactLink.id.asc())
        .all()
    )
    items = []
    gate_proxies = []
    for link in links:
        snapshot = build_definition_snapshot(link.artifact_definition)
        snapshot["link"] = {
            "link_id": link.id,
            "display_order": link.display_order,
            "is_required": bool(link.is_required),
            "completion_policy_json": link.completion_policy_json or {},
        }
        items.append({
            "id": None,
            "artifact_definition_id": link.artifact_definition_id,
            "artifact_key": link.artifact_definition.artifact_key,
            "artifact_type": link.artifact_definition.artifact_type,
            "artifact_version": link.artifact_definition.version,
            "name": snapshot.get("name"),
            "description": snapshot.get("description"),
            "configuration_json": snapshot.get("configuration_json") or {},
            "definition_snapshot_json": snapshot,
            "status": "pending",
            "is_required": bool(link.is_required),
            "completion_policy_json": link.completion_policy_json or {},
            "output_json": {},
            "evidence_json": {},
        })
        gate_proxies.append(
            SimpleNamespace(
                id=link.id,
                status="pending",
                definition_snapshot_json=snapshot,
            )
        )
    return {
        "items": items,
        "completion": evaluate_required_artifacts(gate_proxies),
    }


def get_artifact_execution(company_id: int, artifact_execution_id: int) -> ProcessActivityArtifactExecution:
    execution = ProcessActivityArtifactExecution.query.filter_by(
        id=artifact_execution_id,
        company_id=company_id,
    ).first()
    if not execution:
        raise ProcessArtifactValidationError("Execução de artefato não encontrada para este tenant.")
    return execution


def _is_answered(value: Any) -> bool:
    return value not in (None, "", [], {})


def _validate_form_submission(execution: ProcessActivityArtifactExecution, output: dict[str, Any]) -> None:
    answers = output.get("answers") or {}
    if not isinstance(answers, dict):
        raise ProcessArtifactValidationError("answers deve ser um objeto.")
    config = (execution.definition_snapshot_json or {}).get("configuration_json") or {}
    for section in config.get("sections") or []:
        for field in section.get("fields") or []:
            if field.get("required") and not _is_answered(answers.get(field.get("id"))):
                raise ProcessArtifactValidationError(f"Campo obrigatório não preenchido: {field.get('label')}.")


def _validate_check_submission(
    execution: ProcessActivityArtifactExecution,
    output: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    answers = output.get("answers") or {}
    if not isinstance(answers, dict):
        raise ProcessArtifactValidationError("answers deve ser um objeto.")
    config = (execution.definition_snapshot_json or {}).get("configuration_json") or {}
    for item in config.get("items") or []:
        item_id = item.get("id")
        answer = answers.get(item_id) or {}
        if not isinstance(answer, dict):
            raise ProcessArtifactValidationError(f"Resposta inválida para: {item.get('label')}.")
        answer_status = _clean_text(answer.get("status"))
        if item.get("required") and answer_status not in {"accepted", "rejected", "na"}:
            raise ProcessArtifactValidationError(f"Item obrigatório não respondido: {item.get('label')}.")
        if answer_status == "na" and not item.get("allow_na"):
            raise ProcessArtifactValidationError(f"Item não permite N/A: {item.get('label')}.")
        if item.get("evidence_required") and answer_status == "accepted" and not _is_answered(evidence.get(item_id)):
            raise ProcessArtifactValidationError(f"Evidência obrigatória ausente: {item.get('label')}.")
        if answer_status == "rejected" and config.get("failure_behavior", "block") == "block":
            raise ProcessArtifactValidationError(f"Item reprovado bloqueia a conclusão: {item.get('label')}.")


def update_artifact_execution(
    company_id: int,
    artifact_execution_id: int,
    payload: dict[str, Any],
) -> ProcessActivityArtifactExecution:
    execution = get_artifact_execution(company_id, artifact_execution_id)
    status = normalize_execution_status(payload.get("status") or execution.status)
    if execution.status in {"completed", "skipped"}:
        raise ProcessArtifactValidationError("Documento concluído é somente leitura e não pode ser alterado.")
    output = payload.get("output_json") if "output_json" in payload else execution.output_json or {}
    evidence = payload.get("evidence_json") if "evidence_json" in payload else execution.evidence_json or {}
    if not isinstance(output, dict) or not isinstance(evidence, dict):
        raise ProcessArtifactValidationError("output_json e evidence_json devem ser objetos.")
    if status == "completed":
        if execution.artifact_type == "form":
            _validate_form_submission(execution, output)
        elif execution.artifact_type == "check":
            _validate_check_submission(execution, output, evidence)

    execution.output_json = output
    execution.evidence_json = evidence
    execution.status = status
    if status == "in_progress" and not execution.started_at:
        execution.started_at = datetime.utcnow()
    if status == "completed":
        execution.started_at = execution.started_at or datetime.utcnow()
        execution.completed_at = datetime.utcnow()
        execution.error_json = {}
    db.session.commit()
    return execution


def evaluate_required_artifacts(executions: Iterable[Any]) -> dict[str, Any]:
    """Avalia o gate usando apenas snapshots, facilitando runtime e testes."""
    required_total = 0
    required_completed = 0
    blocking_ids: list[int] = []
    for execution in executions:
        snapshot = getattr(execution, "definition_snapshot_json", None) or {}
        link_snapshot = snapshot.get("link") or {}
        if not bool(link_snapshot.get("is_required")):
            continue
        required_total += 1
        status = normalize_execution_status(getattr(execution, "status", None) or "pending")
        completion_policy = link_snapshot.get("completion_policy_json") or {}
        skip_is_allowed = status == "skipped" and bool(completion_policy.get("allow_skip"))
        if status == "completed" or skip_is_allowed:
            required_completed += 1
        else:
            execution_id = getattr(execution, "id", None)
            if execution_id is not None:
                blocking_ids.append(execution_id)

    return {
        "required_total": required_total,
        "required_completed": required_completed,
        "activity_may_complete": required_completed == required_total,
        "blocking_artifact_execution_ids": blocking_ids,
    }
