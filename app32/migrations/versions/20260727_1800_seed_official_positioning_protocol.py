"""seed official positioning maturity protocol

Revision ID: 20260727_1800
Revises: 20260723_1000
Create Date: 2026-07-27 18:00:00
"""

import json

import sqlalchemy as sa
from alembic import op


revision = "20260727_1800"
down_revision = "20260723_1000"
branch_labels = None
depends_on = None


SUBPHASE_KEY = "positioning"
PROTOCOL_VERSION = "positioning-official-v1.0"
TITLE = "Protocolo Oficial de Amadurecimento do Posicionamento"
OBJECTIVE = (
    "Definir cliente prioritário, problema relevante, categoria, proposta de valor, "
    "diferenciais defensáveis e provas, conectando percepção de mercado à capacidade real de entrega."
)
QUESTIONS = [
    "Quem é o cliente prioritário, em qual situação de compra e por que esse recorte é estratégico para a empresa?",
    "Qual problema relevante, necessidade ou trabalho a realizar faz esse cliente buscar uma solução?",
    "Em qual categoria de referência a empresa deseja ser comparada e quais alternativas reais o cliente considera?",
    "Qual valor ou resultado específico a empresa promete entregar e como o cliente deve percebê-lo?",
    "Quais atributos são requisitos básicos da categoria e quais diferenciais são relevantes, comprováveis e defensáveis?",
    "Quais evidências, capacidades, processos, ofertas e experiências sustentam cada promessa e diferencial declarado?",
    "O que a empresa deliberadamente não pretende ser, atender ou prometer para preservar foco e coerência?",
    "Como o Posicionamento se conecta à Missão, Visão, Valores, ICP, ofertas, preços, canais, experiência e Planejamento Estratégico?",
]

PROMPT = """# Protocolo Oficial de Amadurecimento do Posicionamento

Atue pelo princípio MCP First e mantenha todas as leituras e escritas isoladas pelo `company_id` autorizado.

1. Chame `consultive_get_next_action` e `consultive_resolve_protocol`.
2. Leia contexto, evidências e gaps antes da entrevista.
3. Faça as oito perguntas obrigatórias e diferencie fala humana, dado APP32, percepção externa, benchmark e hipótese da IA.
4. Pesquise profundamente clientes, concorrentes, substitutos, pares no Brasil e no mundo e critérios reais de escolha, priorizando fontes primárias e pesquisa com clientes quando disponível.
5. Registre links, datas, recorte, premissas, limitações e grau de comparabilidade.
6. Separe requisito básico da categoria de diferencial relevante, comprovável e defensável.
7. Simule aderência para segmentos prioritários em cenários favorável, base e adverso e teste riscos de promessa, percepção e capacidade.
8. Confronte o Posicionamento com MVV, ICP, ofertas, preços, canais, experiência, processos e capacidades reais.
9. Não reduza Posicionamento a slogan, campanha, texto institucional ou intenção interna não percebida pelo mercado.
10. Apresente o payload exato e obtenha confirmação humana antes de qualquer escrita.
11. Não grave dado canônico, não valide por outro Squad e não decida em nome do consultor.
"""


