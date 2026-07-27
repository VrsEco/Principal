"""seed official org chart maturity protocol

Revision ID: 20260727_2100
Revises: 20260727_1800
Create Date: 2026-07-27 21:00:00
"""

import json

import sqlalchemy as sa
from alembic import op


revision = "20260727_2100"
down_revision = "20260727_1800"
branch_labels = None
depends_on = None


SUBPHASE_KEY = "org_chart"
PROTOCOL_VERSION = "org-chart-official-v1.0"
TITLE = "Protocolo Oficial de Amadurecimento do Organograma"
OBJECTIVE = (
    "Traduzir estratégia e processos em papéis, responsabilidades, direitos de decisão, "
    "relações de reporte e capacidade organizacional, distinguindo estrutura atual, praticada e alvo."
)
QUESTIONS = [
    "Quais estratégia, processos e capacidades o Organograma precisa sustentar hoje e no crescimento planejado?",
    "Quais papéis e cargos existem de fato, quais existem apenas no desenho e quem ocupa ou acumula cada papel?",
    "Quais entregas, responsabilidades, decisões, alçadas e limites pertencem a cada papel crítico?",
    "Onde existem lacunas, sobreposições, conflitos, concentração de decisão ou dependência excessiva de uma pessoa?",
    "Quais relações de reporte, níveis, amplitudes de liderança e fóruns de decisão existem formalmente e na prática?",
    "Quem responde por processos, indicadores, projetos e Squads, e como essas responsabilidades aparecem na estrutura?",
    "Qual estrutura-alvo, capacidade, competência e sequência de implantação são necessárias para sustentar o crescimento?",
    "Como o Organograma se conecta ao MVV, Posicionamento, processos, Planejamento e Gerenciamento Estratégico, e o que a empresa deliberadamente não deve criar?",
]

PROMPT = """# Protocolo Oficial de Amadurecimento do Organograma

Atue pelo princípio MCP First e mantenha todas as leituras e escritas isoladas pelo `company_id` autorizado.

1. Chame `consultive_get_next_action` e `consultive_resolve_protocol`.
2. Leia contexto, evidências e gaps antes da entrevista, incluindo cargos, vínculos, raízes e colaboradores sem cargo.
3. Faça as oito perguntas obrigatórias e diferencie cargo, pessoa ocupante, acúmulo de papel, estrutura formal e estrutura praticada.
4. Confronte responsabilidades, entregas, decisões, alçadas, reportes, amplitude de liderança, capacidade e segregação de funções.
5. Identifique responsáveis por processos, indicadores, projetos e Squads quando aplicável.
6. Pesquise referências externas somente quando ajudarem a avaliar desenho organizacional e governança; registre fontes, recorte, premissas e limitações e não copie organogramas.
7. Separe estrutura atual de estrutura-alvo e proponha sequência de implantação compatível com porte, custo, competências e crescimento.
8. Simule operação atual, crescimento planejado e ausência ou ruptura de papel crítico.
9. Não trate desenho cadastrado, título de cargo ou fala não auditada como prova de funcionamento.
10. Apresente o payload exato e obtenha confirmação humana antes de qualquer escrita.
11. Não crie cargos, não vincule colaboradores, não altere subordinações, não valide por outro Squad e não decida em nome do consultor.
12. Encaminhe qualquer mutação canônica para decisão do consultor e executor autorizado; sem tool MCP aprovada, use a UI/API autorizada do APP32.
"""


def _protocol_json():
    return {
        "journey_ref": "structuring-journey-v2.1",
        "journey_version": "org-chart-maturity-v1.0",
        "investigation_layers": [
            "strategy_process_and_capability_demand",
            "roles_people_and_accountabilities",
            "decision_rights_and_reporting",
            "capacity_competencies_and_segregation",
            "current_practiced_and_target_structure",
            "growth_and_critical_role_simulation",
            "strategic_and_operational_coherence",
        ],
        "required_questions": QUESTIONS,
        "research_contract": {
            "deep_and_broad_when_applicable": True,
            "scope": [
                "desenho_organizacional",
                "governanca_e_direitos_de_decisao",
                "amplitude_de_lideranca",
                "segregacao_de_funcoes",
                "pares_brasil_e_mundo",
            ],
            "source_priority": "fontes_primarias_e_referencias_tecnicas",
            "required_metadata": ["link", "access_date", "scope", "premises", "limitations"],
            "benchmark_is_reference_not_copy": True,
            "external_chart_is_not_operational_evidence": True,
        },
        "evidence_contract": {
            "human_evidence_required": True,
            "internal_evidence_required": True,
            "benchmark_or_justification_required": True,
            "classifications": ["declared", "registered", "practiced", "audited"],
            "distinguish_role_from_person": True,
            "distinguish_current_from_target": True,
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
                "positioning",
                "process_architecture",
                "process_owners",
                "indicator_owners",
                "projects",
                "squads",
                "growth_plan",
                "strategic_management",
            ],
            "final_identity_coherence_review_required": True,
        },
        "simulation_contract": {
            "scenarios": ["current_operation", "planned_growth", "critical_role_absence"],
            "test_dimensions": [
                "accountability",
                "decision_flow",
                "reporting",
                "leadership_span",
                "capacity",
                "segregation_of_duties",
                "operational_continuity",
            ],
        },
        "maturity_contract": {
            "registered_chart_is_not_methodological_maturity": True,
            "requires": [
                "roles_and_hierarchy_registered",
                "active_people_linked_to_roles",
                "responsibilities_and_decision_rights_explicit",
                "critical_accountabilities_linked",
                "no_orphan_or_cyclic_relationships",
                "current_and_target_structure_distinguished",
                "implementation_and_operation_evidence",
                "periodic_review_defined",
            ],
        },
        "validation_sequence": ["client", "versus", "engineering_when_required", "consultant"],
        "write_policy": {
            "requires_explicit_human_confirmation": True,
            "canonical_write_allowed_before_consultant_decision": False,
            "canonical_org_chart_mutation_via_client_cli": False,
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
            "canonical_write_requires": ["consultant_decision", "authorized_executor"],
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
    _insert_protocol(bind, company_id=None, notes=f"seed:{PROTOCOL_VERSION}:global")

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
