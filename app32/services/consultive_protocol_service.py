from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import has_app_context
from sqlalchemy import or_

from models import Company, ConsultiveProtocol, db
from models.consultive_protocol import (
    CONSULTIVE_PROTOCOL_AUDIENCE_VALUES,
    CONSULTIVE_PROTOCOL_DEPTH_VALUES,
    CONSULTIVE_PROTOCOL_STATUS_VALUES,
)
from services.urgent_business_review_common import UrgentBusinessReviewError


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _choice(value: Any, allowed: tuple[str, ...], *, default: str, field: str) -> str:
    normalized = str(value or default).strip().lower()
    if normalized not in allowed:
        raise UrgentBusinessReviewError(f"Valor inválido para {field}: {value}.")
    return normalized


class ConsultiveProtocolService:
    """Biblioteca evolutiva de protocolos consultivos versionados."""

    DEFAULT_PROTOCOL_CATALOG: dict[tuple[str, str], dict[str, Any]] = {
        ("identity", "mission"): {
            "title": "Protocolo de amadurecimento da Missão Organizacional",
            "objective": "Desenvolver ou amadurecer a missão conectando intenção do gestor, mercado e capacidade real de entrega.",
            "depth_level": "simulation",
            "investigation_layers": ["gestor_intent", "internal_mvv_process_fit", "external_benchmark", "consumer_market_reading", "promise_delivery_simulation"],
            "required_questions": [
                "O que a empresa entrega que não deveria deixar de existir?",
                "Para quem a empresa cria valor de forma prioritária?",
                "Qual transformação concreta o cliente percebe?",
                "Quais processos provam que essa promessa é entregável?",
            ],
        },
        ("identity", "vision"): {
            "title": "Protocolo de amadurecimento da Visão Organizacional",
            "objective": "Definir futuro desejado, horizonte e ambição realista da empresa.",
            "depth_level": "deep_research",
            "investigation_layers": ["future_ambition", "market_trends", "capability_constraints", "strategic_options"],
            "required_questions": [
                "Onde os gestores querem que a empresa esteja em 3 a 5 anos?",
                "Qual crescimento é desejado e qual crescimento é suportável?",
                "Que tendências externas podem acelerar ou limitar essa visão?",
            ],
        },
        ("identity", "values"): {
            "title": "Protocolo de amadurecimento dos Valores",
            "objective": "Evidenciar comportamentos reais e valores desejados que devem orientar decisões e pessoas.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["declared_behaviors", "real_decision_patterns", "culture_risks", "policy_alignment"],
            "required_questions": [
                "Quais comportamentos a empresa não negocia?",
                "Quais atitudes são recompensadas ou toleradas hoje?",
                "Onde há distância entre valor declarado e comportamento real?",
            ],
        },
        ("identity", "positioning"): {
            "title": "Protocolo de amadurecimento do Posicionamento",
            "objective": "Clarificar mercado-alvo, diferenciação, promessa e percepção externa da empresa.",
            "depth_level": "deep_research",
            "investigation_layers": ["customer_segments", "competitor_benchmark", "differentiation", "promise_evidence"],
            "required_questions": [
                "Por que o cliente deveria escolher esta empresa?",
                "Qual promessa o mercado realmente percebe?",
                "Que provas internas sustentam o posicionamento?",
            ],
        },
        ("identity", "org_chart"): {
            "title": "Protocolo de amadurecimento do Organograma",
            "objective": "Avaliar estrutura, papéis, responsabilidades, lacunas de liderança e aderência à estratégia.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["roles", "accountabilities", "decision_rights", "growth_structure"],
            "required_questions": [
                "Quem decide o quê hoje?",
                "Quais papéis críticos não têm responsável claro?",
                "A estrutura atual suporta o crescimento planejado?",
            ],
        },
        ("processes", "architecture"): {
            "title": "Protocolo de Arquitetura de Processos",
            "objective": "Estruturar áreas, macroprocessos, processos, donos e possíveis indicadores.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["areas", "macroprocesses", "process_inventory", "owners", "candidate_indicators"],
            "required_questions": [
                "Quais processos sustentam a proposta de valor?",
                "Quem é dono de cada processo crítico?",
                "Quais processos faltam ou estão duplicados?",
            ],
        },
        ("processes", "modeling"): {
            "title": "Protocolo de Modelagem de Processos",
            "objective": "Amadurecer fluxo, POP, recursos, rotina, SPEC para IA e indicadores.",
            "depth_level": "simulation",
            "investigation_layers": ["flow", "pop", "resources", "routine", "ai_spec", "indicators"],
            "required_questions": [
                "O fluxo reflete como o trabalho realmente acontece?",
                "Quais recursos e informações são necessários para executar?",
                "O processo já pode ser implantado parcialmente com segurança?",
            ],
        },
        ("processes", "implantation"): {
            "title": "Protocolo de Implantação de Processos",
            "objective": "Planejar implantação com projeto associado, treinamento, comunicação e controle inicial.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["training_project", "stakeholders", "readiness", "change_management", "initial_controls"],
            "required_questions": [
                "Que projeto sustenta a implantação?",
                "Quem precisa ser treinado e em que sequência?",
                "Quais riscos impedem a entrada em operação?",
            ],
        },
        ("processes", "stabilization"): {
            "title": "Protocolo de Estabilização de Processos",
            "objective": "Conduzir estabilização com 3 ciclos dentro das faixas de controle dos indicadores.",
            "depth_level": "simulation",
            "investigation_layers": ["control_ranges", "cycle_evidence", "deviation_causes", "corrective_actions"],
            "required_questions": [
                "Quais indicadores provam estabilidade?",
                "Quantos ciclos estão dentro da faixa de controle?",
                "Que desvios ainda impedem estabilização?",
            ],
        },
        ("processes", "audit"): {
            "title": "Protocolo de Entrada em Auditoria",
            "objective": "Preparar inclusão do processo no rol da auditoria interna com periodicidade e critérios.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["audit_scope", "frequency", "controls", "evidence", "nonconformity_protocol"],
            "required_questions": [
                "Quais controles serão auditados?",
                "Qual periodicidade é adequada ao risco?",
                "Que evidências mínimas precisam ficar disponíveis?",
            ],
        },
        ("growth_plan", "structured"): {
            "title": "Protocolo de Planejamento Estratégico Estruturado",
            "objective": "Verificar se o planejamento de crescimento está formalizado, claro e acionável.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["growth_goals", "strategic_choices", "constraints", "resources"],
            "required_questions": [
                "Qual crescimento a empresa está buscando?",
                "Quais escolhas estratégicas foram feitas?",
                "Quais recursos limitam ou viabilizam o plano?",
            ],
        },
        ("growth_plan", "connected"): {
            "title": "Protocolo de Planejamento Conectado",
            "objective": "Conectar planejamento à identidade, processos, projetos, pessoas e indicadores.",
            "depth_level": "simulation",
            "investigation_layers": ["identity_connection", "process_connection", "project_connection", "indicator_connection"],
            "required_questions": [
                "Quais processos entregam o plano?",
                "Quais projetos materializam a estratégia?",
                "Quais indicadores mostram avanço real?",
            ],
        },
        ("growth_plan", "deployed"): {
            "title": "Protocolo de Desdobramento Estratégico",
            "objective": "Avaliar se o plano foi desdobrado em responsáveis, metas, projetos e rotina de gestão.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["owners", "targets", "projects", "cadence", "accountability"],
            "required_questions": [
                "Quem é responsável por cada frente do plano?",
                "Quais metas e projetos existem para executar o plano?",
                "Como a rotina acompanha o desdobramento?",
            ],
        },
        ("growth_plan", "linked_to_management"): {
            "title": "Protocolo de Vínculo com Gerenciamento Estratégico",
            "objective": "Verificar se o planejamento está lincado com o gerenciamento estratégico e decisões reais.",
            "depth_level": "simulation",
            "investigation_layers": ["management_cadence", "decision_records", "indicator_reviews", "learning_loop"],
            "required_questions": [
                "O plano entra nas reuniões de gestão?",
                "Decisões são tomadas com base no plano e nos indicadores?",
                "O aprendizado altera projetos, processos ou metas?",
            ],
        },
        ("strategic_management", "indicators"): {
            "title": "Protocolo de Indicadores Estratégicos",
            "objective": "Avaliar indicadores, responsáveis, metas, frequência e utilidade para decisão.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["indicator_inventory", "owners", "targets", "frequency", "decision_use"],
            "required_questions": [
                "Quais indicadores realmente orientam decisão?",
                "Quem é o Responsável do Indicador?",
                "Há meta, frequência e fonte confiável?",
            ],
        },
        ("strategic_management", "cycles"): {
            "title": "Protocolo de Ciclos de Gestão",
            "objective": "Avaliar cadência de reuniões, análise de fatos, plano de ação e aprendizado.",
            "depth_level": "internal_diagnosis",
            "investigation_layers": ["meeting_cadence", "fact_based_review", "actions", "follow_up", "learning"],
            "required_questions": [
                "Com que frequência a estratégia é acompanhada?",
                "As reuniões geram decisões e ações?",
                "Há acompanhamento até fechamento?",
            ],
        },
        ("strategic_management", "incentives"): {
            "title": "Protocolo de Gestão de Incentivos",
            "objective": "Verificar se incentivos reforçam estratégia, processos, comportamento e indicadores corretos.",
            "depth_level": "simulation",
            "investigation_layers": ["incentive_rules", "behavior_effect", "indicator_alignment", "risk_of_distortion"],
            "required_questions": [
                "O que o modelo de incentivo estimula na prática?",
                "Há risco de incentivar comportamento contrário à estratégia?",
                "Os incentivos estão conectados a processos e indicadores certos?",
            ],
        },
        ("strategic_management", "connection_web"): {
            "title": "Protocolo da Teia de Conexões",
            "objective": "Entender conexões entre estratégia, processos, projetos, pessoas e indicadores.",
            "depth_level": "simulation",
            "investigation_layers": ["strategy_map", "process_links", "project_links", "people_links", "indicator_causality"],
            "required_questions": [
                "Quais relações de causa e efeito explicam o desempenho?",
                "Que processo, pessoa ou projeto impacta cada indicador crítico?",
                "Onde há desconexões entre estratégia e operação?",
            ],
        },
    }

    SUBPHASE_ALIASES = {
        None: "mission",
        "missao": "mission",
        "visao": "vision",
        "valores": "values",
        "posicionamento": "positioning",
        "organograma": "org_chart",
        "arquitetura": "architecture",
        "modelagem": "modeling",
        "implantacao": "implantation",
        "implantação": "implantation",
        "estabilizacao": "stabilization",
        "estabilização": "stabilization",
        "auditoria": "audit",
        "estruturado": "structured",
        "conectado": "connected",
        "desdobrado": "deployed",
        "vinculado": "linked_to_management",
        "indicadores": "indicators",
        "ciclos": "cycles",
        "incentivos": "incentives",
        "teia": "connection_web",
    }

    @staticmethod
    def _require_company(company_id: int | None) -> None:
        if company_id is None:
            return
        if Company.query.filter_by(id=company_id).first() is None:
            raise UrgentBusinessReviewError(f"Empresa não encontrada: company_id={company_id}.")

    @staticmethod
    def _normalize_subphase(subphase_key: str | None) -> str | None:
        normalized = _clean(subphase_key)
        return ConsultiveProtocolService.SUBPHASE_ALIASES.get(normalized, normalized)

    @classmethod
    def resolve_protocol(
        cls,
        *,
        company_id: int | None,
        front_key: str,
        subphase_key: str | None = None,
        audience: str = "ai_cli",
        depth_level: str | None = None,
    ) -> dict[str, Any]:
        normalized_front = _clean(front_key) or "identity"
        normalized_subphase = cls._normalize_subphase(subphase_key)
        normalized_audience = _choice(
            audience,
            CONSULTIVE_PROTOCOL_AUDIENCE_VALUES,
            default="ai_cli",
            field="audience",
        )
        if depth_level:
            _choice(depth_level, CONSULTIVE_PROTOCOL_DEPTH_VALUES, default="basic", field="depth_level")

        if has_app_context():
            query = ConsultiveProtocol.query.filter_by(
                front_key=normalized_front,
                subphase_key=normalized_subphase,
                audience=normalized_audience,
                status="active",
            )
            tenant_filter = (
                or_(ConsultiveProtocol.company_id == company_id, ConsultiveProtocol.company_id.is_(None))
                if company_id is not None
                else ConsultiveProtocol.company_id.is_(None)
            )
            candidates = query.filter(tenant_filter).order_by(
                ConsultiveProtocol.company_id.desc().nullslast(),
                ConsultiveProtocol.updated_at.desc(),
                ConsultiveProtocol.id.desc(),
            ).all()
            if depth_level:
                candidates = [item for item in candidates if item.depth_level == depth_level] or candidates
            if candidates:
                return candidates[0].to_dict()

        return cls._default_protocol(
            company_id=company_id,
            front_key=normalized_front,
            subphase_key=normalized_subphase,
            audience=normalized_audience,
        )

    @classmethod
    def list_protocols(
        cls,
        *,
        company_id: int | None = None,
        front_key: str | None = None,
        audience: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not has_app_context():
            return []
        query = ConsultiveProtocol.query
        if company_id is not None:
            query = query.filter(ConsultiveProtocol.company_id.in_([company_id, None]))
        if front_key:
            query = query.filter_by(front_key=_clean(front_key))
        if audience:
            query = query.filter_by(audience=_choice(audience, CONSULTIVE_PROTOCOL_AUDIENCE_VALUES, default="ai_cli", field="audience"))
        if status:
            query = query.filter_by(status=_choice(status, CONSULTIVE_PROTOCOL_STATUS_VALUES, default="active", field="status"))
        rows = query.order_by(ConsultiveProtocol.updated_at.desc()).limit(max(1, min(int(limit or 100), 500))).all()
        return [row.to_dict() for row in rows]

    @classmethod
    def list_protocol_catalog(
        cls,
        *,
        company_id: int | None = None,
        audience: str = "ai_cli",
    ) -> dict[str, Any]:
        """Lista todas as subfases do Cockpit com o protocolo resolvido ativo."""
        normalized_audience = _choice(
            audience,
            CONSULTIVE_PROTOCOL_AUDIENCE_VALUES,
            default="ai_cli",
            field="audience",
        )
        fronts = {
            "identity": {
                "title": "Identidade Organizacional",
                "subphases": ["mission", "vision", "values", "positioning", "org_chart"],
            },
            "processes": {
                "title": "Processos",
                "subphases": ["architecture", "modeling", "implantation", "stabilization", "audit"],
            },
            "growth_plan": {
                "title": "Planejamento Estratégico",
                "subphases": ["structured", "connected", "deployed", "linked_to_management"],
            },
            "strategic_management": {
                "title": "Gerenciamento Estratégico",
                "subphases": ["indicators", "cycles", "incentives", "connection_web"],
            },
        }
        items: list[dict[str, Any]] = []
        for front_key, front in fronts.items():
            for subphase_key in front["subphases"]:
                protocol = cls.resolve_protocol(
                    company_id=company_id,
                    front_key=front_key,
                    subphase_key=subphase_key,
                    audience=normalized_audience,
                )
                items.append(
                    {
                        "front_key": front_key,
                        "front_title": front["title"],
                        "subphase_key": subphase_key,
                        "subphase_title": cls._subphase_title(subphase_key),
                        "active_protocol": protocol,
                    }
                )
        return {
            "company_id": company_id,
            "audience": normalized_audience,
            "total": len(items),
            "items": items,
        }

    @classmethod
    def upsert_protocol(
        cls,
        *,
        payload: dict[str, Any],
        company_id: int | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if not has_app_context():
            raise UrgentBusinessReviewError("App context indisponível para persistir protocolo consultivo.")
        if company_id is not None:
            cls._require_company(company_id)
        if not isinstance(payload, dict):
            raise UrgentBusinessReviewError("Payload do protocolo deve ser um objeto.")

        row = None
        if payload.get("id"):
            row = ConsultiveProtocol.query.filter_by(id=int(payload["id"]), company_id=company_id).first()
            if row is None:
                raise UrgentBusinessReviewError("Protocolo não encontrado no tenant informado.")
        if row is None:
            row = ConsultiveProtocol(company_id=company_id, created_by_user_id=user_id)
            db.session.add(row)

        row.front_key = _clean(payload.get("front_key")) or "identity"
        row.subphase_key = cls._normalize_subphase(payload.get("subphase_key"))
        row.audience = _choice(payload.get("audience"), CONSULTIVE_PROTOCOL_AUDIENCE_VALUES, default="ai_cli", field="audience")
        row.depth_level = _choice(payload.get("depth_level"), CONSULTIVE_PROTOCOL_DEPTH_VALUES, default="basic", field="depth_level")
        row.status = _choice(payload.get("status"), CONSULTIVE_PROTOCOL_STATUS_VALUES, default="draft", field="status")
        row.protocol_version = _clean(payload.get("protocol_version")) or "v1"
        row.title = _clean(payload.get("title")) or "Protocolo consultivo"
        row.objective = _clean(payload.get("objective"))
        row.prompt_markdown = _clean(payload.get("prompt_markdown")) or ""
        if not row.prompt_markdown:
            raise UrgentBusinessReviewError("prompt_markdown é obrigatório.")
        row.protocol_json = dict(payload.get("protocol") or payload.get("protocol_json") or {})
        row.notes = _clean(payload.get("notes"))
        row.updated_by_user_id = user_id
        if row.status == "active" and row.approved_at is None:
            row.approved_at = datetime.utcnow()
            row.approved_by_user_id = user_id
        db.session.commit()
        return row.to_dict()

    @classmethod
    def _default_protocol(
        cls,
        *,
        company_id: int | None,
        front_key: str,
        subphase_key: str | None,
        audience: str,
    ) -> dict[str, Any]:
        normalized_subphase = cls._normalize_subphase(subphase_key) or cls._default_subphase_for_front(front_key)
        payload = cls.DEFAULT_PROTOCOL_CATALOG.get((front_key, normalized_subphase))
        if payload:
            return cls._format_default_protocol(
                company_id=company_id,
                front_key=front_key,
                subphase_key=normalized_subphase,
                audience=audience,
                payload=payload,
            )
        return {
            "id": None,
            "company_id": company_id,
            "front_key": front_key,
            "subphase_key": subphase_key,
            "audience": audience,
            "depth_level": "basic",
            "status": "active",
            "protocol_version": "fallback-v1",
            "source": "fallback",
            "title": "Protocolo consultivo padrão",
            "objective": "Orientar análise da frente consultiva com MCP First e gate humano.",
            "prompt_markdown": "Use o MCP para ler contexto, evidências e gaps. Faça perguntas quando faltarem dados. Não tome decisão final.",
            "protocol": {"output_format": ["diagnóstico", "gaps", "recomendações", "próximos passos"]},
        }

    @classmethod
    def _default_subphase_for_front(cls, front_key: str) -> str | None:
        return {
            "identity": "mission",
            "processes": "architecture",
            "growth_plan": "structured",
            "strategic_management": "indicators",
        }.get(front_key)

    @staticmethod
    def _subphase_title(subphase_key: str) -> str:
        return {
            "mission": "Missão",
            "vision": "Visão",
            "values": "Valores",
            "positioning": "Posicionamento",
            "org_chart": "Organograma",
            "architecture": "Arquitetura",
            "modeling": "Modelagem",
            "implantation": "Implantação",
            "stabilization": "Estabilização",
            "audit": "Auditoria",
            "structured": "Estruturado",
            "connected": "Conectado",
            "deployed": "Desdobrado",
            "linked_to_management": "Vinculado à gestão",
            "indicators": "Indicadores",
            "cycles": "Ciclos",
            "incentives": "Incentivos",
            "connection_web": "Teia de Conexões",
        }.get(subphase_key, subphase_key)

    @classmethod
    def _format_default_protocol(
        cls,
        *,
        company_id: int | None,
        front_key: str,
        subphase_key: str,
        audience: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = cls._build_prompt_markdown(payload)
        protocol = {
            "investigation_layers": list(payload.get("investigation_layers") or []),
            "required_questions": list(payload.get("required_questions") or []),
            "output_format": [
                "diagnóstico",
                "perguntas ao gestor",
                "evidências internas via MCP",
                "benchmarks e referências quando aplicável",
                "riscos e incoerências",
                "recomendações e próximos passos",
            ],
        }
        return {
            "id": None,
            "company_id": company_id,
            "front_key": front_key,
            "subphase_key": subphase_key,
            "audience": audience,
            "depth_level": payload.get("depth_level") or "internal_diagnosis",
            "status": "active",
            "protocol_version": "fallback-v1",
            "source": "fallback",
            "title": payload["title"],
            "objective": payload["objective"],
            "prompt_markdown": prompt,
            "protocol": protocol,
        }

    @classmethod
    def _build_prompt_markdown(cls, payload: dict[str, Any]) -> str:
        layers = "\n".join(f"- {item}" for item in payload.get("investigation_layers", []))
        questions = "\n".join(f"- {item}" for item in payload.get("required_questions", []))
        return f"""Atue como analista consultivo da Metodologia Versus.

Objetivo do protocolo:
{payload.get("objective")}

Conduza a investigação pelas camadas:
{layers}

Perguntas obrigatórias ao gestor ou responsáveis:
{questions}

Regras de condução:
- use MCP First para buscar contexto, evidências internas, processos, indicadores, projetos e registros relacionados;
- quando o protocolo exigir pesquisa profunda, pesquise boas práticas, benchmarks e referências externas antes de concluir;
- simule aderência entre o que está sendo proposto, a capacidade operacional, os processos e a percepção do mercado;
- aponte lacunas, riscos, incoerências e perguntas pendentes;
- não tome decisão final: entregue opções e próximos passos para validação do gestor, Squad Cliente, Squad Versus e consultor.
"""


__all__ = ["ConsultiveProtocolService"]
