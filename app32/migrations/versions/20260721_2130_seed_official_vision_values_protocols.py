"""seed official vision and values maturity protocols

Revision ID: 20260721_2130
Revises: 20260721_0900
Create Date: 2026-07-21 21:30:00
"""

import json

import sqlalchemy as sa
from alembic import op


revision = "20260721_2130"
down_revision = "20260721_0900"
branch_labels = None
depends_on = None


PROTOCOLS = {
    "vision": {
        "version": "vision-official-v1.0",
        "title": "Protocolo Oficial de Amadurecimento da Visão Organizacional",
        "objective": "Definir futuro desejado, horizonte e ambição sustentável, conectando cenários, capacidades e estratégia.",
        "questions": [
            "Onde os gestores querem que a empresa esteja em 3 a 5 anos e por que esse horizonte é adequado?",
            "Quais clientes, mercados, geografias, ofertas e posição competitiva compõem esse futuro desejado?",
            "Quais evidências mensuráveis permitirão reconhecer que a Visão foi alcançada?",
            "Qual ambição de crescimento ou impacto a empresa busca e o que ela deliberadamente não pretende perseguir?",
            "Quais capacidades, processos, pessoas, tecnologia e capital precisam existir para sustentar esse futuro?",
            "Quais tendências, cenários e premissas externas sustentam ou ameaçam a Visão?",
            "Quais restrições, escolhas e trade-offs podem tornar a ambição inviável ou incoerente?",
            "Como a Visão se conecta à Missão, aos Valores, ao Posicionamento e ao Planejamento Estratégico sem se transformar em uma lista de metas?",
        ],
        "layers": [
            "future_ambition",
            "time_horizon",
            "market_and_scenario_research",
            "capability_and_constraint_fit",
            "strategic_coherence",
            "future_state_simulation",
        ],
        "research_scope": ["pares_brasil", "pares_mundo", "tendencias", "cenarios", "mercado_consumidor"],
        "coherence_scope": ["mission", "values", "positioning", "growth_plan"],
        "prompt": """# Protocolo Oficial de Amadurecimento da Visão Organizacional

Atue pelo princípio MCP First e mantenha todas as leituras e escritas isoladas pelo `company_id` autorizado.

1. Chame `consultive_get_next_action` e `consultive_resolve_protocol`.
2. Leia contexto, evidências e gaps antes da entrevista.
3. Faça as oito perguntas obrigatórias e diferencie fala humana, dado APP32, benchmark e hipótese da IA.
4. Pesquise profundamente pares no Brasil e no mundo, tendências, cenários e mercado, priorizando fontes primárias.
5. Registre links, datas, recorte, premissas, limitações e grau de comparabilidade.
6. Simule os cenários favorável, base e adverso e confronte a ambição com capacidades, recursos e restrições.
7. Não transforme a Visão em meta, slogan vazio ou promessa de capacidade já comprovada.
8. Compare a Visão com Missão, Valores, Posicionamento e Planejamento Estratégico.
9. Apresente o payload exato e obtenha confirmação humana antes de qualquer escrita.
10. Não grave dado canônico, não valide por outro Squad e não decida em nome do consultor.
""",
    },
    "values": {
        "version": "values-official-v1.0",
        "title": "Protocolo Oficial de Amadurecimento dos Valores Organizacionais",
        "objective": "Converter princípios declarados em comportamentos observáveis, dilemas, anticomportamentos e evidências da cultura real.",
        "questions": [
            "Quais princípios a empresa não negocia, mesmo quando respeitá-los gera custo, atraso ou perda de receita?",
            "Qual comportamento observável demonstra cada valor no cotidiano?",
            "Quais anticomportamentos violam explicitamente cada valor?",
            "Quais decisões difíceis ou dilemas reais já colocaram esses valores à prova?",
            "Quais exemplos atuais demonstram aderência e quais revelam distância entre discurso e prática?",
            "Como processos, políticas, controles e incentivos reforçam ou contradizem cada valor?",
            "Como líderes e equipes devem agir diante de uma violação de valor?",
            "Quais evidências, indicadores ou auditorias permitirão acompanhar a prática dos valores sem reduzi-los a slogans?",
        ],
        "layers": [
            "non_negotiable_principles",
            "observable_behaviors",
            "anti_behaviors",
            "real_decision_patterns",
            "policy_and_incentive_alignment",
            "dilemma_simulation",
        ],
        "research_scope": ["boas_praticas_de_cultura", "pares_brasil", "pares_mundo", "governanca_e_incentivos"],
        "coherence_scope": ["mission", "vision", "processes", "people", "incentives"],
        "prompt": """# Protocolo Oficial de Amadurecimento dos Valores Organizacionais

Atue pelo princípio MCP First e mantenha todas as leituras e escritas isoladas pelo `company_id` autorizado.

1. Chame `consultive_get_next_action` e `consultive_resolve_protocol`.
2. Leia contexto, evidências e gaps antes da entrevista.
3. Faça as oito perguntas obrigatórias e diferencie valor declarado, comportamento observado, benchmark e hipótese da IA.
4. Pesquise boas práticas e pares comparáveis quando aplicável, priorizando fontes primárias e sem copiar listas de valores.
5. Registre links, datas, recorte, premissas e limitações.
6. Simule dilemas concretos para testar se cada valor orienta decisões sob pressão.
7. Exija comportamento esperado, anticomportamento, resposta à violação e evidência para cada valor.
8. Compare os Valores com Missão, Visão, processos, pessoas, políticas e incentivos.
9. Apresente o payload exato e obtenha confirmação humana antes de qualquer escrita.
10. Não grave dado canônico, não valide por outro Squad e não decida em nome do consultor.
""",
    },
}


