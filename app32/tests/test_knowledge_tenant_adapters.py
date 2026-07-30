from __future__ import annotations

import os
import sys
from datetime import date, datetime
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge.adapters.meeting import MeetingKnowledgeAdapter
from services.knowledge.adapters.process_publication import (
    ProcessPublicationKnowledgeAdapter,
)


def _publication(**overrides):
    values = {
        "id": 41,
        "company_id": 7,
        "process_id": 13,
        "publication_version": 3,
        "visibility_scope": "restricted",
        "title": "Venda para pessoa jurídica",
        "summary": "Procedimento comercial oficial.",
        "slug": "venda-pessoa-juridica",
        "published_at": datetime(2026, 7, 29, 9, 0),
        "updated_at": datetime(2026, 7, 30, 10, 0),
        "content_snapshot_json": {
            "objective": "Orientar o cadastro e a venda.",
            "steps": [
                {"title": "Validar CNPJ", "description": "Consultar situação cadastral."},
                {"title": "Emitir proposta", "description": "Registrar condições."},
            ],
            "svg_snapshot": "<svg>não indexar</svg>",
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _grant(scope, *, user_id=None, employee_id=None):
    return SimpleNamespace(
        grant_scope=scope,
        user_id=user_id,
        employee_id=employee_id,
    )


def _meeting(**overrides):
    values = {
        "id": 91,
        "company_id": 7,
        "project_id": 22,
        "title": "Reunião de infraestrutura",
        "status": "completed",
        "meeting_notes": "A manutenção elétrica preventiva será da equipe predial.",
        "agenda_json": [{"topic": "Manutenção elétrica"}],
        "discussions_json": [{"decision": "Equipe predial responsável"}],
        "activities_json": [{"activity": "Criar plano preventivo", "owner": "Ana"}],
        "participants_json": {"internal": [{"employee_id": 101}]},
        "guests_json": {"internal": [{"id": 102}]},
        "actual_date": date(2026, 7, 28),
        "actual_time": "14:30",
        "created_at": datetime(2026, 7, 28, 13, 0),
        "updated_at": datetime(2026, 7, 29, 8, 0),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _employee(employee_id, name):
    return SimpleNamespace(id=employee_id, name=name)


def test_process_publication_projects_content_and_supported_grants():
    document = ProcessPublicationKnowledgeAdapter()._build_document(
        _publication(),
        [
            _grant("employee", employee_id=101),
            _grant("user", user_id=15),
            _grant("process"),
        ],
    )

    assert document.source_ref == "process-publication:41"
    assert document.knowledge_kind == "procedure"
    assert {item.grant_scope for item in document.grants} == {"employee", "user"}
    assert document.metadata["unsupported_grants_ignored"] == 1
    content = "\n".join(chunk.content for chunk in document.chunks)
    assert "Validar CNPJ" in content
    assert "não indexar" not in content


def test_company_process_publication_receives_company_grant():
    document = ProcessPublicationKnowledgeAdapter()._build_document(
        _publication(visibility_scope="company"),
        [],
    )

    assert [(item.grant_scope, item.user_id, item.employee_id) for item in document.grants] == [
        ("company", None, None)
    ]


def test_completed_meeting_projects_minutes_sections_and_employee_grants():
    employees = {
        101: _employee(101, "Ana"),
        102: _employee(102, "Bruno"),
    }
    document = MeetingKnowledgeAdapter()._build_document(
        _meeting(),
        employees_by_id=employees,
    )

    assert document.source_ref == "meeting:91"
    assert document.knowledge_kind == "decision_record"
    assert [item.employee_id for item in document.grants] == [101, 102]
    assert document.metadata["grant_resolution"] == "resolved"
    content = "\n".join(chunk.content for chunk in document.chunks)
    assert "manutenção elétrica preventiva" in content
    assert "Equipe predial responsável" in content
    assert "Criar plano preventivo" in content


def test_meeting_without_resolvable_participant_fails_closed():
    document = MeetingKnowledgeAdapter()._build_document(
        _meeting(
            participants_json={"internal": [{"name": "Sem identificador"}]},
            guests_json=[],
        )
    )

    assert document.grants == ()
    assert document.metadata["grant_resolution"] == "unresolved_fail_closed"


def test_meeting_ignores_stale_employee_identifier():
    document = MeetingKnowledgeAdapter()._build_document(
        _meeting(
            participants_json={"internal": [{"employee_id": 999}]},
            guests_json=[],
        ),
        employees_by_id={101: _employee(101, "Ana")},
    )

    assert document.grants == ()


def test_meeting_resolves_unique_active_employee_by_name():
    employee = _employee(101, "Ana Souza")
    document = MeetingKnowledgeAdapter()._build_document(
        _meeting(
            participants_json={"internal": [{"name": "  ANA   SOUZA "}]},
            guests_json=[],
        ),
        employees_by_name={"ana souza": [employee]},
    )

    assert [item.employee_id for item in document.grants] == [101]


@pytest.mark.parametrize(
    "adapter",
    [ProcessPublicationKnowledgeAdapter(), MeetingKnowledgeAdapter()],
)
def test_tenant_adapters_require_positive_company(adapter):
    with pytest.raises(ValueError):
        adapter.validate_scope(company_id=None)
