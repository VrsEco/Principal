from __future__ import annotations

import os
from typing import Any

from sqlalchemy.exc import IntegrityError

from models import (
    AICapability,
    AICapabilityCompanySetting,
    StrategicTree,
    StrategicTreeAuditEvent,
    StrategicTreeContribution,
    StrategicTreeNode,
    db,
)
from repositories.strategic_tree_repository import StrategicTreeRepository
from services.knowledge.strategic_tree_classification_service import StrategicTreeClassificationService
from services.knowledge.strategic_tree_policy import StrategicTreeAccessPolicy, StrategicTreeActor


class StrategicTreeError(ValueError):
    pass


class StrategicTreeService:
    CAPABILITY_KEY = "knowledge.strategic_tree"
    DEFAULT_BRANCHES = (
        "Caixa de entrada",
        "Identidade e Direcionamento",
        "Mercado e Público",
        "Produtos e Serviços",
        "Prospecção e Venda",
        "Execução e Entrega",
        "Comunicação de Valor e Continuidade",
        "Arquitetura de Processos",
    )

    def __init__(self, repository: StrategicTreeRepository | None = None):
        self.repository = repository or StrategicTreeRepository()
        self.policy = StrategicTreeAccessPolicy()
        self.classifier = StrategicTreeClassificationService()

    @classmethod
    def is_enabled(cls, company_id: int | None) -> bool:
        if not company_id:
            return False
        try:
            capability = AICapability.query.filter_by(key=cls.CAPABILITY_KEY).first()
            if capability:
                setting = AICapabilityCompanySetting.query.filter_by(
                    capability_id=capability.id,
                    company_id=int(company_id),
                ).first()
                return bool(setting and setting.is_enabled)
        except Exception:
            db.session.rollback()
        enabled_ids = {
            int(value.strip())
            for value in os.getenv("STRATEGIC_TREE_ENABLED_COMPANY_IDS", "").split(",")
            if value.strip().isdigit()
        }
        return int(company_id) in enabled_ids

    def _require_enabled(self, company_id: int) -> None:
        if not self.is_enabled(company_id):
            raise PermissionError("Árvore Estratégica não habilitada para esta empresa.")

    @staticmethod
    def _clean_text(value: Any, *, field: str, minimum: int = 1, maximum: int = 10000) -> str:
        text = str(value or "").strip()
        if len(text) < minimum:
            raise StrategicTreeError(f"{field} é obrigatório.")
        if len(text) > maximum:
            raise StrategicTreeError(f"{field} excede o limite de {maximum} caracteres.")
        return text

    @staticmethod
    def _audit(*, actor: StrategicTreeActor, event_type: str, tree_id: int | None = None, node_id: int | None = None, contribution_id: int | None = None, surface: str = "app32", metadata: dict | None = None) -> None:
        # O conteúdo bruto nunca deve ser enviado para metadata/log.
        db.session.add(StrategicTreeAuditEvent(
            company_id=actor.company_id,
            tree_id=tree_id,
            node_id=node_id,
            contribution_id=contribution_id,
            event_type=event_type,
            actor_user_id=actor.user_id,
            surface=surface,
            metadata_json=dict(metadata or {}),
        ))

    def list_trees(self, actor: StrategicTreeActor) -> dict:
        self.policy.require_read(actor)
        self._require_enabled(actor.company_id)
        trees = self.repository.list_trees(actor.company_id)
        return {"company_id": actor.company_id, "trees": [tree.to_dict() for tree in trees]}

    def create_tree(self, actor: StrategicTreeActor, *, title: str, purpose: str | None = None, surface: str = "app32") -> dict:
        self.policy.require_manage(actor)
        self._require_enabled(actor.company_id)
        title = self._clean_text(title, field="Título", maximum=180)
        purpose = str(purpose or "").strip()[:2000] or None

        tree = StrategicTree(
            company_id=actor.company_id,
            title=title,
            purpose=purpose,
            created_by_user_id=actor.user_id,
            updated_by_user_id=actor.user_id,
        )
        db.session.add(tree)
        db.session.flush()
        root = StrategicTreeNode(
            company_id=actor.company_id,
            tree_id=tree.id,
            node_type="root",
            title=title,
            summary=purpose,
            created_by_user_id=actor.user_id,
            updated_by_user_id=actor.user_id,
        )
        db.session.add(root)
        db.session.flush()
        tree.root_node_id = root.id
        for order, branch_title in enumerate(self.DEFAULT_BRANCHES, start=1):
            db.session.add(StrategicTreeNode(
                company_id=actor.company_id,
                tree_id=tree.id,
                parent_node_id=root.id,
                node_type="theme",
                title=branch_title,
                sort_order=order,
                created_by_user_id=actor.user_id,
                updated_by_user_id=actor.user_id,
            ))
        self._audit(actor=actor, event_type="tree_created", tree_id=tree.id, node_id=root.id, surface=surface)
        db.session.commit()
        return self.get_tree(actor, tree.id)

    def get_tree(self, actor: StrategicTreeActor, tree_id: int) -> dict:
        self.policy.require_read(actor)
        self._require_enabled(actor.company_id)
        tree = self.repository.get_tree(actor.company_id, int(tree_id))
        if not tree:
            raise StrategicTreeError("Árvore não encontrada.")
        nodes = self.repository.list_nodes(actor.company_id, tree.id)
        by_id = {node.id: node for node in nodes}
        root = by_id.get(tree.root_node_id)
        node_payload = root.to_dict(include_children=True) if root else None
        counts: dict[int, int] = {}
        for contribution in self.repository.list_contributions(actor.company_id, tree.id, limit=1000):
            if self.policy.can_read_contribution(actor, contribution):
                counts[contribution.node_id] = counts.get(contribution.node_id, 0) + 1
        return {
            "company_id": actor.company_id,
            "tree": tree.to_dict(),
            "root": node_payload,
            "contribution_counts": counts,
        }

    def get_branch(self, actor: StrategicTreeActor, *, tree_id: int, node_id: int) -> dict:
        self.policy.require_read(actor)
        self._require_enabled(actor.company_id)
        tree = self.repository.get_tree(actor.company_id, int(tree_id))
        node = self.repository.get_node(actor.company_id, int(tree_id), int(node_id))
        if not tree or not node:
            raise StrategicTreeError("Ramo não encontrado.")
        contributions = []
        for item in self.repository.list_contributions(actor.company_id, tree.id, node.id, limit=100):
            serialized = self.policy.serialize_contribution(actor, item)
            if serialized:
                contributions.append(serialized)
        breadcrumb = []
        current = node
        visited = set()
        while current and current.id not in visited:
            visited.add(current.id)
            breadcrumb.append({"id": current.id, "title": current.title})
            current = self.repository.get_node(actor.company_id, tree.id, current.parent_node_id) if current.parent_node_id else None
        breadcrumb.reverse()
        return {
            "company_id": actor.company_id,
            "tree": tree.to_dict(),
            "node": node.to_dict(include_children=False),
            "breadcrumb": breadcrumb,
            "contributions": contributions,
            "next_action": "Adicionar informação" if not contributions else "Discutir e aprofundar o tema",
        }

    def add_contribution(
        self,
        actor: StrategicTreeActor,
        *,
        tree_id: int,
        content: str,
        node_id: int | None = None,
        attribution_mode: str = "identified",
        visibility_scope: str = "company_authorized",
        source_type: str = "app32",
        idempotency_key: str | None = None,
        surface: str = "app32",
    ) -> dict:
        self.policy.require_contribute(actor)
        self._require_enabled(actor.company_id)
        content = self._clean_text(content, field="Informação", minimum=3, maximum=10000)
        tree = self.repository.get_tree(actor.company_id, int(tree_id))
        if not tree:
            raise StrategicTreeError("Árvore não encontrada.")
        normalized_key = str(idempotency_key or "").strip()[:120] or None
        existing = self.repository.find_contribution_by_idempotency(actor.company_id, normalized_key)
        if existing:
            return {"company_id": actor.company_id, "created": False, "contribution": self.policy.serialize_contribution(actor, existing)}

        classification = self.classifier.classify(content)
        node = self.repository.get_node(actor.company_id, tree.id, int(node_id)) if node_id else None
        should_route = not node or node.node_type == "root" or node.title == "Caixa de entrada"
        if should_route and not classification["ambiguity"]:
            node = self.repository.find_node_by_title(
                actor.company_id,
                tree.id,
                classification["suggested_branch_title"],
            )
        if not node:
            node = self.repository.get_node(actor.company_id, tree.id, tree.root_node_id)
        if not node:
            raise StrategicTreeError("A árvore não possui ramo válido para receber a informação.")

        attribution_mode = str(attribution_mode or "identified").strip().lower()
        if attribution_mode not in {"identified", "confidential"}:
            raise StrategicTreeError("Modalidade de atribuição indisponível no MVP.")
        visibility_scope = str(visibility_scope or "company_authorized").strip().lower()
        if visibility_scope not in {"company_authorized", "author_only", "consultant", "squad_client", "squad_versus"}:
            raise StrategicTreeError("Escopo de visibilidade inválido.")

        contribution = StrategicTreeContribution(
            company_id=actor.company_id,
            tree_id=tree.id,
            node_id=node.id,
            contribution_type=classification["suggested_contribution_type"],
            source_type=str(source_type or "app32")[:40],
            attribution_mode=attribution_mode,
            author_user_id=actor.user_id,
            raw_content=content,
            sanitized_content=("Informação confidencial registrada para análise autorizada." if attribution_mode == "confidential" else None),
            classification_json=classification,
            confidence_state="proposed",
            sensitivity_level="confidential" if attribution_mode == "confidential" else "internal",
            visibility_scope="consultant" if attribution_mode == "confidential" else visibility_scope,
            idempotency_key=normalized_key,
        )
        db.session.add(contribution)
        db.session.flush()
        self._audit(
            actor=actor,
            event_type="contribution_created",
            tree_id=tree.id,
            node_id=node.id,
            contribution_id=contribution.id,
            surface=surface,
            metadata={"classification": classification["suggested_branch_title"], "attribution_mode": attribution_mode},
        )
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = self.repository.find_contribution_by_idempotency(actor.company_id, normalized_key)
            if existing:
                return {"company_id": actor.company_id, "created": False, "contribution": self.policy.serialize_contribution(actor, existing)}
            raise
        return {
            "company_id": actor.company_id,
            "created": True,
            "contribution": self.policy.serialize_contribution(actor, contribution),
            "classified_branch": {"id": node.id, "title": node.title},
            "next_action": "Revisar a classificação e continuar a discussão",
        }
