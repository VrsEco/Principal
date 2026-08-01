from __future__ import annotations

import os
import sys

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import db
from models.company import Company
from models.knowledge import (
    KnowledgeChunk,
    KnowledgeIndexRun,
    KnowledgeSource,
    KnowledgeSourceGrant,
)
from services.knowledge.query_service import (
    KnowledgeQueryService,
    KnowledgeTenantContextError,
)


@pytest.fixture()
def knowledge_app():
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TESTING=True,
    )
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                Company.__table__,
                KnowledgeSource.__table__,
                KnowledgeSourceGrant.__table__,
                KnowledgeChunk.__table__,
                KnowledgeIndexRun.__table__,
            ],
        )
        db.session.add_all(
            [
                Company(id=1, name="Empresa Um"),
                Company(id=2, name="Empresa Dois"),
            ]
        )
        product = KnowledgeSource(
            knowledge_scope="product",
            company_id=None,
            source_type="product_help",
            source_ref="processos.publicar",
            knowledge_kind="product_help",
            title="Publicar processo",
            canonical_uri="app-versus://help/processes/publish",
            status="published",
            authority_level="official",
            version="v1",
            module_key="processes",
            navigation_target="/process-portal",
            content_checksum="a" * 64,
        )
        product.chunks.append(
            KnowledgeChunk(
                knowledge_scope="product",
                company_id=None,
                section_key="passos",
                content="Abra Fluxo / POP, revise o processo e envie para aprovação.",
                content_checksum="b" * 64,
                source_span="passos",
            )
        )
        open_titles = KnowledgeSource(
            knowledge_scope="product",
            company_id=None,
            source_type="product_help",
            source_ref="financeiro.titulos_em_aberto",
            knowledge_kind="product_help",
            title="Consultar títulos financeiros em aberto",
            canonical_uri="app-versus://help/finance/open-titles",
            status="published",
            authority_level="official",
            version="v1",
            module_key="finance",
            navigation_target="/financial/schedules",
            metadata_json={
                "navigation_actions": [
                    {"label": "Abrir Títulos Financeiros", "target": "/financial/schedules"},
                    {
                        "label": "Abrir Relatório de Agendamentos",
                        "target": "/financial/reports/agendamento",
                    },
                ]
            },
            content_checksum="1" * 64,
        )
        open_titles.chunks.append(
            KnowledgeChunk(
                knowledge_scope="product",
                company_id=None,
                section_key="como-ver",
                content=(
                    "Como ver títulos financeiros em aberto. Abra Gestão Financeira, "
                    "selecione Agendamentos e escolha Em aberto no filtro Baixa."
                ),
                content_checksum="2" * 64,
                source_span="Como ver os títulos financeiros em aberto",
            )
        )
        tenant_one = KnowledgeSource(
            knowledge_scope="company",
            company_id=1,
            source_type="meeting",
            source_ref="meeting-1",
            knowledge_kind="decision",
            title="Decisão elétrica",
            canonical_uri="app-versus://meetings/1",
            status="published",
            authority_level="internal",
            version="v1",
            content_checksum="c" * 64,
        )
        tenant_one.chunks.append(
            KnowledgeChunk(
                knowledge_scope="company",
                company_id=1,
                section_key="decision",
                content="A manutenção elétrica preventiva ficou com a equipe predial.",
                content_checksum="d" * 64,
                source_span="decision",
            )
        )
        tenant_one.grants.append(
            KnowledgeSourceGrant(
                company_id=1,
                grant_scope="employee",
                employee_id=101,
            )
        )
        tenant_two = KnowledgeSource(
            knowledge_scope="company",
            company_id=2,
            source_type="meeting",
            source_ref="meeting-2",
            knowledge_kind="decision",
            title="Decisão gerador",
            canonical_uri="app-versus://meetings/2",
            status="published",
            authority_level="internal",
            version="v1",
            content_checksum="e" * 64,
        )
        tenant_two.chunks.append(
            KnowledgeChunk(
                knowledge_scope="company",
                company_id=2,
                section_key="decision",
                content="O gerador exclusivo pertence somente à empresa dois.",
                content_checksum="f" * 64,
                source_span="decision",
            )
        )
        tenant_two.grants.append(
            KnowledgeSourceGrant(
                company_id=2,
                grant_scope="company",
            )
        )
        db.session.add_all([product, open_titles, tenant_one, tenant_two])
        db.session.commit()
        yield app
        db.session.remove()


def test_product_help_answer_is_cited_and_has_registered_action(knowledge_app):
    with knowledge_app.app_context():
        payload = KnowledgeQueryService().answer(
            "Como publicar o processo?",
            company_id=None,
            source_types=("product_help",),
            require_company=False,
        )

    assert payload["citations"][0]["canonical_uri"] == "app-versus://help/processes/publish"
    assert payload["claims"][0]["citations"] == ["citation-1"]
    assert payload["actions"][0]["label"] == "Abrir processo (Fluxo / POP)"
    assert payload["actions"][0]["target"] == "/process-portal"
    assert payload["query_plan"]["strategies"] == ["sql", "full_text"]


def test_product_help_search_considers_source_title(knowledge_app):
    with knowledge_app.app_context():
        payload = KnowledgeQueryService().search(
            "publicar",
            company_id=1,
            source_types=("product_help",),
            require_company=False,
        )

    assert [item["source_ref"] for item in payload["results"]] == [
        "processos.publicar"
    ]