def _protocol_json():
    return {
        "journey_ref": "structuring-journey-v2.1",
        "journey_version": "positioning-maturity-v1.0",
        "investigation_layers": [
            "priority_customer_and_buying_context",
            "problem_and_job_to_be_done",
            "category_and_alternatives",
            "value_proposition_and_reasons_to_believe",
            "defensible_differentiation",
            "market_perception_and_scenario_simulation",
            "strategic_and_operational_coherence",
        ],
        "required_questions": QUESTIONS,
        "research_contract": {
            "deep_and_broad_when_applicable": True,
            "scope": [
                "clientes_e_criterios_de_escolha",
                "concorrentes_e_substitutos",
                "pares_brasil",
                "pares_mundo",
                "categoria_e_percepcao_de_mercado",
            ],
            "source_priority": "fontes_primarias_e_evidencia_de_cliente",
            "required_metadata": [
                "link",
                "access_date",
                "scope",
                "premises",
                "limitations",
            ],
            "benchmark_is_reference_not_copy": True,
            "declared_positioning_is_not_market_perception": True,
        },
        "evidence_contract": {
            "human_evidence_required": True,
            "internal_evidence_required": True,
            "benchmark_or_justification_required": True,
            "classifications": ["declared", "audited", "externally_perceived"],
        },
        "eligibility_contract": {
            "analysis_type": "methodological",
            "subphase_key": SUBPHASE_KEY,
            "required_content": [
                "diagnosis",
                "human_evidence",
                "internal_evidence",
                "risks",
                "recommendations",
                "benchmarks_or_justification",
            ],
        },
        "coherence_contract": {
            "compare_with": [
                "mission",
                "vision",
                "values",
                "segments_icp",
                "offers",
                "pricing",
                "channels",
                "customer_experience",
                "processes",
                "growth_plan",
            ],
            "final_identity_coherence_review_required": True,
        },
        "simulation_contract": {
            "scenarios": ["favorable", "base", "adverse"],
            "test_dimensions": [
                "segment_fit",
                "problem_relevance",
                "message_clarity",
                "differentiation",
                "proof",
                "delivery_capability",
            ],
        },
        "validation_sequence": [
            "client",
            "versus",
            "engineering_when_required",
            "consultant",
        ],
        "write_policy": {
            "requires_explicit_human_confirmation": True,
            "canonical_write_allowed_before_consultant_decision": False,
            "reread_after_mutation": True,
        },
        "journey_guide": {
            "entry_state": "collecting_evidence",
            "states": [
                "collecting_evidence",
                "awaiting_client_validation",
                "awaiting_versus_validation",
                "awaiting_engineering_validation",
                "awaiting_consultant_decision",
                "ready_for_authorized_execution",
                "blocked",
            ],
            "human_gate_required": True,
            "canonical_write_requires": [
                "consultant_decision",
                "authorized_executor",
            ],
        },
    }


def _insert_protocol(bind, *, company_id, notes):
    exists = bind.execute(
        sa.text(
            """
            SELECT 1
              FROM public.consultive_protocols
             WHERE company_id IS NOT DISTINCT FROM CAST(:company_id AS INTEGER)
               AND front_key = 'identity'
               AND subphase_key = :subphase_key
               AND audience = 'ai_cli'
               AND status = 'active'
             LIMIT 1
            """
        ),
        {"company_id": company_id, "subphase_key": SUBPHASE_KEY},
    ).scalar()
    if exists:
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO public.consultive_protocols (
                company_id, front_key, subphase_key, audience, depth_level, status,
                protocol_version, title, objective, prompt_markdown, protocol_json,
                notes, approved_at, created_at, updated_at
            ) VALUES (
                CAST(:company_id AS INTEGER), 'identity', :subphase_key, 'ai_cli',
                'simulation', 'active', :protocol_version, :title, :objective,
                :prompt_markdown, CAST(:protocol_json AS JSONB), :notes,
                NOW(), NOW(), NOW()
            )
            """
        ),
        {
            "company_id": company_id,
            "subphase_key": SUBPHASE_KEY,
            "protocol_version": PROTOCOL_VERSION,
            "title": TITLE,
            "objective": OBJECTIVE,
            "prompt_markdown": PROMPT,
            "protocol_json": json.dumps(_protocol_json(), ensure_ascii=False),
            "notes": notes,
        },
    )


def upgrade():
    bind = op.get_bind()
    _insert_protocol(
        bind,
        company_id=None,
        notes=f"seed:{PROTOCOL_VERSION}:global",
    )

    versus_company_id = bind.execute(
        sa.text(
            """
            SELECT id
              FROM public.companies
             WHERE client_code = 'AA'
             ORDER BY id
             LIMIT 1
            """
        )
    ).scalar()
    if versus_company_id is not None:
        _insert_protocol(
            bind,
            company_id=versus_company_id,
            notes=f"seed:{PROTOCOL_VERSION}:tenant-aa",
        )


def downgrade():
    op.get_bind().execute(
        sa.text(
            """
            DELETE FROM public.consultive_protocols
             WHERE protocol_version = :protocol_version
               AND notes LIKE 'seed:%'
            """
        ),
        {"protocol_version": PROTOCOL_VERSION},
    )
