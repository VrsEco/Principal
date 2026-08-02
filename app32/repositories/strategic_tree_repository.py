from __future__ import annotations

from models import StrategicTree, StrategicTreeContribution, StrategicTreeNode


class StrategicTreeRepository:
    @staticmethod
    def list_trees(company_id: int):
        return (
            StrategicTree.query.filter_by(company_id=company_id)
            .filter(StrategicTree.archived_at.is_(None))
            .order_by(StrategicTree.updated_at.desc(), StrategicTree.id.desc())
            .all()
        )

    @staticmethod
    def get_tree(company_id: int, tree_id: int) -> StrategicTree | None:
        return StrategicTree.query.filter_by(company_id=company_id, id=tree_id).filter(
            StrategicTree.archived_at.is_(None)
        ).first()

    @staticmethod
    def get_node(company_id: int, tree_id: int, node_id: int) -> StrategicTreeNode | None:
        return StrategicTreeNode.query.filter_by(
            company_id=company_id,
            tree_id=tree_id,
            id=node_id,
        ).filter(StrategicTreeNode.archived_at.is_(None)).first()

    @staticmethod
    def list_nodes(company_id: int, tree_id: int):
        return (
            StrategicTreeNode.query.filter_by(company_id=company_id, tree_id=tree_id)
            .filter(StrategicTreeNode.archived_at.is_(None))
            .order_by(StrategicTreeNode.sort_order.asc(), StrategicTreeNode.id.asc())
            .all()
        )

    @staticmethod
    def find_node_by_title(company_id: int, tree_id: int, title: str) -> StrategicTreeNode | None:
        return StrategicTreeNode.query.filter_by(
            company_id=company_id,
            tree_id=tree_id,
            title=title,
        ).filter(StrategicTreeNode.archived_at.is_(None)).first()

    @staticmethod
    def find_contribution_by_idempotency(company_id: int, idempotency_key: str):
        if not idempotency_key:
            return None
        return StrategicTreeContribution.query.filter_by(
            company_id=company_id,
            idempotency_key=idempotency_key,
        ).first()

    @staticmethod
    def list_contributions(company_id: int, tree_id: int, node_id: int | None = None, *, limit: int = 100):
        query = StrategicTreeContribution.query.filter_by(company_id=company_id, tree_id=tree_id).filter(
            StrategicTreeContribution.deleted_at.is_(None)
        )
        if node_id is not None:
            query = query.filter(StrategicTreeContribution.node_id == node_id)
        return query.order_by(StrategicTreeContribution.created_at.desc()).limit(limit).all()
