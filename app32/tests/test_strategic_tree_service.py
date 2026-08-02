from __future__ import annotations

import os
import sys

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (
    AICapability,
    AICapabilityCompanySetting,
    Company,
    StrategicTree,
    StrategicTreeAuditEvent,
    StrategicTreeContribution,
    StrategicTreeNode,
    User,
    db,
)
from services.knowledge.strategic_tree_policy import StrategicTreeActor
from services.knowledge.strategic_tree_service import StrategicTreeError, StrategicTreeService


@pytest.fixture()
def strategic_tree_app():
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
                User.__table__,
                AICapability.__table__,
                AICapabilityCompanySetting.__table__,
                StrategicTree.__table__,
                StrategicTreeNode.__table__,
                StrategicTreeContribution.__table__,
                StrategicTreeAuditEvent.__table__,
            ],
        )
        db.session.add_all([
            Company(id=1, name="Empresa Um"),
            Company(id=2, name="Empresa Dois"),
            User(id=10, email="gestor@example.com", password_hash="x", name="Gestor", role="client"),
            User(id=20, email="outro@example.com", password_hash="x", name="Outro", role="client"),
        ])
        capability = AICapability(
            key="knowledge.strategic_tree",
            name="Árvore Estratégica",
            domain="knowledge",
            status="active",
            rollout_status="pilot",
        )
        db.session.add(capability)
        db.session.flush()
        db.session.add_all([
            AICapabilityCompanySetting(capability_id=capability.id, company_id=1, is_enabled=True),
            AICapabilityCompanySetting(capability_id=capability.id, company_id=2, is_enabled=True),
        ])
        db.session.commit()
        yield app
        db.session.remove()


def actor(company_id=1, user_id=10, profile="client", accessible=(1,)):
    return StrategicTreeActor(
        user_id=user_id,
        company_id=company_id,
        profile=profile,
        accessible_company_ids=accessible,
    )


def test_create_tree_builds_root_and_standard_branches(strategic_tree_app):
    with strategic_tree_app.app_context():
        result = StrategicTreeService().create_tree(
            actor(),
            title="Reestruturação da Empresa Um",
            purpose="Organizar e amadurecer o conhecimento estratégico.",
        )

        assert result["tree"]["company_id"] == 1
        assert result["root"]["node_type"] == "root"
        titles = {item["title"] for item in result["root"]["children"]}
        assert "Caixa de entrada" in titles
        assert "Mercado e Público" in titles
        assert StrategicTreeAuditEvent.query.filter_by(company_id=1, event_type="tree_created").count() == 1


def test_contribution_is_classified_and_idempotent(strategic_tree_app):
    with strategic_tree_app.app_context():
        service = StrategicTreeService()
        tree_id = service.create_tree(actor(), title="Árvore Um")["tree"]["id"]
        first = service.add_contribution(
            actor(),
            tree_id=tree_id,
            content="Precisamos estudar profundamente o mercado, os clientes e os concorrentes.",
            idempotency_key="same-request",
        )
        retry = service.add_contribution(
            actor(),
            tree_id=tree_id,
            content="Este conteúdo não deve criar outra linha.",
            idempotency_key="same-request",
        )

        assert first["created"] is True
        assert first["classified_branch"]["title"] == "Mercado e Público"
        assert retry["created"] is False
        assert retry["contribution"]["id"] == first["contribution"]["id"]
        assert StrategicTreeContribution.query.filter_by(company_id=1).count() == 1


def test_cross_tenant_tree_id_is_not_disclosed(strategic_tree_app):
    with strategic_tree_app.app_context():
        service = StrategicTreeService()
        foreign_tree_id = service.create_tree(actor(company_id=2, user_id=20, accessible=(2,)), title="Empresa Dois")["tree"]["id"]

        with pytest.raises(StrategicTreeError, match="não encontrada"):
            service.get_tree(actor(), foreign_tree_id)


def test_actor_cannot_claim_company_outside_accessible_scope(strategic_tree_app):
    with strategic_tree_app.app_context(), pytest.raises(PermissionError, match="fora do escopo"):
        StrategicTreeService().list_trees(actor(company_id=2, accessible=(1,)))


def test_confidential_contribution_is_not_exposed_to_collaborator(strategic_tree_app):
    with strategic_tree_app.app_context():
        service = StrategicTreeService()
        tree = service.create_tree(actor(), title="Árvore Confidencial")
        tree_id = tree["tree"]["id"]
        root_id = tree["root"]["id"]
        service.add_contribution(
            actor(),
            tree_id=tree_id,
            node_id=root_id,
            content="Informação sensível da direção.",
            attribution_mode="confidential",
            idempotency_key="confidential-1",
        )
        collaborator = actor(user_id=20, profile="collaborator")
        branch = service.get_branch(collaborator, tree_id=tree_id, node_id=root_id)

        assert branch["contributions"] == []