def _protocol_json(subphase_key, spec):
    journey_version = f"{subphase_key}-maturity-v1.0"
    return {
        "journey_ref": "structuring-journey-v2.1",
        "journey_version": journey_version,
        "investigation_layers": spec["layers"],
        "required_questions": spec["questions"],
        "research_contract": {
            "deep_and_broad_when_applicable": True,
            "scope": spec["research_scope"],
            "source_priority": "fontes_primarias",
            "required_metadata": ["link", "access_date", "scope", "premises", "limitations"],
            "benchmark_is_reference_not_copy": True,
        },
        "evidence_contract": {
            "human_evidence_required": True,
            "internal_evidence_required": True,
            "benchmark_or_justification_required": True,
            "classifications": ["declared", "audited"],
        },
        "eligibility_contract": {
            "analysis_type": "methodological",
            "subphase_key": subphase_key,
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
            "compare_with": spec["coherence_scope"],
            "final_mvv_coherence_review_required": True,
        },
        "validation_sequence": ["client", "versus", "engineering_when_required", "consultant"],
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
            "canonical_write_requires": ["consultant_decision", "authorized_executor"],
        },
    }


def _insert_protocol(bind, *, company_id, subphase_key, spec, notes):
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
        {"company_id": company_id, "subphase_key": subphase_key},
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
            "subphase_key": subphase_key,
            "protocol_version": spec["version"],
            "title": spec["title"],
            "objective": spec["objective"],
            "prompt_markdown": spec["prompt"],
            "protocol_json": json.dumps(_protocol_json(subphase_key, spec), ensure_ascii=False),
            "notes": notes,
        },
    )


def upgrade():
    bind = op.get_bind()
    for subphase_key, spec in PROTOCOLS.items():
        _insert_protocol(
            bind,
            company_id=None,
            subphase_key=subphase_key,
            spec=spec,
            notes=f"seed:{spec['version']}:global",
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
        for subphase_key, spec in PROTOCOLS.items():
            _insert_protocol(
                bind,
                company_id=versus_company_id,
                subphase_key=subphase_key,
                spec=spec,
                notes=f"seed:{spec['version']}:tenant-aa",
            )


def downgrade():
    versions = [spec["version"] for spec in PROTOCOLS.values()]
    op.get_bind().execute(
        sa.text(
            """
            DELETE FROM public.consultive_protocols
             WHERE protocol_version IN :versions
               AND notes LIKE 'seed:%'
            """
        ).bindparams(sa.bindparam("versions", expanding=True)),
        {"versions": versions},
    )
