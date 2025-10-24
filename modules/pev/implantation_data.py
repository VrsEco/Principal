"""
Helper functions to assemble Implantação (new venture) data structures
for templates and reports.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

# Order in which macro phases should appear
PHASE_ORDER = ["alignment", "model", "execution", "delivery"]

PHASE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "alignment": {
        "title": "Alinhamento Estratégico",
        "tagline": "Garantir visão, ritmo compartilhado e responsabilidades antes de evoluir para modelo e execução.",
        "pulse": None,
    },
    "model": {
        "title": "Modelo & Mercado",
        "tagline": "Transformar hipóteses em propostas fundamentadas para cada segmento do negócio.",
        "pulse": None,
    },
    "execution": {
        "title": "Estruturas de Execução",
        "tagline": "Ancorar operação, comercial e finanças para suportar o plano.",
        "pulse": None,
    },
    "delivery": {
        "title": "Relatório Final",
        "tagline": "Consolidar narrativa, indicadores e entrega final do planejamento.",
        "pulse": None,
    },
}

DEFAULT_DELIVERABLES: Dict[str, List[Dict[str, str]]] = {
    "alignment": [
        {"label": "Canvas de expectativas dos sócios", "endpoint": "pev.implantacao_canvas_expectativas"},
    ],
    "model": [
        {"label": "Canvas de proposta de valor", "endpoint": "pev.implantacao_canvas_proposta_valor"},
        {"label": "Mapa de persona e jornada", "endpoint": "pev.implantacao_mapa_persona"},
        {"label": "Matriz de diferenciais", "endpoint": "pev.implantacao_matriz_diferenciais"},
    ],
    "execution": [
        {"label": "Estruturas por área", "endpoint": "pev.implantacao_estruturas"},
    ],
    "delivery": [
        {"label": "Relatório final", "endpoint": "pev.implantacao_relatorio_final"},
    ],
}

AREA_LABELS = {
    "comercial": "Estruturação Comercial",
    "comércio": "Estruturação Comercial",
    "operacional": "Estruturação Operacional",
    "operacao": "Estruturação Operacional",
    "adm_fin": "Estruturação Adm / Fin",
    "administrativo_financeiro": "Estruturação Adm / Fin",
    "administrativo": "Estruturação Adm / Fin",
}

AREA_ORDER = ["Estruturação Comercial", "Estruturação Operacional", "Estruturação Adm / Fin"]

BLOCK_LABELS = {
    "processos": "Processos",
    "process": "Processos",
    "instalacoes": "Instalações",
    "instalações": "Instalações",
    "maquinas_equipamentos": "Máquinas e Equipamentos",
    "maquinas": "Máquinas e Equipamentos",
    "equipamentos": "Máquinas e Equipamentos",
    "pessoas": "Pessoas",
    "insumos": "Insumos",
    "material_consumo": "Material de Uso e Consumo / Outros",
    "material_uso_consumo": "Material de Uso e Consumo / Outros",
    "outros": "Material de Uso e Consumo / Outros",
    "material_de_uso_e_consumo": "Material de Uso e Consumo / Outros",
}


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if value is None:
        return ""
    return str(value)


def _ensure_list(value: Any, default: Optional[List[Any]] = None) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return list(default or [])
    return list(default or [])


def _ensure_dict(value: Any, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return dict(default or {})


def _normalize_sections(sections: Any, fallback: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    raw_list = sections if isinstance(sections, list) else fallback or []
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        normalized.append(
            {
                "title": entry.get("title") or entry.get("nome") or entry.get("header"),
                "description": entry.get("description") or entry.get("descricao"),
                "highlights": _ensure_list(entry.get("highlights") or entry.get("pontos") or []),
            }
        )
    return normalized


def _resolve_deliverables(phase_key: str, raw_deliverables: Any) -> List[Dict[str, str]]:
    deliverables: List[Dict[str, str]] = []
    if isinstance(raw_deliverables, list):
        for item in raw_deliverables:
            if isinstance(item, dict):
                label = item.get("label") or item.get("nome") or item.get("titulo")
                endpoint = item.get("endpoint")
                url = item.get("url")
                if label:
                    deliverables.append({"label": label, "endpoint": endpoint, "url": url})
            elif isinstance(item, str):
                deliverables.append({"label": item, "endpoint": None, "url": None})
    if not deliverables:
        deliverables = list(DEFAULT_DELIVERABLES.get(phase_key, []))
    return deliverables


def _compute_status_summary(phases: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    statuses = [phase.get("status") or "sem_registros" for phase in phases]
    total = len(phases)
    concluded = sum(1 for status in statuses if status == "concluida")
    if concluded == total and total > 0:
        total_status_text = "Todas as fases concluídas"
        progress_message = "Implantação pronta para apresentação final."
    elif concluded > 0:
        total_status_text = f"{concluded} de {total} fases concluídas"
        progress_message = "Continue concluindo as próximas macro fases para evoluir a implantação."
    else:
        total_status_text = "Nenhuma fase concluída"
        progress_message = "Inicie pela fase de alinhamento para dar ritmo ao planejamento."
    return total_status_text, progress_message, statuses


def build_plan_context(db, plan_id: int) -> Dict[str, Any]:
    plan_record = db.get_plan_with_company(plan_id) or {}
    dashboard_record = db.get_implantation_dashboard(plan_id) or {}

    last_update_reference = dashboard_record.get("updated_at") or plan_record.get("updated_at") or datetime.now()
    status = plan_record.get("status") or "Em andamento"

    actual_plan_id = plan_record.get("id") or plan_id
    return {
        "id": actual_plan_id,  # Adicionar id também (usado em templates)
        "plan_id": actual_plan_id,
        "company_id": plan_record.get("company_id"),
        "plan_name": plan_record.get("name") or "Implantação do Negócio",
        "company_name": plan_record.get("company_name") or "Empresa não informada",
        "status": status.capitalize() if isinstance(status, str) else status,
        "version": plan_record.get("version") or "v1.0",
        "consultant": plan_record.get("owner") or "Consultor responsável",
        "sponsor": plan_record.get("sponsor") or "Patrocinador",
        "last_update": _format_date(last_update_reference),
        "next_checkpoint": dashboard_record.get("next_focus") or "Checkpoint a definir",
        "project_link": None,
    }


def _generate_model_summary_sections(db, plan_id: int) -> List[Dict[str, Any]]:
    """Generate dynamic summary sections for Model & Market phase based on actual data"""
    segments = db.list_plan_segments(plan_id)
    
    if not segments:
        return []
    
    total_segments = len(segments)
    total_personas = sum(len(seg.get('personas', [])) for seg in segments)
    total_competitors = sum(len(seg.get('competitors_matrix', [])) for seg in segments)
    
    sections = []
    
    # Resumo geral
    sections.append({
        "title": "Resumo Geral",
        "description": f"{total_segments} segmento(s) de negócio mapeado(s) com propostas de valor definidas.",
        "highlights": [
            f"{total_personas} persona(s) detalhada(s)",
            f"{total_competitors} critério(s) competitivo(s) analisado(s)",
            "Estratégia de posicionamento por segmento"
        ]
    })
    
    # Detalhes por segmento
    for segment in segments[:3]:  # Mostrar até 3 segmentos no resumo
        seg_personas = len(segment.get('personas', []))
        seg_differentials = len(segment.get('differentials', []))
        
        highlights = []
        if seg_personas > 0:
            highlights.append(f"{seg_personas} persona(s)")
        if seg_differentials > 0:
            highlights.append(f"{seg_differentials} diferencial(is)")
        
        strategy = segment.get('strategy', {})
        value_prop = strategy.get('value_proposition', {})
        if value_prop.get('solution'):
            highlights.append("Proposta de valor definida")
        
        sections.append({
            "title": segment.get('name', 'Segmento'),
            "description": segment.get('description', ''),
            "highlights": highlights if highlights else ["Em desenvolvimento"]
        })
    
    if total_segments > 3:
        sections.append({
            "title": "Outros Segmentos",
            "description": f"+ {total_segments - 3} segmento(s) adicional(is)",
            "highlights": []
        })
    
    return sections


def build_overview_payload(db, plan_id: int) -> Dict[str, Any]:
    plan = build_plan_context(db, plan_id)
    dashboard_record = db.get_implantation_dashboard(plan_id) or {}

    phases_raw = {row.get("phase_key"): row for row in db.list_implantation_phases(plan_id)}
    macro_phases: List[Dict[str, Any]] = []

    for key in PHASE_ORDER:
        stored = phases_raw.get(key, {}) or {}
        defaults = PHASE_DEFAULTS.get(key, {})
        normalized_sections = _normalize_sections(stored.get("sections"), defaults.get("sections"))
        
        # Gerar resumo dinâmico para fase "model" baseado em dados reais
        if key == "model" and not normalized_sections:
            normalized_sections = _generate_model_summary_sections(db, plan_id)
        
        macro_phases.append(
            {
                "id": key,
                "phase_key": key,
                "title": stored.get("title") or defaults.get("title"),
                "status": stored.get("status") or "sem_registros",
                "tagline": stored.get("tagline") or defaults.get("tagline"),
                "pulse": stored.get("pulse") or defaults.get("pulse"),
                "sections": normalized_sections,
                "deliverables": _resolve_deliverables(key, stored.get("deliverables")),
            }
        )

    checkpoints = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "status": item.get("status") or "upcoming",
            "date": item.get("date") or item.get("date_label"),
        }
        for item in db.list_implantation_checkpoints(plan_id)
    ]

    total_status_text, computed_progress_message, statuses = _compute_status_summary(macro_phases)

    next_focus_phase = next((phase for phase in macro_phases if phase.get("status") != "concluida"), None)
    next_focus = dashboard_record.get("next_focus") or (next_focus_phase["title"] if next_focus_phase else "Implantação concluída")
    next_focus_details = dashboard_record.get("next_focus_details") or (
        next_focus_phase.get("tagline") if next_focus_phase else "Todas as macro fases foram finalizadas."
    )

    dashboard = {
        "total_status": total_status_text,
        "progress_message": dashboard_record.get("progress_message") or computed_progress_message,
        "next_focus": next_focus,
        "next_focus_details": next_focus_details,
        "general_note": dashboard_record.get("general_note") or "Status geral atualizado",
        "general_details": dashboard_record.get("general_details") or "Utilize os botões de conclusão para registrar o andamento de cada macro fase.",
        "statuses": statuses,
    }

    return {
        "plan": plan,
        "macro_phases": macro_phases,
        "checkpoints": checkpoints,
        "dashboard": dashboard,
    }


def load_alignment_canvas(db, plan_id: int) -> Dict[str, Any]:
    members = db.list_alignment_members(plan_id)
    overview = db.get_alignment_overview(plan_id) or {}
    principles_records = db.list_alignment_principles(plan_id)

    socios = [
        {
            "id": member.get("id"),
            "nome": member.get("name"),
            "papel": member.get("role"),
            "motivacao": member.get("motivation"),
            "compromisso": member.get("commitment"),
            "risco": member.get("risk"),
        }
        for member in members
    ]

    criterios = overview.get("decision_criteria") or []
    if isinstance(principles_records, list) and not criterios:
        criterios = [item.get("principle") for item in principles_records if item.get("principle")]

    alinhamento = {
        "visao_compartilhada": overview.get("shared_vision"),
        "metas_financeiras": overview.get("financial_goals"),
        "criterios_decisao": criterios,
        "notas": overview.get("notes"),
    }

    return {
        "socios": socios,
        "alinhamento": alinhamento,
    }


def load_alignment_project(db, plan_id: int) -> Dict[str, Any]:
    project = db.get_alignment_project(plan_id) or {}
    observacoes = project.get("observations") or []
    if isinstance(observacoes, dict):
        observacoes = observacoes.get("itens") or list(observacoes.values())
    if not isinstance(observacoes, list):
        observacoes = [observacoes] if observacoes else []

    return {
        "nome": project.get("project_name") or "PEV - Planejamento | Agenda do Planejamento",
        "descricao": project.get("description"),
        "observacoes": observacoes,
        "grv_project_id": project.get("grv_project_id"),
    }


def load_alignment_agenda(db, plan_id: int) -> Dict[str, Any]:
    project = load_alignment_project(db, plan_id)
    agenda_records = db.list_alignment_agenda(plan_id)
    atividades = [
        {
            "oque": item.get("action_title"),
            "quem": item.get("owner_name"),
            "quando": item.get("schedule_info"),
            "como": item.get("execution_info"),
        }
        for item in agenda_records
    ]
    return {"projeto": project, "atividades": atividades}


def load_segments(db, plan_id: int) -> List[Dict[str, Any]]:
    segments = db.list_plan_segments(plan_id)
    prepared: List[Dict[str, Any]] = []
    for record in segments:
        strategy = _ensure_dict(record.get("strategy"))
        value_prop = _ensure_dict(strategy.get("value_proposition"))
        monetization = _ensure_dict(strategy.get("monetization"))
        personas = _ensure_list(record.get("personas"))
        for persona in personas:
            if isinstance(persona, dict):
                persona.setdefault("jornada", persona.get("jornada") or persona.get("journey") or [])
        prepared.append(
            {
                "id": record.get("id"),
                "nome": record.get("name"),
                "descricao": record.get("description"),
                "audiences": _ensure_list(record.get("audiences")),
                "differentials": _ensure_list(record.get("differentials")),
                "evidences": _ensure_list(record.get("evidences")),
                "personas": personas,
                "strategy": strategy,
                "value_proposition": value_prop,
                "monetization": monetization,
                "competitive_matrix": _ensure_list(record.get("competitors_matrix") or strategy.get("competitive_matrix")),
                "journey_triggers": _ensure_dict(strategy.get("journey_triggers")),
                "persona_overview": strategy.get("persona_overview") or strategy.get("persona_description"),
                "positioning": _ensure_dict(strategy.get("positioning")),
            }
        )
    return prepared


def build_value_canvas_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for segment in segments:
        value_prop = segment.get("value_proposition", {})
        monetization = segment.get("monetization", {})
        data.append(
            {
                "id": segment.get("id"),
                "nome": segment.get("nome"),
                "descricao": segment.get("descricao"),
                "proposta": {
                    "segmentos": segment.get("audiences") or [],
                    "problemas": value_prop.get("problems") or value_prop.get("dor") or [],
                    "solucao": value_prop.get("solution") or value_prop.get("solucao"),
                    "diferenciais": segment.get("differentials") or [],
                    "provas": segment.get("evidences") or [],
                },
                "monetizacao": {
                    "fontes_receita": monetization.get("revenue_streams") or monetization.get("receitas") or [],
                    "estrutura_custos": monetization.get("cost_structure") or monetization.get("custos") or [],
                    "parcerias_chave": monetization.get("key_partners") or monetization.get("parcerias") or [],
                },
            }
        )
    return data


def build_persona_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    persona_segments: List[Dict[str, Any]] = []
    for segment in segments:
        triggers = segment.get("journey_triggers") or {}
        persona_segments.append(
            {
                "id": segment.get("id"),
                "nome": segment.get("nome"),
                "persona_descricao": segment.get("persona_overview"),
                "personas": segment.get("personas") or [],
                "gatilhos": triggers,
            }
        )
    return persona_segments


def build_competitive_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    comp_segments: List[Dict[str, Any]] = []
    for segment in segments:
        positioning = segment.get("positioning") or {}
        comp_segments.append(
            {
                "id": segment.get("id"),
                "nome": segment.get("nome"),
                "descricao": segment.get("descricao"),
                "matriz": segment.get("competitive_matrix") or [],
                "estrategia": {
                    "posicionamento": positioning.get("narrative") or positioning.get("posicionamento"),
                    "promessa": positioning.get("promise") or positioning.get("promessa"),
                    "proximos_passos": positioning.get("next_steps") or positioning.get("proximos_passos") or [],
                },
                "proposta": {
                    "publico": segment.get("audiences") or [],
                    "diferenciais": segment.get("differentials") or [],
                    "comprobacoes": segment.get("evidences") or [],
                },
                "personas": segment.get("personas") or [],
            }
        )
    return comp_segments


def load_structures(db, plan_id: int) -> List[Dict[str, Any]]:
    rows = db.list_plan_structures(plan_id)
    installments = db.list_plan_structure_installments(plan_id)

    installments_map: Dict[int, List[Dict[str, Any]]] = {}
    for inst in installments:
        structure_id = inst.get("structure_id")
        installments_map.setdefault(structure_id, []).append(
            {
                "numero": inst.get("installment_number"),
                "valor": inst.get("amount"),
                "vencimento": inst.get("due_info"),
                "tipo": inst.get("installment_type"),
            }
        )

    area_map: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        area_key_raw = (row.get("area") or "").lower()
        area_name = AREA_LABELS.get(area_key_raw, row.get("area") or "Outros")

        block_key_raw = (row.get("block") or "").lower().replace(" ", "_")
        block_name = BLOCK_LABELS.get(block_key_raw, row.get("block") or "Outros")

        area_entry = area_map.setdefault(
            area_name,
            {
                "id": area_key_raw or area_name.lower().replace(" ", "_"),
                "nome": area_name,
                "blocos": {},
            },
        )

        blocos = area_entry["blocos"]
        bloco_entry = blocos.setdefault(
            block_name,
            {
                "nome": block_name,
                "itens": [],
            },
        )

        structure_id = row.get("id")
        parcelas = installments_map.get(structure_id, [])
        payment_form = row.get("payment_form") or ("Conforme parcelas" if parcelas else "A definir")
        bloco_entry["itens"].append(
            {
                "id": structure_id,
                "tipo": row.get("item_type"),
                "descricao": row.get("description"),
                "valor": row.get("value"),
                "repeticao": row.get("repetition"),
                "forma_pagamento": payment_form,
                "data_aquisicao": row.get("acquisition_info"),
                "fornecedor": row.get("supplier"),
                "data_disponibilizacao": row.get("availability_info"),
                "observacoes": row.get("observations"),
                "status": row.get("status"),
                "parcelas": parcelas,
            }
        )

    ordered_areas: List[Dict[str, Any]] = []
    for area_name in AREA_ORDER:
        if area_name in area_map:
            ordered_areas.append(area_map.pop(area_name))
    ordered_areas.extend(area_map.values())

    # Convert bloco dicts to sorted lists
    for area in ordered_areas:
        blocos_dict = area.get("blocos", {})
        blocos_list = list(blocos_dict.values())
        area["blocos"] = blocos_list

    return ordered_areas


def summarize_structures_for_report(structures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for area in structures:
        area_summary = {"area": area.get("nome"), "resumo": []}
        for bloco in area.get("blocos", []):
            pontos = [item.get("descricao") for item in bloco.get("itens", []) if item.get("descricao")]
            if not pontos:
                continue
            area_summary["resumo"].append({"escopo": bloco.get("nome"), "pontos": pontos[:5]})
        summary.append(area_summary)
    return summary


def load_financial_model(db, plan_id: int) -> Dict[str, Any]:
    premises = db.list_plan_finance_premises(plan_id)
    investments = db.list_plan_finance_investments(plan_id)
    sources = db.list_plan_finance_sources(plan_id)
    business_periods = db.list_plan_finance_business_periods(plan_id)
    distribution = db.list_plan_finance_business_distribution(plan_id)
    variable_costs = db.list_plan_finance_variable_costs(plan_id)
    result_rules = db.list_plan_finance_result_rules(plan_id)
    investor_periods = db.list_plan_finance_investor_periods(plan_id)
    metrics = db.get_plan_finance_metrics(plan_id) or {}

    distribution_map: Dict[int, List[Dict[str, Any]]] = {}
    for item in distribution:
        period_id = item.get("period_id")
        distribution_map.setdefault(period_id, []).append(
            {
                "descricao": item.get("description"),
                "valor": item.get("amount"),
            }
        )

    business_periods_prepared = []
    for period in business_periods:
        pid = period.get("id")
        business_periods_prepared.append(
            {
                "periodo": period.get("period_label"),
                "receita": period.get("revenue"),
                "variaveis": period.get("variables"),
                "margem_contribuicao": period.get("contribution_margin"),
                "fixos": period.get("fixed_costs"),
                "resultado_operacional": period.get("operating_result"),
                "destinacao": distribution_map.get(pid, []),
                "resultado_periodo": period.get("result_period"),
            }
        )

    investor_periods_prepared = [
        {
            "periodo": item.get("period_label"),
            "aporte": item.get("contribution"),
            "distribuicao": item.get("distribution"),
            "saldo": item.get("balance"),
            "acumulado": item.get("cumulative"),
        }
        for item in investor_periods
    ]

    return {
        "premissas": [
            {
                "id": item.get("id"),
                "indicador": item.get("description"),
                "sugestao": item.get("suggestion"),
                "ajustado": item.get("adjusted"),
                "observacoes": item.get("observations"),
                "memoria": item.get("memory"),
            }
            for item in premises
        ],
        "investimento": {
            "investimento": [
                {
                    "id": item.get("id"),
                    "descricao": item.get("description"),
                    "valor": item.get("amount")
                }
                for item in investments
            ],
            "fontes": [
                {
                    "id": item.get("id"),
                    "categoria": item.get("category"),
                    "descricao": item.get("description"),
                    "valor": item.get("amount"),
                    "disponibilidade": item.get("availability"),
                }
                for item in sources
            ],
        },
        "fluxo_negocio": {
            "periodos": business_periods_prepared,
            "variaveis": [
                {
                    "id": item.get("id"),
                    "descricao": item.get("description"),
                    "percentual": item.get("percentage")
                }
                for item in variable_costs
            ],
            "destinacao_regras": [
                {
                    "id": item.get("id"),
                    "descricao": item.get("description"),
                    "percentual": item.get("percentage"),
                    "periodicidade": item.get("periodicity"),
                }
                for item in result_rules
            ],
        },
        "fluxo_investidor": {
            "periodos": investor_periods_prepared,
            "analises": {
                "payback": metrics.get("payback"),
                "tir_5_anos": metrics.get("tir"),
                "comentarios": metrics.get("notes") or "",
            },
        },
    }


def build_final_report_payload(
    plan: Dict[str, Any],
    alignment_canvas: Dict[str, Any],
    alignment_project: Dict[str, Any],
    principles: List[Dict[str, Any]],
    segments_for_report: List[Dict[str, Any]],
    structures_summary: List[Dict[str, Any]],
    financial_model: Dict[str, Any],
) -> Dict[str, Any]:
    principles_list = [item.get("principle") for item in principles if item.get("principle")]
    alignment_section = {
        "socios": alignment_canvas.get("socios", []),
        "agenda": alignment_canvas.get("proximos_passos", []),
        "principios": principles_list,
        "visao": alignment_canvas.get("alinhamento", {}).get("visao_compartilhada"),
        "metas": alignment_canvas.get("alinhamento", {}).get("metas_financeiras"),
    }

    return {
        "plan": plan,
        "alinhamento": alignment_section,
        "segmentos": segments_for_report,
        "estruturas": structures_summary,
        "financeiro": financial_model,
        "issued_at": datetime.now().strftime("%d/%m/%Y às %H:%M"),
        "projeto": alignment_project,
    }
