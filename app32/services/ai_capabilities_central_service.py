from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_

from database.postgresql_db import list_integrations
from models import (
    db,
    AICapability,
    AICapabilityAuditLog,
    AICapabilityCompanySetting,
    AICapabilityGrant,
    Company,
    Employee,
    FinancialDomainEnablement,
    FinancialIngestionRecord,
    User,
    WorkflowExecutionLog,
)


class AICapabilitiesCentralService:
    """Serviço operacional da Central de Capacidades de IA."""

    CORE_CAPABILITIES: tuple[dict[str, Any], ...] = (
        {
            "key": "financial.receipt_photo_ingestion",
            "name": "Comprovante por foto",
            "description": "Recebe imagem do comprovante e encaminha para o fluxo financeiro correto.",
            "domain": "Financeiro",
            "capability_type": "workflow",
            "risk_level": "medium",
            "status": "pilot",
            "rollout_status": "pilot",
            "origin": "system",
            "source_ref": "financial_ingestion_records",
            "requires_human_gate": True,
            "requires_active_company": True,
            "requires_user_binding": True,
            "supported_channels_json": ["web", "whatsapp"],
            "supported_surfaces_json": ["user", "admin"],
            "technical_binding_json": {"workflow_key": "financial.receipt_photo_ingestion"},
            "default_settings_json": {
                "processamento_automatico": "assistido",
                "exigir_aprovacao_humana": True,
                "limite_sem_aprovacao": "350.00",
            },
            "metadata_json": {},
        },
        {
            "key": "financial.classification_assistant",
            "name": "Assistente de classificação",
            "description": "Sugere categoria, centro de custo e projeto com apoio do histórico financeiro.",
            "domain": "Financeiro",
            "capability_type": "feature",
            "risk_level": "low",
            "status": "pilot",
            "rollout_status": "pilot",
            "origin": "system",
            "source_ref": "financial.classification_assistant",
            "requires_human_gate": False,
            "requires_active_company": True,
            "requires_user_binding": True,
            "supported_channels_json": ["web"],
            "supported_surfaces_json": ["user", "analytics"],
            "technical_binding_json": {"feature_flag": "financial.classification_assistant"},
            "default_settings_json": {"modo": "assistido", "sugerir_centro_custo": True},
            "metadata_json": {},
        },
        {
            "key": "meetings.minutes_draft",
            "name": "Minuta automática de reunião",
            "description": "Gera minuta estruturada com decisões e responsáveis.",
            "domain": "Reuniões",
            "capability_type": "tool",
            "risk_level": "low",
            "status": "active",
            "rollout_status": "active",
            "origin": "system",
            "source_ref": "meetings.minutes_draft",
            "requires_human_gate": False,
            "requires_active_company": True,
            "requires_user_binding": True,
            "supported_channels_json": ["web"],
            "supported_surfaces_json": ["user"],
            "technical_binding_json": {"entrypoint": "/meetings/manage-v2"},
            "default_settings_json": {"incluir_encaminhamentos": True},
            "metadata_json": {},
        },
    )

    @classmethod
    def sync_catalog(cls) -> None:
        changed = False
        existing = {item.key: item for item in AICapability.query.all()}
        for payload in cls.CORE_CAPABILITIES:
            _, item_changed = cls._upsert_capability(existing, payload)
            changed = changed or item_changed
        for payload in cls._tool_manifest_capabilities():
            _, item_changed = cls._upsert_capability(existing, payload)
            changed = changed or item_changed
        if changed:
            db.session.commit()

    @classmethod
    def build_frontend_state(cls, active_company: Any | None = None) -> dict[str, Any]:
        cls.sync_catalog()
        company_id = getattr(active_company, "id", None)
        company_name = getattr(active_company, "name", None) or "Sem empresa ativa"
        capabilities = AICapability.query.order_by(AICapability.domain.asc(), AICapability.name.asc()).all()
        selected = capabilities[0] if capabilities else None
        grants = AICapabilityGrant.query.all()

        return {
            "hero": cls._build_hero(capabilities, grants),
            "assistant": cls._build_assistant(),
            "tabs": cls._build_tabs(),
            "catalog": {"filters": cls._build_filters(capabilities), "items": [cls._serialize_capability(item, grants) for item in capabilities]},
            "availability": cls._build_availability(capabilities, grants, company_id, company_name, selected),
            "requirements": cls._build_requirements(selected, company_id, company_name),
            "rollout": cls._build_rollout(selected, company_id),
            "audit": {"events": cls._load_audit_events(getattr(selected, "id", None), company_id)},
            "sidebar": cls._build_sidebar(selected, company_name, grants),
            "options": cls._build_options(company_id),
        }

    @classmethod
    def upsert_grant(cls, payload: dict[str, Any], *, actor_user_id: int | None = None) -> AICapabilityGrant:
        capability = cls._get_capability_or_raise(payload["capability_key"])
        grant = AICapabilityGrant.query.filter_by(
            capability_id=capability.id,
            scope_type=payload["scope_type"],
            company_id=payload.get("company_id"),
            user_id=payload.get("user_id"),
            role_id=payload.get("role_id"),
        ).first()
        created = False
        if not grant:
            grant = AICapabilityGrant(
                capability_id=capability.id,
                scope_type=payload["scope_type"],
                company_id=payload.get("company_id"),
                user_id=payload.get("user_id"),
                role_id=payload.get("role_id"),
            )
            db.session.add(grant)
            created = True
        grant.is_enabled = bool(payload.get("is_enabled", True))
        grant.channels_json = list(payload.get("channels") or [])
        grant.notes = payload.get("notes")
        grant.valid_from = payload.get("valid_from")
        grant.valid_until = payload.get("valid_until")
        grant.created_by_user_id = actor_user_id
        db.session.flush()
        cls.record_audit_event(
            capability_key=capability.key,
            event_type="grant_created" if created else "grant_updated",
            result="success",
            company_id=grant.company_id,
            user_id=grant.user_id,
            actor_user_id=actor_user_id,
            detail=f"Grant {grant.scope_type} {'habilitado' if grant.is_enabled else 'bloqueado'}.",
            payload={"scope_type": grant.scope_type, "is_enabled": grant.is_enabled},
            commit=False,
        )
        db.session.commit()
        return grant

    @classmethod
    def upsert_company_settings(cls, payload: dict[str, Any], *, actor_user_id: int | None = None) -> AICapabilityCompanySetting:
        capability = cls._get_capability_or_raise(payload["capability_key"])
        record = AICapabilityCompanySetting.query.filter_by(
            capability_id=capability.id,
            company_id=payload["company_id"],
        ).first()
        created = False
        if not record:
            record = AICapabilityCompanySetting(capability_id=capability.id, company_id=payload["company_id"])
            db.session.add(record)
            created = True
        record.settings_json = dict(payload.get("settings") or {})
        record.is_enabled = bool(payload.get("is_enabled", True))
        record.updated_by_user_id = actor_user_id
        db.session.flush()
        cls.record_audit_event(
            capability_key=capability.key,
            event_type="company_settings_created" if created else "company_settings_updated",
            result="success",
            company_id=record.company_id,
            actor_user_id=actor_user_id,
            detail="Parâmetros por empresa atualizados.",
            payload={"settings": record.settings_json, "is_enabled": record.is_enabled},
            commit=False,
        )
        db.session.commit()
        return record

    @classmethod
    def update_rollout(cls, payload: dict[str, Any], *, actor_user_id: int | None = None) -> AICapability:
        capability = cls._get_capability_or_raise(payload["capability_key"])
        capability.rollout_status = payload["rollout_status"]
        if payload.get("status"):
            capability.status = payload["status"]
        capability.approved_by_user_id = actor_user_id
        capability.approved_at = datetime.utcnow()
        db.session.flush()
        cls.record_audit_event(
            capability_key=capability.key,
            event_type="rollout_updated",
            result="success",
            actor_user_id=actor_user_id,
            detail=f"Rollout alterado para {capability.rollout_status}.",
            payload={"status": capability.status, "notes": payload.get("notes")},
            commit=False,
        )
        db.session.commit()
        return capability

    @classmethod
    def record_audit_event(
        cls,
        *,
        capability_key: str,
        event_type: str,
        result: str = "success",
        company_id: int | None = None,
        user_id: int | None = None,
        actor_user_id: int | None = None,
        channel: str | None = None,
        surface: str | None = None,
        detail: str | None = None,
        payload: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> AICapabilityAuditLog:
        capability = AICapability.query.filter_by(key=capability_key).first()
        log = AICapabilityAuditLog(
            capability_id=getattr(capability, "id", None),
            company_id=company_id,
            user_id=user_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            result=result,
            channel=channel,
            surface=surface,
            detail=detail,
            payload_json=dict(payload or {}),
        )
        db.session.add(log)
        if commit:
            db.session.commit()
        return log

    @classmethod
    def _upsert_capability(cls, existing: dict[str, AICapability], payload: dict[str, Any]) -> tuple[AICapability, bool]:
        capability = existing.get(payload["key"])
        created = False
        if capability is None:
            capability = AICapability(key=payload["key"])
            db.session.add(capability)
            existing[payload["key"]] = capability
            created = True
        if not created and capability.origin == "manual":
            return capability, False
        changed = created
        for field in (
            "name",
            "description",
            "domain",
            "capability_type",
            "risk_level",
            "status",
            "rollout_status",
            "origin",
            "source_ref",
            "requires_human_gate",
            "requires_active_company",
            "requires_user_binding",
            "technical_binding_json",
            "supported_channels_json",
            "supported_surfaces_json",
            "default_settings_json",
            "metadata_json",
        ):
            new_value = payload.get(field)
            if getattr(capability, field) != new_value:
                setattr(capability, field, new_value)
                changed = True
        if created:
            db.session.flush()
            cls.record_audit_event(
                capability_key=payload["key"],
                event_type="capability_registered",
                result="success",
                detail="Capacidade registrada automaticamente pelo sistema.",
                payload={"origin": payload.get("origin"), "source_ref": payload.get("source_ref")},
                commit=False,
            )
        return capability, changed

    @classmethod
    def _tool_manifest_capabilities(cls) -> list[dict[str, Any]]:
        try:
            from src.intelligence.tool_catalog import catalog

            manifest = catalog.get_capability_manifest(include_tools=True)
            tools = list(manifest.get("tools", []))
        except Exception:
            return []

        capabilities: list[dict[str, Any]] = []
        for tool in tools:
            tool_name = str(tool.get("name") or "").strip()
            if not tool_name:
                continue
            supported_surfaces = list(tool.get("surfaces") or [])
            if not supported_surfaces and tool.get("surface"):
                supported_surfaces = [str(tool.get("surface"))]
            capabilities.append(
                {
                    "key": f"tool.{tool_name}",
                    "name": str(tool.get("title") or tool.get("label") or tool_name.replace("_", " ").title()),
                    "description": str(tool.get("description") or "Tool MCP sincronizada automaticamente."),
                    "domain": str(tool.get("domain") or "General"),
                    "capability_type": "tool",
                    "risk_level": str(tool.get("risk") or "medium"),
                    "status": "active",
                    "rollout_status": "active",
                    "origin": "system",
                    "source_ref": tool_name,
                    "requires_human_gate": bool(tool.get("human_gate")),
                    "requires_active_company": True,
                    "requires_user_binding": True,
                    "technical_binding_json": {"tool_name": tool_name, "mcp_enabled": True},
                    "supported_channels_json": list(tool.get("channels") or []),
                    "supported_surfaces_json": supported_surfaces,
                    "default_settings_json": {},
                    "metadata_json": {"tool_tags": list(tool.get("tags") or [])},
                }
            )
        return capabilities

    @classmethod
    def _build_assistant(cls) -> dict[str, Any]:
        return {
            "title": "Comece por aqui",
            "intro": "Escolha o movimento que você precisa agora para o APP32 te levar ao bloco certo.",
            "steps": [
                {
                    "step": 1,
                    "question": "O que você quer fazer agora?",
                    "options": [
                        {"label": "Liberar uso", "description": "Habilitar capacidade para empresa ou usuário.", "target_tab": "availability", "result_title": "Abra Disponibilização", "result_body": "Use a visão por capacidade, empresa ou usuário para conceder ou revogar acesso."},
                        {"label": "Configurar empresa", "description": "Ajustar parâmetros e validar pré-requisitos.", "target_tab": "requirements", "result_title": "Abra Pré-requisitos e Configuração", "result_body": "Valide dependências operacionais e ajuste parâmetros por empresa."},
                        {"label": "Revisar rollout", "description": "Mover entre piloto, ativo, pausado e bloqueado.", "target_tab": "rollout", "result_title": "Abra Rollout", "result_body": "Controle a expansão com leitura de risco, uso e saúde operacional."},
                        {"label": "Auditar uso", "description": "Ver quem liberou, quem usou e quem foi bloqueado.", "target_tab": "audit", "result_title": "Abra Auditoria", "result_body": "Confira a timeline completa com trilha de decisão e eventos operacionais."},
                    ],
                }
            ],
        }

    @staticmethod
    def _build_tabs() -> list[dict[str, str]]:
        return [
            {"key": "catalog", "title": "Catálogo", "eyebrow": "O que existe", "description": ""},
            {"key": "availability", "title": "Disponibilização", "eyebrow": "Quem pode usar", "description": ""},
            {"key": "requirements", "title": "Pré-requisitos e Configuração", "eyebrow": "O que precisa estar pronto", "description": ""},
            {"key": "rollout", "title": "Rollout", "eyebrow": "Como está sendo expandido", "description": ""},
            {"key": "audit", "title": "Auditoria", "eyebrow": "Quem fez o quê", "description": ""},
        ]

    @staticmethod
    def _build_filters(capabilities: list[AICapability]) -> dict[str, list[str]]:
        return {
            "domains": sorted({item.domain for item in capabilities}) or ["Financeiro"],
            "types": sorted({item.capability_type for item in capabilities}) or ["workflow"],
            "risk_levels": sorted({item.risk_level for item in capabilities}) or ["medium"],
        }

    @classmethod
    def _build_hero(cls, capabilities: list[AICapability], grants: list[AICapabilityGrant]) -> dict[str, Any]:
        active_company_ids = {item.company_id for item in grants if item.is_enabled and item.company_id is not None}
        enabled_user_ids = {item.user_id for item in grants if item.is_enabled and item.user_id is not None}
        pending_critical = sum(1 for item in capabilities if item.rollout_status in {"blocked", "paused"} or item.status in {"paused", "retired"})
        return {
            "eyebrow": "Sistema · IA Corporativa",
            "title": "Central de Capacidades de IA",
            "description": "Controle catálogo, disponibilização, pré-requisitos, parâmetros por empresa, rollout e auditoria da camada de IA.",
            "metrics": [
                {"label": "Capacidades ativas", "value": sum(1 for item in capabilities if item.status == "active")},
                {"label": "Empresas em rollout", "value": len(active_company_ids)},
                {"label": "Usuários liberados", "value": len(enabled_user_ids)},
                {"label": "Pendências críticas", "value": pending_critical},
            ],
            "quick_actions": [
                {"title": "Revisar disponibilização", "description": "Ir direto para grants por empresa e usuário.", "target_tab": "availability"},
                {"title": "Ver pré-requisitos", "description": "Conferir o que ainda impede uso operacional.", "target_tab": "requirements"},
                {"title": "Controlar rollout", "description": "Piloto, ativo, pausado e bloqueado.", "target_tab": "rollout"},
                {"title": "Abrir auditoria", "description": "Linha do tempo de liberações, bloqueios e uso.", "target_tab": "audit"},
            ],
        }

    @classmethod
    def _serialize_capability(cls, item: AICapability, grants: list[AICapabilityGrant]) -> dict[str, Any]:
        related_grants = [grant for grant in grants if grant.capability_id == item.id and grant.is_enabled]
        company_names = sorted({grant.company.name for grant in related_grants if grant.company is not None and getattr(grant.company, "name", None)})
        badges = [item.capability_type, item.domain.lower()]
        badges.extend(list(item.supported_channels_json or []))
        badges.extend(list(item.supported_surfaces_json or []))
        if item.requires_human_gate:
            badges.append("human gate")
        return {
            "key": item.key,
            "name": item.name,
            "domain": item.domain,
            "type": item.capability_type,
            "risk": item.risk_level,
            "status": item.status,
            "origin": item.origin,
            "description": item.description or "Sem descrição.",
            "badges": badges,
            "notes": f"Liberada para {', '.join(company_names[:3])}." if company_names else "Ainda sem grants configurados.",
        }

    @classmethod
    def _build_availability(
        cls,
        capabilities: list[AICapability],
        grants: list[AICapabilityGrant],
        company_id: int | None,
        company_name: str,
        selected: AICapability | None,
    ) -> dict[str, Any]:
        selected_grants = [item for item in grants if selected and item.capability_id == selected.id]
        selected_company_grant = next((item for item in selected_grants if item.company_id == company_id and item.scope_type == "company"), None)
        by_capability_cards = []
        for item in capabilities[:6]:
            related = [grant for grant in grants if grant.capability_id == item.id and grant.is_enabled]
            companies = {grant.company_id for grant in related if grant.company_id}
            users = {grant.user_id for grant in related if grant.user_id}
            channels = sorted({channel for grant in related for channel in (grant.channels_json or [])})
            by_capability_cards.append({
                "title": item.key,
                "meta": f"{item.domain} · {item.capability_type} · risco {item.risk_level}",
                "status": item.status,
                "chips": [f"{len(companies)} empresas", f"{len(users)} usuários"] + channels[:2],
                "description": item.description or "Sem descrição operacional.",
            })

        company_cards = []
        company_ids = sorted({grant.company_id for grant in grants if grant.company_id})[:6]
        if company_id and company_id not in company_ids:
            company_ids.insert(0, company_id)
        for item_company_id in company_ids:
            company = Company.query.get(item_company_id)
            if not company:
                continue
            related = [grant for grant in grants if grant.company_id == item_company_id and grant.is_enabled]
            company_cards.append({
                "title": company.name,
                "meta": f"company_id={company.id}",
                "status": "active" if related else "blocked",
                "chips": [f"{len({grant.capability_id for grant in related})} capacidades", f"{len({grant.user_id for grant in related if grant.user_id})} usuários", f"{cls._count_pending_requirements(item_company_id)} pendências"],
                "description": "Disponibilização consolidada por grants explícitos na central.",
            })

        employees_query = Employee.query.filter_by(company_id=company_id, status="active") if company_id else Employee.query.filter_by(status="active")
        user_cards = []
        for employee in employees_query.limit(6).all():
            user = User.query.get(employee.user_id) if employee.user_id else None
            if not user:
                continue
            user_grants = [grant for grant in grants if grant.user_id == user.id]
            denied = any(not grant.is_enabled for grant in user_grants)
            allowed = any(grant.is_enabled for grant in user_grants)
            user_cards.append({
                "title": user.name,
                "meta": f"{company_name} · {'interno' if employee.user_id else 'externo'} · {employee.department or 'sem departamento'}",
                "status": "blocked" if denied else "active" if allowed else "pilot",
                "chips": [f"{len({grant.capability_id for grant in user_grants if grant.is_enabled})} capabilities", "web", "whatsapp" if (employee.whatsapp or user.whatsapp) else "sem whatsapp"],
                "description": "Usuário com deny explícito." if denied else "Usuário com allow explícito." if allowed else "Usuário depende da regra herdada da empresa/cargo.",
            })

        return {
            "selected_capability_key": selected.key if selected else "",
            "selected_context": {
                "title": selected.name if selected else "Nenhuma capacidade",
                "subtitle": selected.description if selected else "Sem capacidade selecionada",
                "company": company_name,
                "effective_rule": cls._describe_effective_rule(selected_company_grant, selected_grants),
                "surfaces": list(selected.supported_surfaces_json or []) if selected else [],
                "status": selected.status if selected else "draft",
            },
            "views": [
                {"title": "Por capacidade", "summary": "Veja para quais empresas e usuários cada capacidade está liberada.", "cards": by_capability_cards},
                {"title": "Por empresa", "summary": "Entenda rapidamente tudo o que a empresa pode usar.", "cards": company_cards},
                {"title": "Por usuário", "summary": "Descubra o acesso efetivo do usuário e de onde ele vem.", "cards": user_cards},
            ],
            "precedence": ["deny explícito por usuário", "allow explícito por usuário", "deny explícito por empresa", "allow explícito por empresa", "allow por cargo/perfil", "fallback: negado"],
        }

    @classmethod
    def _build_requirements(cls, selected: AICapability | None, company_id: int | None, company_name: str) -> dict[str, Any]:
        checklist = []
        integrations_total = len(list_integrations() or [])
        checklist.append({
            "title": "Integração principal ativa",
            "status": "ok" if integrations_total > 0 else "danger",
            "detail": f"{integrations_total} integrações mapeadas no ecossistema." if integrations_total > 0 else "Nenhuma integração encontrada.",
            "action": "Abrir integrações",
            "href": "/channels",
        })

        valid_contacts = 0
        total_employees = 0
        if company_id:
            employees = Employee.query.filter_by(company_id=company_id, status="active").all()
            total_employees = len(employees)
            for employee in employees:
                if employee.whatsapp or employee.phone or employee.telegram:
                    valid_contacts += 1
        invalid_contacts = max(total_employees - valid_contacts, 0)
        checklist.append({
            "title": "Usuários com contato válido",
            "status": "ok" if invalid_contacts == 0 else "warning" if invalid_contacts <= 1 else "danger",
            "detail": f"{valid_contacts} usuários aptos em {company_name}." if invalid_contacts == 0 else f"{invalid_contacts} usuários sem canal válido para fluxos assistidos.",
            "action": "Ver usuários",
            "href": "/usuarios",
        })

        if company_id and selected and selected.domain.lower() == "financeiro":
            enabled_domains = FinancialDomainEnablement.query.filter_by(company_id=company_id, is_enabled=True).count()
            checklist.append({
                "title": "Módulo financeiro habilitado",
                "status": "ok" if enabled_domains > 0 else "warning",
                "detail": f"{enabled_domains} domínios habilitados para cruzamento financeiro." if enabled_domains > 0 else "Nenhum domínio financeiro habilitado para sugestão contextual.",
                "action": "Abrir domínios",
                "href": "/financial/domain-enablements",
            })
            ingestion_count = FinancialIngestionRecord.query.filter_by(company_id=company_id).count()
            checklist.append({
                "title": "Base operacional do fluxo",
                "status": "ok" if ingestion_count > 0 else "warning",
                "detail": f"{ingestion_count} registros de ingestão já passaram pelo pipeline." if ingestion_count > 0 else "Ainda não há ingestões financeiras registradas para esta empresa.",
                "action": "Abrir entradas",
                "href": "/financial/ingestions",
            })

        company_settings = dict(selected.default_settings_json or {}) if selected else {}
        if selected and company_id:
            record = AICapabilityCompanySetting.query.filter_by(capability_id=selected.id, company_id=company_id).first()
            if record:
                company_settings.update(record.settings_json or {})
        formatted_settings = [{"label": key.replace("_", " ").capitalize(), "value": cls._format_setting_value(value)} for key, value in company_settings.items()]
        return {"checklist": checklist, "company_settings": formatted_settings}

    @classmethod
    def _build_rollout(cls, selected: AICapability | None, company_id: int | None) -> dict[str, Any]:
        if not selected:
            return {"status": "draft", "status_label": "Sem capacidade selecionada", "owner": "-", "updated_at": "-", "steps": [], "summary_cards": []}
        steps_order = ["draft", "internal_test", "pilot", "active", "paused", "blocked"]
        current_index = steps_order.index(selected.rollout_status) if selected.rollout_status in steps_order else 0
        steps = []
        for idx, step in enumerate(steps_order[:5]):
            state = "done" if idx < current_index else "current" if idx == current_index else "upcoming"
            steps.append({"label": step.replace("_", " ").title(), "state": state})
        executions_query = WorkflowExecutionLog.query
        if company_id:
            executions_query = executions_query.filter(or_(WorkflowExecutionLog.company_id == company_id, WorkflowExecutionLog.company_id.is_(None)))
        executions = executions_query.order_by(WorkflowExecutionLog.created_at.desc()).limit(200).all()
        blocked_recent = sum(1 for item in cls._load_audit_events(selected.id, company_id) if item["result"] in {"warning", "danger"})
        failures = sum(1 for item in executions if item.status in {"failed", "blocked", "error"})
        return {
            "status": selected.rollout_status,
            "status_label": selected.rollout_status.replace("_", " ").title(),
            "owner": selected.approved_by.name if selected.approved_by else "Admin plataforma",
            "updated_at": selected.updated_at.strftime("%d/%m/%Y %H:%M") if selected.updated_at else "-",
            "steps": steps,
            "summary_cards": [
                {"label": "Empresas no rollout", "value": str(cls._count_enabled_companies(selected.id)), "tone": "primary"},
                {"label": "Usuários usando", "value": str(cls._count_enabled_users(selected.id)), "tone": "success"},
                {"label": "Bloqueios recentes", "value": str(blocked_recent), "tone": "warning"},
                {"label": "Falhas operacionais", "value": str(failures), "tone": "danger"},
            ],
        }

    @classmethod
    def _load_audit_events(cls, selected_id: int | None, company_id: int | None) -> list[dict[str, Any]]:
        query = AICapabilityAuditLog.query
        if selected_id:
            query = query.filter(AICapabilityAuditLog.capability_id == selected_id)
        if company_id:
            query = query.filter(or_(AICapabilityAuditLog.company_id == company_id, AICapabilityAuditLog.company_id.is_(None)))
        items = query.order_by(AICapabilityAuditLog.created_at.desc()).limit(20).all()
        return [{
            "when": item.created_at.strftime("%d/%m/%Y %H:%M") if item.created_at else "-",
            "event": item.event_type.replace("_", " ").capitalize(),
            "actor": item.actor_user.name if item.actor_user else "Sistema",
            "company": item.company.name if item.company else "Global",
            "result": item.result,
            "detail": item.detail or "Sem detalhe.",
        } for item in items]

    @classmethod
    def _build_sidebar(cls, selected: AICapability | None, company_name: str, grants: list[AICapabilityGrant]) -> dict[str, Any]:
        return {
            "search_placeholder": "Buscar capability, empresa, usuário ou evento...",
            "shortcuts": [
                {"label": "Catálogo", "tab": "catalog"},
                {"label": "Disponibilização", "tab": "availability"},
                {"label": "Pré-requisitos", "tab": "requirements"},
                {"label": "Rollout", "tab": "rollout"},
                {"label": "Auditoria", "tab": "audit"},
            ],
            "context": {
                "title": "Contexto selecionado",
                "items": [
                    {"label": "Capacidade foco", "value": selected.name if selected else "Nenhuma"},
                    {"label": "Empresa ativa", "value": company_name},
                    {"label": "Fonte catálogo", "value": "Sincronização automática"},
                    {"label": "Grants ativos", "value": sum(1 for item in grants if item.is_enabled)},
                ],
            },
        }

    @classmethod
    def _build_options(cls, active_company_id: int | None) -> dict[str, Any]:
        companies = Company.query.filter_by(is_active=True).order_by(Company.name.asc()).limit(100).all()
        employees_query = Employee.query.filter_by(status="active")
        if active_company_id:
            employees_query = employees_query.filter_by(company_id=active_company_id)
        employees = employees_query.order_by(Employee.name.asc()).limit(100).all()

        try:
            from models import Role

            roles_query = Role.query
            if active_company_id:
                roles_query = roles_query.filter_by(company_id=active_company_id)
            roles = roles_query.order_by(Role.title.asc()).limit(100).all()
        except Exception:
            roles = []

        return {
            "companies": [
                {"id": item.id, "label": item.name, "selected": item.id == active_company_id}
                for item in companies
            ],
            "users": [
                {
                    "id": item.user_id,
                    "label": f"{item.name} · {item.department or 'sem departamento'}",
                    "company_id": item.company_id,
                }
                for item in employees
                if item.user_id
            ],
            "roles": [
                {
                    "id": item.id,
                    "label": item.title,
                    "company_id": item.company_id,
                }
                for item in roles
            ],
        }

    @classmethod
    def _count_pending_requirements(cls, company_id: int) -> int:
        count = 0
        employees = Employee.query.filter_by(company_id=company_id, status="active").all()
        if not employees:
            count += 1
        if any(not (employee.whatsapp or employee.phone or employee.telegram) for employee in employees):
            count += 1
        return count

    @classmethod
    def _count_enabled_companies(cls, capability_id: int) -> int:
        return len({item.company_id for item in AICapabilityGrant.query.filter_by(capability_id=capability_id, is_enabled=True).all() if item.company_id})

    @classmethod
    def _count_enabled_users(cls, capability_id: int) -> int:
        return len({item.user_id for item in AICapabilityGrant.query.filter_by(capability_id=capability_id, is_enabled=True).all() if item.user_id})

    @classmethod
    def _describe_effective_rule(cls, selected_company_grant: AICapabilityGrant | None, selected_grants: list[AICapabilityGrant]) -> str:
        if any(item.scope_type == "user" and not item.is_enabled for item in selected_grants):
            return "deny por usuário"
        if any(item.scope_type == "user" and item.is_enabled for item in selected_grants):
            return "allow por usuário"
        if selected_company_grant and not selected_company_grant.is_enabled:
            return "deny por empresa"
        if selected_company_grant and selected_company_grant.is_enabled:
            return "allow por empresa"
        if any(item.scope_type == "role" and item.is_enabled for item in selected_grants):
            return "allow por cargo"
        return "fallback negado"

    @staticmethod
    def _format_setting_value(value: Any) -> str:
        if isinstance(value, bool):
            return "Sim" if value else "Não"
        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(item) for item in value) if value else "-"
        return str(value)

    @staticmethod
    def _get_capability_or_raise(capability_key: str) -> AICapability:
        capability = AICapability.query.filter_by(key=capability_key).first()
        if capability is None:
            raise ValueError(f"Capacidade não encontrada: {capability_key}")
        return capability
