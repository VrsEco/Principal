from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import has_app_context

from models import InstructionRegistryAuditLog, InstructionRegistryEntry, db
from src.intelligence.mcp_contracts.instruction_registry import (
    APP32_INSTRUCTION_REGISTRY_MANIFEST,
    InstructionBootstrapBundle,
    InstructionDocumentRef,
    InstructionRule,
)
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec
from services.squad_runtime_bootstrap_service import OFFICIAL_SQUAD_CLIENTE_AGENTS


class InstructionRegistryService:
    """Resolve bundles instrucionais mínimos com persistência remota, rollout e cache metadata."""

    SUPPORTED_RUNTIMES = {"squad_cliente", "squad_versus", "engineering"}
    SUPPORTED_CHANNELS = {"stable", "beta", "hotfix"}
    DEFAULT_CACHE_TTL_SECONDS = 1800
    DEFAULT_ENVIRONMENT = "production"
    CURRENT_BUNDLE_VERSION = "2026-08-28.3"

    _EXPERIENCE_LABELS = {
        "squad_cliente": "Sapiens Cliente",
        "squad_versus": "Sapiens Consultor",
        "engineering": "Sapiens Engenharia",
    }
    _AGENT_BY_HARNESS = {
        "harness_coordenador_cliente_v1": "SC-COORD",
        "harness_comercial_cliente_v1": "SC-COM",
        "harness_operacional_cliente_v1": "SC-OPS",
        "harness_admfin_cliente_v1": "SC-ADM",
        "harness_coordenador_versus_v1": "SV-COORD",
        "harness_business_architect_versus_v1": "SV-BUSINESS-ARCHITECT",
        "harness_coordenador_engenharia_v1": "SE-COORD",
    }
    _DOCS = {
        "paper": (
            "instruction_registry_bootstrap_remoto_squad_cliente",
            "Paper — Instruction Registry Remoto do Squad Cliente",
            "papers/paper_instruction_registry_bootstrap_remoto_squad_cliente_v1.md",
            "Registrar a tese, trade-offs e racional do bootstrap remoto.",
        ),
        "spec": (
            "arquitetura_instruction_registry_squad_cliente",
            "SPEC — Arquitetura do Instruction Registry do Squad Cliente",
            "spec/squad_cliente/arquitetura_instruction_registry_squad_cliente_v1.md",
            "Congelar o contrato oficial do registry, bundle mínimo e camadas de override.",
        ),
        "manifesto": (
            "instruction_registry_squad_cliente",
            "Manifesto — Instruction Registry do Squad Cliente",
            "manifestos/manifesto_oficial_instruction_registry_squad_cliente_v1.md",
            "Declarar princípios, limites e identidade do registry instrucional.",
        ),
        "playbook": (
            "bootstrap_instruction_registry_squad_cliente",
            "Playbook — Bootstrap do Instruction Registry do Squad Cliente",
            "playbooks/squad_cliente/playbook_bootstrap_instruction_registry_squad_cliente_v1.md",
            "Orientar como ativar, resolver, cachear e escalar o bundle.",
        ),
        "runbook": (
            "implantacao_instruction_registry_squad_cliente",
            "Runbook — Implantação do Instruction Registry do Squad Cliente",
            "runbooks/instalacao/runbook_implantacao_instruction_registry_squad_cliente_v1.md",
            "Executar implantação incremental, smoke e troubleshooting do registry.",
        ),
        "harness": (
            "instruction_registry_squad_cliente",
            "Harness — Instruction Registry do Squad Cliente",
            "harnesses/squad_cliente/harness_instruction_registry_squad_cliente_v1.md",
            "Empacotar como o resolvedor remoto deve iniciar, compor e devolver o bundle mínimo.",
        ),
    }

    @classmethod
    def _root_dir(cls) -> Path:
        return Path(__file__).resolve().parents[1]

    @classmethod
    def supports_runtime(cls, runtime_profile: str) -> bool:
        return str(runtime_profile or "").strip().lower() in cls.SUPPORTED_RUNTIMES

    @classmethod
    def supports_channel(cls, channel: str) -> bool:
        return str(channel or "").strip().lower() in cls.SUPPORTED_CHANNELS

    @classmethod
    def describe_registry(cls) -> dict:
        cls.sync_defaults()
        manifest = APP32_INSTRUCTION_REGISTRY_MANIFEST.model_dump(mode="json")
        manifest["admin_endpoints"] = {
            "frontend_state": "/api/configs/ai/mcp/instruction-registry/frontend-state",
            "upsert_entry": "/api/configs/ai/mcp/instruction-registry/entries",
            "invalidate": "/api/configs/ai/mcp/instruction-registry/invalidate",
            "promote": "/api/configs/ai/mcp/instruction-registry/promote",
        }
        return manifest

    @classmethod
    def build_frontend_state(cls) -> dict[str, Any]:
        cls.sync_defaults()
        entries = cls._query_entries()
        audit = cls._query_audit_events(limit=20)
        status_distribution: dict[str, int] = {}
        rollout_distribution: dict[str, int] = {}
        environment_distribution: dict[str, int] = {}
        for item in entries:
            status_distribution[item.status] = status_distribution.get(item.status, 0) + 1
            rollout_distribution[item.rollout_status] = rollout_distribution.get(item.rollout_status, 0) + 1
            environment_distribution[item.environment] = environment_distribution.get(item.environment, 0) + 1
        return {
            "summary": {
                "entries": len(entries),
                "active_entries": sum(1 for item in entries if item.status == "active"),
                "tenant_overrides": sum(1 for item in entries if item.scope_type == "tenant_override"),
                "channels": sorted({item.channel for item in entries}),
                "runtimes": sorted({item.runtime_profile for item in entries}),
                "status_distribution": status_distribution,
                "rollout_distribution": rollout_distribution,
                "environment_distribution": environment_distribution,
            },
            "entries": [item.to_dict() for item in entries],
            "recent_audit": [item.to_dict() for item in audit],
            "recent_changes": cls._build_recent_changes(audit),
            "supported_runtimes": sorted(cls.SUPPORTED_RUNTIMES),
            "supported_channels": sorted(cls.SUPPORTED_CHANNELS),
            "supported_environments": ["production", "staging", "development"],
        }

    @classmethod
    def resolve_bundle(
        cls,
        *,
        runtime_profile: str = "squad_cliente",
        agent_key: str | None = None,
        harness_key: str | None = None,
        channel: str = "stable",
        company_id: int | None = None,
    ) -> dict:
        normalized_runtime = str(runtime_profile or "").strip().lower() or "squad_cliente"
        normalized_channel = str(channel or "stable").strip().lower() or "stable"
        if not cls.supports_runtime(normalized_runtime):
            raise ValueError(f"Runtime profile não suportado pelo instruction registry: {normalized_runtime}.")
        if not cls.supports_channel(normalized_channel):
            raise ValueError(f"Canal do instruction registry inválido: {normalized_channel}.")

        runtime_spec = get_runtime_profile_spec(normalized_runtime)
        if runtime_spec is None:
            raise ValueError(f"Runtime profile não encontrado: {normalized_runtime}.")

        cls.sync_defaults()
        selected_harness = (harness_key or runtime_spec.default_harness_key or "").strip() or runtime_spec.default_harness_key
        selected_agent = (agent_key or cls._AGENT_BY_HARNESS.get(selected_harness or "", "")).strip() or cls._default_agent_key(normalized_runtime)

        static_base = cls._build_static_base(
            runtime_profile=normalized_runtime,
            agent_key=selected_agent,
            harness_key=selected_harness or "",
            channel=normalized_channel,
            company_id=company_id,
        )
        dynamic_layers = cls._resolve_dynamic_layers(
            runtime_profile=normalized_runtime,
            agent_key=selected_agent,
            harness_key=selected_harness,
            channel=normalized_channel,
            company_id=company_id,
        )

        merged = dict(static_base)
        source_scope = ["static_base"]
        invalidation_parts = []
        for entry in dynamic_layers:
            merged = cls._deep_merge(merged, dict(entry.payload_json or {}))
            source_scope.append(f"db:{entry.scope_type}:{entry.id}")
            invalidation_parts.append(entry.invalidation_token)

        # A política da jornada pertence à camada runtime/global e não pode ser
        # relaxada por override tenant ou prompt textual.
        merged["journey_guide"] = cls.build_journey_guide(normalized_runtime)

        canonical_payload = {
            key: merged[key]
            for key in (
                "runtime_profile",
                "experience_label",
                "surface",
                "agent_key",
                "harness_key",
                "channel",
                "bundle_version",
                "company_id",
                "summary",
                "introduction_message",
                "cache_ttl_seconds",
                "startup_sequence",
                "mandatory_rules",
                "handoff_rules",
                "forbidden_actions",
                "layer_matrix",
                "doc_refs",
                "journey_guide",
            )
        }
        checksum = hashlib.sha256(json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        invalidation_token = "-".join(invalidation_parts) if invalidation_parts else "static"
        cache_key = f"instruction-registry:{normalized_runtime}:{selected_agent}:{selected_harness}:{normalized_channel}:{company_id or 0}:{checksum[:12]}"

        bundle = InstructionBootstrapBundle(
            runtime_profile=merged["runtime_profile"],
            experience_label=merged["experience_label"],
            surface=merged["surface"],
            agent_key=merged["agent_key"],
            harness_key=merged["harness_key"],
            channel=merged["channel"],
            bundle_version=merged["bundle_version"],
            checksum=checksum,
            invalidation_token=invalidation_token,
            cache_key=cache_key,
            company_id=merged.get("company_id"),
            summary=merged["summary"],
            introduction_message=merged["introduction_message"],
            cache_ttl_seconds=int(merged["cache_ttl_seconds"]),
            source_scope=source_scope,
            startup_sequence=list(merged["startup_sequence"]),
            mandatory_rules=[InstructionRule.model_validate(item) for item in merged["mandatory_rules"]],
            handoff_rules=[InstructionRule.model_validate(item) for item in merged["handoff_rules"]],
            forbidden_actions=list(merged["forbidden_actions"]),
            layer_matrix=list(APP32_INSTRUCTION_REGISTRY_MANIFEST.layer_matrix),
            doc_refs=[InstructionDocumentRef.model_validate(item) for item in merged["doc_refs"]],
            journey_guide=merged.get("journey_guide"),
        )
        return bundle.model_dump(mode="json")

    @classmethod
    def upsert_entry(cls, payload: dict[str, Any], *, actor_user_id: int | None = None) -> InstructionRegistryEntry:
        cls.sync_defaults()
        entry = cls._find_entry(
            scope_type=payload["scope_type"],
            runtime_profile=payload["runtime_profile"],
            channel=payload.get("channel") or "stable",
            environment=payload.get("environment") or cls.DEFAULT_ENVIRONMENT,
            company_id=payload.get("company_id"),
            agent_key=payload.get("agent_key"),
            harness_key=payload.get("harness_key"),
        )
        created = False
        before_snapshot = entry.to_dict() if entry is not None else None
        if entry is None:
            entry = InstructionRegistryEntry(
                scope_type=payload["scope_type"],
                runtime_profile=payload["runtime_profile"],
                channel=payload.get("channel") or "stable",
                environment=payload.get("environment") or cls.DEFAULT_ENVIRONMENT,
                company_id=payload.get("company_id"),
                agent_key=payload.get("agent_key"),
                harness_key=payload.get("harness_key"),
            )
            db.session.add(entry)
            created = True
        entry.status = payload.get("status") or "active"
        entry.rollout_status = payload.get("rollout_status") or "active"
        entry.entry_version = payload.get("entry_version") or "v1"
        entry.cache_ttl_seconds = int(payload.get("cache_ttl_seconds") or cls.DEFAULT_CACHE_TTL_SECONDS)
        entry.payload_json = dict(payload.get("payload") or {})
        entry.notes = payload.get("notes")
        entry.updated_by_user_id = actor_user_id
        if created:
            entry.created_by_user_id = actor_user_id
        entry.approved_by_user_id = actor_user_id
        entry.approved_at = datetime.utcnow()
        entry.invalidation_token = secrets.token_hex(8)
        entry.checksum = cls._compute_entry_checksum(entry.payload_json)
        db.session.flush()
        after_snapshot = entry.to_dict()
        cls._record_audit(
            event_type="instruction_registry.create" if created else "instruction_registry.update",
            entry=entry,
            actor_user_id=actor_user_id,
            detail="Entry do instruction registry persistida com sucesso.",
            payload={
                "status": entry.status,
                "rollout_status": entry.rollout_status,
                "diff": cls._build_entry_diff(before_snapshot, after_snapshot),
                "before": before_snapshot,
                "after": after_snapshot,
            },
            commit=False,
        )
        db.session.commit()
        return entry

    @classmethod
    def promote_entry(cls, payload: dict[str, Any], *, actor_user_id: int | None = None) -> InstructionRegistryEntry:
        cls.sync_defaults()
        if not has_app_context():
            raise ValueError("App context indisponível para promoção do instruction registry.")
        source = InstructionRegistryEntry.query.get(payload["source_entry_id"])
        if source is None:
            raise ValueError("Entry de origem não encontrada para promoção.")

        target_channel = str(payload.get("target_channel") or "").strip().lower()
        if not cls.supports_channel(target_channel):
            raise ValueError(f"Canal alvo inválido para promoção: {target_channel}.")
        target_environment = payload.get("target_environment") or source.environment or cls.DEFAULT_ENVIRONMENT
        target = cls._find_entry(
            scope_type=source.scope_type,
            runtime_profile=source.runtime_profile,
            channel=target_channel,
            environment=target_environment,
            company_id=source.company_id,
            agent_key=source.agent_key,
            harness_key=source.harness_key,
        )
        created = False
        before_snapshot = target.to_dict() if target is not None else None
        if target is None:
            target = InstructionRegistryEntry(
                scope_type=source.scope_type,
                runtime_profile=source.runtime_profile,
                channel=target_channel,
                environment=target_environment,
                company_id=source.company_id,
                agent_key=source.agent_key,
                harness_key=source.harness_key,
            )
            db.session.add(target)
            created = True
        target.status = payload.get("target_status") or "active"
        target.rollout_status = payload.get("target_rollout_status") or "active"
        target.entry_version = payload.get("entry_version") or f"{source.entry_version}-{target_channel}"
        target.cache_ttl_seconds = source.cache_ttl_seconds
        target.payload_json = dict(source.payload_json or {})
        target.notes = payload.get("notes") or f"Promovida da entry #{source.id} ({source.channel} -> {target_channel})."
        target.updated_by_user_id = actor_user_id
        if created:
            target.created_by_user_id = actor_user_id
        target.approved_by_user_id = actor_user_id
        target.approved_at = datetime.utcnow()
        target.invalidation_token = secrets.token_hex(8)
        target.checksum = cls._compute_entry_checksum(target.payload_json)
        db.session.flush()
        after_snapshot = target.to_dict()
        cls._record_audit(
            event_type="instruction_registry.promote",
            entry=target,
            actor_user_id=actor_user_id,
            detail=f"Entry promovida da #{source.id} para o canal {target_channel}.",
            payload={
                "source_entry_id": source.id,
                "source_channel": source.channel,
                "target_channel": target_channel,
                "created": created,
                "diff": cls._build_entry_diff(before_snapshot, after_snapshot),
                "before": before_snapshot,
                "after": after_snapshot,
            },
            commit=False,
        )
        db.session.commit()
        return target

    @classmethod
    def invalidate_entries(
        cls,
        payload: dict[str, Any],
        *,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        cls.sync_defaults()
        entries = []
        if payload.get("entry_id"):
            item = InstructionRegistryEntry.query.get(payload["entry_id"])
            if item is not None:
                entries = [item]
        else:
            query = InstructionRegistryEntry.query
            if payload.get("runtime_profile"):
                query = query.filter_by(runtime_profile=payload["runtime_profile"])
            if payload.get("company_id") is not None:
                query = query.filter_by(company_id=payload["company_id"])
            if payload.get("channel"):
                query = query.filter_by(channel=payload["channel"])
            entries = query.all()

        changed = 0
        for entry in entries:
            entry.invalidation_token = secrets.token_hex(8)
            entry.last_invalidated_at = datetime.utcnow()
            entry.updated_by_user_id = actor_user_id
            changed += 1
            cls._record_audit(
                event_type="entry_invalidated",
                entry=entry,
                actor_user_id=actor_user_id,
                detail=payload["reason"],
                payload={"reason": payload["reason"]},
                commit=False,
            )
        db.session.commit()
        return {"invalidated": changed}

    @classmethod
    def sync_defaults(cls) -> None:
        if not has_app_context():
            return
        changed = False
        for seed in cls._default_seed_entries():
            existing = cls._find_entry(
                scope_type=seed["scope_type"],
                runtime_profile=seed["runtime_profile"],
                channel=seed["channel"],
                environment=seed["environment"],
                company_id=seed.get("company_id"),
                agent_key=seed.get("agent_key"),
                harness_key=seed.get("harness_key"),
            )
            if existing is None:
                existing = InstructionRegistryEntry(
                    scope_type=seed["scope_type"],
                    runtime_profile=seed["runtime_profile"],
                    channel=seed["channel"],
                    environment=seed["environment"],
                    company_id=seed.get("company_id"),
                    agent_key=seed.get("agent_key"),
                    harness_key=seed.get("harness_key"),
                )
                db.session.add(existing)
                changed = True
            for field in ("status", "rollout_status", "entry_version", "cache_ttl_seconds", "payload_json", "notes"):
                value = seed.get(field)
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            checksum = cls._compute_entry_checksum(existing.payload_json or {})
            if existing.checksum != checksum:
                existing.checksum = checksum
                changed = True
            if not existing.invalidation_token:
                existing.invalidation_token = secrets.token_hex(8)
                changed = True
        if changed:
            db.session.commit()

    @classmethod
    def _resolve_dynamic_layers(
        cls,
        *,
        runtime_profile: str,
        agent_key: str,
        harness_key: str | None,
        channel: str,
        company_id: int | None,
    ) -> list[InstructionRegistryEntry]:
        if not has_app_context():
            return []
        query = InstructionRegistryEntry.query.filter(
            InstructionRegistryEntry.status == "active",
            InstructionRegistryEntry.rollout_status.in_(["active", "pilot", "internal_test"]),
            InstructionRegistryEntry.channel == channel,
            InstructionRegistryEntry.runtime_profile.in_(["global", runtime_profile]),
        )
        entries = query.all()

        selected: list[InstructionRegistryEntry] = []
        for entry in entries:
            if entry.scope_type == "global":
                selected.append(entry)
                continue
            if entry.runtime_profile not in {runtime_profile}:
                continue
            if entry.scope_type == "runtime":
                selected.append(entry)
                continue
            if entry.scope_type == "agent":
                if entry.agent_key and entry.agent_key != agent_key:
                    continue
                if entry.harness_key and harness_key and entry.harness_key != harness_key:
                    continue
                selected.append(entry)
                continue
            if entry.scope_type == "tenant_override":
                if company_id is None or entry.company_id != company_id:
                    continue
                selected.append(entry)

        precedence = {"global": 1, "runtime": 2, "agent": 3, "tenant_override": 4}
        selected.sort(key=lambda item: (precedence.get(item.scope_type, 99), item.id))
        return selected

    @classmethod
    def _build_static_base(
        cls,
        *,
        runtime_profile: str,
        agent_key: str,
        harness_key: str,
        channel: str,
        company_id: int | None,
    ) -> dict[str, Any]:
        runtime_spec = get_runtime_profile_spec(runtime_profile)
        experience_label = cls._EXPERIENCE_LABELS[runtime_profile]
        return {
            "runtime_profile": runtime_profile,
            "experience_label": experience_label,
            "surface": runtime_spec.default_surface if runtime_spec else "user",
            "agent_key": agent_key,
            "harness_key": harness_key or (runtime_spec.default_harness_key if runtime_spec else ""),
            "channel": channel,
            "bundle_version": cls.CURRENT_BUNDLE_VERSION,
            "company_id": company_id,
            "summary": f"Bundle mínimo do {experience_label} para bootstrap remoto, previsível, versionado e cacheável.",
            "introduction_message": "Ative o bundle mínimo, preserve tenant isolation, use MCP First e consulte documentos completos apenas sob demanda.",
            "cache_ttl_seconds": cls.DEFAULT_CACHE_TTL_SECONDS,
            "startup_sequence": cls._default_startup_sequence(runtime_profile),
            "mandatory_rules": [item.model_dump(mode="json") for item in cls._mandatory_rules(runtime_profile, agent_key)],
            "handoff_rules": [item.model_dump(mode="json") for item in cls._handoff_rules(runtime_profile, agent_key)],
            "forbidden_actions": cls._forbidden_actions(runtime_profile, agent_key),
            "layer_matrix": [item.model_dump(mode="json") for item in APP32_INSTRUCTION_REGISTRY_MANIFEST.layer_matrix],
            "doc_refs": [item.model_dump(mode="json") for item in cls._doc_refs()],
            "journey_guide": cls.build_journey_guide(runtime_profile),
        }

    @classmethod
    def build_journey_guide(cls, runtime_profile: str) -> dict[str, Any] | None:
        if runtime_profile != "squad_cliente":
            return None
        return {
            "version": "structuring-journey-v2.1",
            "scope": "Condução MCP First das quatro frentes da Estruturação Empresarial pelo Squad Cliente.",
            "entry_state": "collecting_evidence",
            "states": [
                {
                    "key": "collecting_evidence",
                    "responsible": "Squad Cliente / cliente",
                    "required_output": "Perguntas mínimas, evidências internas lidas e lacunas objetivas.",
                },
                {
                    "key": "awaiting_client_validation",
                    "responsible": "Gestor / Squad Cliente",
                    "required_output": "Conteúdo humano confirmado, corrigido ou explicitamente mantido como hipótese.",
                },
                {
                    "key": "awaiting_versus_validation",
                    "responsible": "Squad Versus",
                    "required_output": "Diagnóstico, método utilizado, riscos, fontes e opções de encaminhamento.",
                },
                {
                    "key": "awaiting_engineering_validation",
                    "responsible": "Squad de Engenharia",
                    "required_output": "Gaps técnicos, dados, MCP, read models e rastreabilidade validados quando aplicável.",
                },
                {
                    "key": "awaiting_consultant_decision",
                    "responsible": "Consultor Versus",
                    "required_output": "Recomendação rastreável e escopo exato da decisão solicitada.",
                },
                {
                    "key": "approved_for_execution",
                    "responsible": "Executor autorizado",
                    "required_output": "Objetos, campos e valores expressamente autorizados para execução.",
                },
                {
                    "key": "executed_verified",
                    "responsible": "Executor autorizado / consultor",
                    "required_output": "Leitura pós-execução, resultado persistido e divergências remanescentes.",
                },
                {
                    "key": "blocked",
                    "responsible": "Squad Versus ou Engenharia",
                    "required_output": "Motivo do bloqueio, evidência ou capability faltante e rota de escalonamento.",
                },
            ],
            "action_policy": [
                {
                    "action": "read_consultive_context",
                    "autonomy": "may",
                    "rule": "Ler contexto, evidências, gaps e protocolos permitidos para o company_id ativo.",
                },
                {
                    "action": "collect_human_evidence",
                    "autonomy": "must",
                    "rule": "Fazer perguntas mínimas e separar fala humana de hipótese produzida pela IA.",
                },
                {
                    "action": "research_benchmark",
                    "autonomy": "may",
                    "rule": "Pesquisar quando o protocolo exigir e registrar fontes, recorte e limitações.",
                },
                {
                    "action": "classify_assisted_analysis",
                    "autonomy": "must",
                    "rule": "Classificar como technical_test ou methodological; somente análise metodológica elegível pode avançar a jornada.",
                },
                {
                    "action": "register_canonical_data",
                    "autonomy": "cannot",
                    "rule": "Não gravar nem confirmar dado canônico sem decisão do consultor e executor autorizado.",
                },
                {
                    "action": "validate_for_another_squad",
                    "autonomy": "cannot",
                    "rule": "Não registrar validação em nome de outro squad nem usar validação como notificação.",
                },
                {
                    "action": "approve_method_or_maturity",
                    "autonomy": "cannot",
                    "rule": "Escalar decisões de método e maturidade ao Squad Versus e ao Consultor Versus.",
                },
                {
                    "action": "execute_ui_only_action",
                    "autonomy": "cannot",
                    "rule": "Registrar pendência e não declarar execução de ação exclusiva da UI ou capability ausente.",
                },
                {
                    "action": "execute_authorized_mutation",
                    "autonomy": "gated",
                    "rule": "Somente perfil autorizado, após decisão explícita, com releitura equivalente para verificação.",
                },
            ],
            "read_tool_sequence": [
                "select_app32_session_company_tool",
                "consultive_get_next_action",
                "consultive_get_front_context",
                "consultive_get_front_evidence",
                "consultive_get_front_gaps",
                "consultive_get_methodology_guidance",
                "consultive_resolve_protocol",
            ],
            "escalation_rules": [
                "Escalar ao Squad Versus quando o caso exigir método, estratégia, maturidade ou redesenho estrutural.",
                "Escalar à Engenharia quando houver erro técnico, capability ausente, problema de MCP ou dado indisponível.",
            ],
        }

    @classmethod
    def _default_startup_sequence(cls, runtime_profile: str) -> list[str]:
        if runtime_profile == "squad_cliente":
            return [
                "resolve_app32_instruction_bundle_tool",
                "describe_app32_squad_runtime_tool",
                "list_user_app32_capabilities",
                "describe_app32_profile_contracts_tool",
                "describe_app32_surface_playbooks_tool",
                "describe_app32_domain_playbooks_tool",
            ]
        if runtime_profile == "squad_versus":
            return [
                "resolve_app32_instruction_bundle_tool",
                "describe_app32_squad_runtime_tool",
                "list_admin_app32_capabilities",
                "describe_app32_profile_contracts_tool",
                "describe_app32_surface_playbooks_tool",
                "describe_app32_domain_playbooks_tool",
            ]
        return [
            "resolve_app32_instruction_bundle_tool",
            "describe_app32_squad_runtime_tool",
            "list_ops_app32_capabilities",
            "describe_app32_profile_contracts_tool",
            "describe_app32_surface_playbooks_tool",
            "describe_app32_domain_playbooks_tool",
        ]

    @classmethod
    def _mandatory_rules(cls, runtime_profile: str, agent_key: str) -> list[InstructionRule]:
        per_runtime = {
            "squad_cliente": "Operar com menor privilégio na surface user e sem contornar restrições de admin, analytics ou ops.",
            "squad_versus": "Operar com company_id explícito em surface privilegiada e começar sempre por discovery antes de qualquer mutação consultiva.",
            "engineering": "Operar com evidência, boundaries técnicos e intervenção disciplinada em ops/admin/analytics.",
        }
        per_agent = {
            "SC-COORD": "Coordenar sem inflar custo, preferindo resposta direta segura antes de qualquer roteamento.",
            "SC-OPS": "Na descoberta de processos, levantar o AS-IS com evidências, percorrer o SIPOC do gatilho ao objetivo e escalar redesenho estrutural ao Squad Versus.",
            "SV-COORD": "Conduzir discovery consultivo antes de acionar especialidades do Squad Versus.",
            "SV-BUSINESS-ARCHITECT": "Revisar AS-IS, desenhar TO-BE com validação SIPOC progressiva/regressiva e manter publicação BPMN sob gate humano explícito.",
            "SE-COORD": "Fazer triagem técnica antes de qualquer mudança estrutural ou intervenção operacional.",
        }
        return [
            InstructionRule(
                rule="Toda sessão deve respeitar company_id e tenant isolation como premissas inegociáveis.",
                rationale="O registry não pode virar vetor de tenant crossing.",
            ),
            InstructionRule(
                rule="Carregar apenas o bundle mínimo no contexto inicial; documentos completos ficam por referência.",
                rationale="Reduz consumo de tokens, latência e diluição de foco do agente.",
            ),
            InstructionRule(
                rule="MCP First para discovery operacional; o bundle não substitui contratos, capabilities nem playbooks da surface.",
                rationale="Mantém o APP32 como fonte de verdade operacional.",
            ),
            InstructionRule(
                rule="Na maturidade assistida, chamar consultive_get_next_action para obter estado, próximo responsável, critérios e gate antes de improvisar a sequência metodológica.",
                rationale="Mantém Forma de Trabalho, Ferramenta, Agentes e Orquestração sincronizados.",
            ),
            InstructionRule(
                rule="Para toda nova solicitação operacional, chamar resolve_app32_operation_tool antes de pesquisar tools ou catálogos; se houver troca de especialista, usar select_app32_session_harness_tool e atualizar tools/list.",
                rationale="Evita varredura lenta de catálogos, separa capabilities planejadas e executa a menor rota determinística disponível.",
            ),
            InstructionRule(
                rule="Em specialist_discovery, atualizar tools/list uma vez e executar somente correspondência semântica exata; sem correspondência direta, informar capability_not_available sem testar tools aproximadas.",
                rationale="Evita respostas incorretas, chamadas irrelevantes e latência por tentativa e erro.",
            ),
            InstructionRule(
                rule="Em 502, 503 ou 504, reabrir streamable-http e repetir só leitura idempotente, até 3 tentativas com espera de 1, 2 e 4s; restaurar empresa e harness. Nunca repetir mutação automaticamente.",
                rationale="Recupera falhas transitórias sem duplicar escritas nem perder o isolamento da sessão.",
            ),
            InstructionRule(
                rule=per_runtime[runtime_profile],
                rationale="Especializa o comportamento base do runtime ativo.",
            ),
            InstructionRule(
                rule=per_agent.get(agent_key, "Aplicar o escopo do harness ativo com economia de contexto."),
                rationale="Especializa o agente sem replicar um prompt gigante por cliente.",
            ),
            InstructionRule(
                rule="Em modelagem de processos, separar responsável único do processo de times executores; tratar POP como seletivo e compartilhável, rotina como gatilho e indicadores como conjunto mínimo.",
                rationale="Evita reproduzir no BPMN relações artificiais de um POP, rotina ou indicador para cada atividade.",
            ),
            InstructionRule(
                rule="Construir o fluxo progressivamente do gatilho ao objetivo e validá-lo regressivamente do objetivo ao gatilho, usando o SIPOC como contrato transversal e distinguindo saída de objetivo.",
                rationale="Evita atividades sem contribuição, saídas sem recebedor e lacunas de entrada ou fornecedor sem impor relação 1:1 com o BPMN.",
            ),
            InstructionRule(
                rule="Na maturação da modelagem, aplicar process-modeling-official-v1.0, diagnosticar seis dimensões e indicar estado, gate e próxima ação sem score percentual universal.",
                rationale="Separa maturidade metodológica de completude cadastral, implantação e desempenho operacional.",
            ),
        ]

    @classmethod
    def _handoff_rules(cls, runtime_profile: str, agent_key: str) -> list[InstructionRule]:
        if runtime_profile == "squad_cliente":
            return [
                InstructionRule(
                    rule="Escalar para SC-COM, SC-OPS ou SC-ADM quando o domínio ficar claro e houver ganho real de especialização.",
                    rationale="Preserva fronteiras entre copilotos do Squad Cliente.",
                ),
                InstructionRule(
                    rule="Escalar para Squad Versus ou Engenharia quando o caso sair da operação local ou virar problema técnico.",
                    rationale="Evita atuação fora da surface correta.",
                ),
                InstructionRule(
                    rule="Na modelagem de processos, entregar evidências e AS-IS ao Business Architect Versus; não publicar BPMN nem validar TO-BE em nome do Squad Versus.",
                    rationale="Preserva a autonomia operacional do cliente e o gate metodológico da Versus.",
                ),
                InstructionRule(
                    rule="No AS-IS, percorrer o contrato SIPOC nos dois sentidos e registrar gaps como evidência, sem preencher lacunas com desenho TO-BE.",
                    rationale="Mantém a descoberta fiel à realidade operacional do cliente.",
                ),
                InstructionRule(
                    rule="Na jornada de maturação da modelagem, atuar em collecting_evidence, mapping_as_is e awaiting_client_validation; demais estados exigem handoff.",
                    rationale="Preserva o gate de realidade sem personificar a validação metodológica da Versus.",
                ),
            ]
        if runtime_profile == "squad_versus":
            return [
                InstructionRule(
                    rule="Escalar para Engenharia quando a hipótese consultiva exigir correção estrutural de plataforma, integrações ou observabilidade.",
                    rationale="Separa consultoria de execução técnica.",
                ),
                InstructionRule(
                    rule="Redirecionar ao Squad Cliente quando a demanda couber em operação local de menor privilégio.",
                    rationale="Evita inflar a surface admin sem necessidade.",
                ),
                InstructionRule(
                    rule="Na modelagem de processos, receber o AS-IS do Squad Cliente, validar o TO-BE e publicar somente após confirmação humana explícita.",
                    rationale="Mantém realidade, método e decisão humana em gates distintos.",
                ),
                InstructionRule(
                    rule="No TO-BE, construir do gatilho ao objetivo e validar do objetivo ao gatilho pelo SIPOC, assegurando saída e recebedor em cada caminho final.",
                    rationale="Torna explícito o teste de suficiência e contribuição do desenho proposto.",
                ),
                InstructionRule(
                    rule="Na jornada de maturação da modelagem, conduzir contracting_process, designing_to_be, completing_operational_model e awaiting_versus_validation pelo protocolo oficial.",
                    rationale="Concentra método, fronteira e TO-BE no Squad Versus sem contornar decisão do consultor.",
                ),
            ]
        return [
            InstructionRule(
                rule="Escalar para Squad Versus quando o tema for governança, política, método ou desenho consultivo, não execução técnica.",
                rationale="Mantém a Engenharia enxuta e focada em correção/evolução técnica.",
            ),
            InstructionRule(
                rule="Redirecionar ao Squad Cliente quando a demanda voltar a ser operação assistida do dia a dia.",
                rationale="Evita capturar demandas funcionais que não exigem surface técnica.",
            ),
        ]

    @classmethod
    def _forbidden_actions(cls, runtime_profile: str, agent_key: str) -> list[str]:
        base = [
            "Não injetar SPEC, Paper, Playbook ou Runbook completos no contexto inicial da sessão.",
            "Não criar override por tenant capaz de violar multi-tenancy, company_id ou boundaries globais.",
        ]
        if runtime_profile == "squad_cliente":
            base.append("Não contornar surfaces privilegiadas, human gate ou restrições financeiras sensíveis.")
            base.append("Não publicar BPMN, redefinir fronteira estrutural ou validar TO-BE em nome do Squad Versus.")
        elif runtime_profile == "squad_versus":
            base.append("Não usar surface admin como atalho para analytics read-only ou operação do cliente quando o menor privilégio bastar.")
            base.append("Não duplicar POP compartilhado nem publicar BPMN sem confirmação humana explícita.")
        else:
            base.append("Não transformar surface ops em atalho para governança funcional, controladoria ou analytics executivo.")
        return base

    @classmethod
    def _doc_refs(cls) -> list[InstructionDocumentRef]:
        root = cls._root_dir() / "docs"
        refs: list[InstructionDocumentRef] = []
        for doc_class, values in cls._DOCS.items():
            slug, title, relative_path, purpose = values
            refs.append(
                InstructionDocumentRef(
                    doc_class=doc_class,  # type: ignore[arg-type]
                    slug=slug,
                    title=title,
                    version="v1",
                    path=str((root / relative_path).resolve()),
                    purpose=purpose,
                )
            )
        return refs

    @classmethod
    def _find_entry(
        cls,
        *,
        scope_type: str,
        runtime_profile: str,
        channel: str,
        environment: str,
        company_id: int | None,
        agent_key: str | None,
        harness_key: str | None,
    ) -> InstructionRegistryEntry | None:
        if not has_app_context():
            return None
        return (
            InstructionRegistryEntry.query.filter_by(
                scope_type=scope_type,
                runtime_profile=runtime_profile,
                channel=channel,
                environment=environment,
                company_id=company_id,
                agent_key=agent_key,
                harness_key=harness_key,
            )
            .order_by(InstructionRegistryEntry.id.desc())
            .first()
        )

    @classmethod
    def _query_entries(cls) -> list[InstructionRegistryEntry]:
        if not has_app_context():
            return []
        return InstructionRegistryEntry.query.order_by(
            InstructionRegistryEntry.runtime_profile.asc(),
            InstructionRegistryEntry.scope_type.asc(),
            InstructionRegistryEntry.channel.asc(),
            InstructionRegistryEntry.id.asc(),
        ).all()

    @classmethod
    def _query_audit_events(cls, *, limit: int = 20) -> list[InstructionRegistryAuditLog]:
        if not has_app_context():
            return []
        return (
            InstructionRegistryAuditLog.query.order_by(InstructionRegistryAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def _build_recent_changes(cls, audit: list[InstructionRegistryAuditLog]) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for item in audit:
            payload = dict(item.payload_json or {})
            diff = payload.get("diff") or {}
            if not diff:
                continue
            changes.append(
                {
                    "event_type": item.event_type,
                    "entry_id": item.entry_id,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "changed_fields": list(diff.get("changed_fields") or []),
                    "payload_keys": list(diff.get("payload_keys") or []),
                    "summary": cls._summarize_diff(diff),
                }
            )
        return changes[:10]

    @classmethod
    def _record_audit(
        cls,
        *,
        event_type: str,
        entry: InstructionRegistryEntry | None,
        actor_user_id: int | None,
        detail: str,
        payload: dict[str, Any],
        commit: bool = True,
    ) -> InstructionRegistryAuditLog:
        log = InstructionRegistryAuditLog(
            entry_id=getattr(entry, "id", None),
            company_id=getattr(entry, "company_id", None),
            actor_user_id=actor_user_id,
            event_type=event_type,
            result="success",
            detail=detail,
            payload_json=dict(payload or {}),
        )
        db.session.add(log)
        if commit:
            db.session.commit()
        return log

    @staticmethod
    def _build_entry_diff(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
        if before is None and after is None:
            return {}
        tracked_fields = (
            "scope_type",
            "runtime_profile",
            "channel",
            "environment",
            "company_id",
            "agent_key",
            "harness_key",
            "status",
            "rollout_status",
            "entry_version",
            "cache_ttl_seconds",
            "notes",
        )
        changed_fields = [field for field in tracked_fields if (before or {}).get(field) != (after or {}).get(field)]
        before_payload = dict((before or {}).get("payload_json") or {})
        after_payload = dict((after or {}).get("payload_json") or {})
        payload_keys = sorted(
            key for key in set(before_payload.keys()) | set(after_payload.keys()) if before_payload.get(key) != after_payload.get(key)
        )
        return {"changed_fields": changed_fields, "payload_keys": payload_keys}

    @staticmethod
    def _summarize_diff(diff: dict[str, Any]) -> str:
        fields = list(diff.get("changed_fields") or [])
        payload_keys = list(diff.get("payload_keys") or [])
        parts = []
        if fields:
            parts.append(f"campos: {', '.join(fields[:5])}")
        if payload_keys:
            parts.append(f"payload: {', '.join(payload_keys[:5])}")
        return " · ".join(parts) or "sem diferenças relevantes"

    @classmethod
    def _default_seed_entries(cls) -> list[dict[str, Any]]:
        seeds = [
            {
                "scope_type": "global",
                "runtime_profile": "global",
                "channel": "stable",
                "environment": cls.DEFAULT_ENVIRONMENT,
                "status": "active",
                "rollout_status": "active",
                "entry_version": "v1",
                "cache_ttl_seconds": cls.DEFAULT_CACHE_TTL_SECONDS,
                "payload_json": {
                    "summary": "Bundle mínimo remoto, versionado e cacheável para os runtimes Sapiens.",
                    "introduction_message": "Use apenas o bundle mínimo e preserve MCP First.",
                },
                "notes": "Seed global do instruction registry.",
            },
        ]
        for runtime in sorted(cls.SUPPORTED_RUNTIMES):
            seeds.append(
                {
                    "scope_type": "runtime",
                    "runtime_profile": runtime,
                    "channel": "stable",
                    "environment": cls.DEFAULT_ENVIRONMENT,
                    "status": "active",
                    "rollout_status": "active",
                    "entry_version": "v1",
                    "cache_ttl_seconds": cls.DEFAULT_CACHE_TTL_SECONDS,
                    "payload_json": {
                        "runtime_profile": runtime,
                        "experience_label": cls._EXPERIENCE_LABELS[runtime],
                        "surface": get_runtime_profile_spec(runtime).default_surface if get_runtime_profile_spec(runtime) else "user",
                        "channel": "stable",
                    },
                    "notes": f"Seed runtime {runtime}.",
                }
            )
        return seeds

    @staticmethod
    def _compute_entry_checksum(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = InstructionRegistryService._deep_merge(dict(merged[key]), value)
            else:
                merged[key] = value
        return merged

    @classmethod
    def _default_agent_key(cls, runtime_profile: str) -> str:
        if runtime_profile == "squad_cliente":
            return OFFICIAL_SQUAD_CLIENTE_AGENTS[0]["key"]
        if runtime_profile == "squad_versus":
            return "SV-COORD"
        return "SE-COORD"


__all__ = ["InstructionRegistryService"]