def test_company_search_never_returns_another_tenant(knowledge_app):
    with knowledge_app.app_context():
        own = KnowledgeQueryService().search(
            "manutenção elétrica",
            company_id=1,
            employee_id=101,
        )
        foreign = KnowledgeQueryService().search(
            "gerador exclusivo",
            company_id=1,
            employee_id=101,
        )

    assert [item["source_ref"] for item in own["results"]] == ["meeting-1"]
    assert foreign["results"] == []


def test_company_query_fails_closed_without_active_company(knowledge_app):
    with knowledge_app.app_context(), pytest.raises(KnowledgeTenantContextError):
        KnowledgeQueryService().answer(
            "Qual foi a decisão?",
            company_id=None,
        )


def test_answer_abstains_without_authorized_evidence(knowledge_app):
    with knowledge_app.app_context():
        payload = KnowledgeQueryService().answer(
            "tema inexistente xyz",
            company_id=1,
            employee_id=101,
        )

    assert payload["citations"] == []
    assert payload["warnings"] == ["knowledge_gap"]
    assert "Não encontrei evidência" in payload["answer"]


def test_company_search_denies_source_without_matching_grant(knowledge_app):
    with knowledge_app.app_context():
        payload = KnowledgeQueryService().search(
            "manutenção elétrica",
            company_id=1,
            employee_id=999,
        )

    assert payload["results"] == []


def test_company_only_search_does_not_mix_product_manual(knowledge_app):
    with knowledge_app.app_context():
        payload = KnowledgeQueryService().search(
            "publicar processo",
            company_id=1,
            employee_id=101,
            include_product=False,
        )

    assert payload["results"] == []
    assert payload["query_plan"]["include_product"] is False


def test_colloquial_open_financial_titles_question_returns_manual_not_workflow(knowledge_app):
    with knowledge_app.app_context():
        payload = KnowledgeQueryService().answer(
            "Como que eu faço pra ver os títulos financeiros em aberto?",
            company_id=None,
            source_types=("product_help",),
            require_company=False,
        )

    assert payload["warnings"] == []
    assert payload["citations"][0]["source_ref"] == "financeiro.titulos_em_aberto"
    assert payload["actions"][0]["target"] == "/financial/schedules"
    assert payload["actions"][1]["target"] == "/financial/reports/agendamento"
    assert "Em aberto" in payload["answer"]


def test_colloquial_question_terms_remove_guidance_noise():
    terms = KnowledgeQueryService._query_terms(
        "Como que eu faço pra ver os títulos financeiros em aberto?"
    )

    assert terms == ("títulos", "financeiros", "aberto")


def test_end_user_guidance_prefers_one_product_manual_and_hides_technical_docs():
    hits = [
        {
            "source_type": "product_help",
            "source_ref": "financeiro.titulos_em_aberto",
        },
        {
            "source_type": "system_documentation",
            "source_ref": "spec.finance.contract",
        },
        {
            "source_type": "product_help",
            "source_ref": "financeiro.agendamentos",
        },
    ]

    selected = KnowledgeQueryService._select_answer_hits(
        "Como ver os títulos financeiros em aberto?",
        hits,
    )

    assert selected == [hits[0]]


def test_technical_question_can_use_system_documentation():
    hits = [
        {
            "source_type": "system_documentation",
            "source_ref": "spec.finance.contract",
        }
    ]

    selected = KnowledgeQueryService._select_answer_hits(
        "Qual é o contrato técnico da API financeira?",
        hits,
    )

    assert selected == hits


def test_non_technical_question_drops_technical_system_documentation_only_hits():
    hits = [
        {
            "source_type": "system_documentation",
            "title": "Paper Sapiens MCP",
            "source_ref": "paper.sapiens",
            "content": "Paper v0.0 sobre MCP, runtime, adapters e arquitetura.",
            "source_span": "paper",
        }
    ]

    selected = KnowledgeQueryService._select_answer_hits(
        "como faço para ver as atividades que tenho?",
        hits,
    )

    assert selected == []


def test_non_technical_question_can_use_non_technical_system_documentation():
    hits = [
        {
            "source_type": "system_documentation",
            "title": "Manual de uso",
            "source_ref": "manual.atividades",
            "content": "Para ver suas atividades, abra Meu Trabalho no menu lateral.",
            "source_span": "manual",
        }
    ]

    selected = KnowledgeQueryService._select_answer_hits(
        "como faço para ver as atividades que tenho?",
        hits,
    )

    assert selected == hits


def test_company_evidence_is_not_replaced_by_lower_ranked_product_help():
    hits = [
        {"source_type": "meeting", "source_ref": "meeting-1"},
        {"source_type": "product_help", "source_ref": "menu.meetings"},
    ]

    selected = KnowledgeQueryService._select_answer_hits(
        "O que foi decidido na última reunião?",
        hits,
    )

    assert selected[0] == hits[0]


def test_claim_text_preserves_safe_structure_for_readable_steps():
    content = "**Opção 1**\n1. Abra Gestão Financeira.\n2. Aplique os filtros."

    assert KnowledgeQueryService._claim_text(content) == content
