from __future__ import annotations

from typing import Optional, Sequence

from models import db
from models.contracts import ContractCatalogItem
from schemas.contracts import ContractCatalogItemInput, ContractCatalogItemUpdateInput


class ContractsCatalogService:
    MAX_DEPTH = 2

    @staticmethod
    def _normalize_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "on", "yes", "sim"}

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def _ensure_company_scope(company_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Optional[str]:
        if company_id is None:
            return "Empresa obrigatória para o catálogo de itens."
        if allowed_company_ids is not None and company_id not in set(allowed_company_ids):
            return "Acesso negado ao catálogo de itens desta empresa."
        return None

    @staticmethod
    def _compose_code(parent_code: Optional[str], suffix: str) -> str:
        normalized_suffix = str(suffix or "").strip()
        if not normalized_suffix:
            raise ValueError("Informe o complemento do código.")
        return f"{parent_code}.{normalized_suffix}" if parent_code else normalized_suffix

    @staticmethod
    def _next_root_suffix(company_id: int) -> str:
        last_number = 0
        rows = ContractCatalogItem.query.with_entities(ContractCatalogItem.code).filter(
            ContractCatalogItem.company_id == company_id,
            ContractCatalogItem.parent_id.is_(None),
            ContractCatalogItem.deleted_at.is_(None),
        ).all()
        for (code,) in rows:
            raw = str(code or "").strip().split(".")[0]
            if raw.isdigit():
                last_number = max(last_number, int(raw))
        return f"{last_number + 1:03d}"

    @staticmethod
    def _resolve_parent(company_id: int, parent_id: Optional[int]) -> Optional[ContractCatalogItem]:
        if not parent_id:
            return None
        return ContractCatalogItem.query.filter(
            ContractCatalogItem.id == parent_id,
            ContractCatalogItem.company_id == company_id,
            ContractCatalogItem.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _get_depth(item: Optional[ContractCatalogItem]) -> int:
        depth = 0
        current = item
        while current and current.parent_id:
            depth += 1
            current = ContractsCatalogService._resolve_parent(current.company_id, current.parent_id)
        return depth

    @staticmethod
    def _get_level_key(item: Optional[ContractCatalogItem]) -> str:
        depth = ContractsCatalogService._get_depth(item)
        if depth <= 0:
            return "group"
        if depth == 1:
            return "subgroup"
        return "item"

    @staticmethod
    def get_level_label(item: Optional[ContractCatalogItem]) -> str:
        labels = {
            "group": "Grupo",
            "subgroup": "Sub-Grupo",
            "item": "Item",
        }
        return labels[ContractsCatalogService._get_level_key(item)]

    @staticmethod
    def _count_descendant_levels(item: Optional[ContractCatalogItem]) -> int:
        if not item:
            return 0
        children = ContractCatalogItem.query.filter(
            ContractCatalogItem.parent_id == item.id,
            ContractCatalogItem.company_id == item.company_id,
            ContractCatalogItem.deleted_at.is_(None),
        ).all()
        if not children:
            return 0
        return 1 + max(ContractsCatalogService._count_descendant_levels(child) for child in children)

    @staticmethod
    def _is_selectable_level(item: Optional[ContractCatalogItem]) -> bool:
        return ContractsCatalogService._get_level_key(item) == "item"

    @staticmethod
    def _validate_hierarchy(company_id: int, parent: Optional[ContractCatalogItem], item: Optional[ContractCatalogItem] = None) -> int:
        parent_depth = ContractsCatalogService._get_depth(parent) if parent else -1
        new_depth = parent_depth + 1
        if new_depth > ContractsCatalogService.MAX_DEPTH:
            raise ValueError("A estrutura permite somente Grupo, Sub-Grupo e Item.")
        subtree_depth = ContractsCatalogService._count_descendant_levels(item) if item else 0
        if new_depth + subtree_depth > ContractsCatalogService.MAX_DEPTH:
            raise ValueError("A movimentação excede a hierarquia permitida de Grupo, Sub-Grupo e Item.")
        return new_depth

    @staticmethod
    def list_parent_candidates(company_id: int, selected_item_id: Optional[int] = None):
        candidates = ContractsCatalogService.list_items(company_id)
        filtered = []
        for item in candidates:
            if selected_item_id and item.id == selected_item_id:
                continue
            if ContractsCatalogService._get_level_key(item) == "item":
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _would_create_cycle(company_id: int, item_id: Optional[int], parent_id: Optional[int]) -> bool:
        if not item_id or not parent_id:
            return False
        if item_id == parent_id:
            return True
        current_parent_id = parent_id
        while current_parent_id:
            parent = ContractsCatalogService._resolve_parent(company_id, current_parent_id)
            if not parent:
                return False
            if parent.id == item_id:
                return True
            current_parent_id = parent.parent_id
        return False

    @staticmethod
    def list_items(company_id: int):
        return (
            ContractCatalogItem.query.filter(
                ContractCatalogItem.company_id == company_id,
                ContractCatalogItem.deleted_at.is_(None),
            )
            .order_by(ContractCatalogItem.code.asc(), ContractCatalogItem.name.asc())
            .all()
        )

    @staticmethod
    def list_selectable_items(company_id: int):
        items = (
            ContractCatalogItem.query.filter(
                ContractCatalogItem.company_id == company_id,
                ContractCatalogItem.deleted_at.is_(None),
                ContractCatalogItem.is_active.is_(True),
            )
            .order_by(ContractCatalogItem.code.asc(), ContractCatalogItem.name.asc())
            .all()
        )
        return [item for item in items if ContractsCatalogService._is_selectable_level(item)]

    @staticmethod
    def get_item(company_id: int, item_id: int) -> Optional[ContractCatalogItem]:
        return ContractCatalogItem.query.filter(
            ContractCatalogItem.id == item_id,
            ContractCatalogItem.company_id == company_id,
            ContractCatalogItem.deleted_at.is_(None),
        ).first()

    @staticmethod
    def build_tree(company_id: int) -> list[dict]:
        items = ContractsCatalogService.list_items(company_id)
        children_map: dict[int, list[ContractCatalogItem]] = {}
        roots: list[ContractCatalogItem] = []
        for item in items:
            if item.parent_id:
                children_map.setdefault(item.parent_id, []).append(item)
            else:
                roots.append(item)

        def build_node(item: ContractCatalogItem) -> dict:
            children = sorted(children_map.get(item.id, []), key=lambda entry: (entry.code or "", entry.name or ""))
            return {
                "item": item,
                "level_label": ContractsCatalogService.get_level_label(item),
                "is_selectable": ContractsCatalogService._is_selectable_level(item),
                "children": [build_node(child) for child in children],
                "child_count": len(children),
            }

        return [build_node(item) for item in sorted(roots, key=lambda entry: (entry.code or "", entry.name or ""))]

    @staticmethod
    def create_item(*, payload: dict, allowed_company_ids: Optional[Sequence[int]] = None):
        data = ContractCatalogItemInput(**payload).model_dump()
        scope_error = ContractsCatalogService._ensure_company_scope(data["company_id"], allowed_company_ids)
        if scope_error:
            raise ValueError(scope_error)

        parent = ContractsCatalogService._resolve_parent(data["company_id"], data.get("parent_id"))
        if data.get("parent_id") and not parent:
            raise ValueError("Item pai não encontrado na empresa.")
        ContractsCatalogService._validate_hierarchy(data["company_id"], parent)

        suffix = data.get("code_suffix") or (ContractsCatalogService._next_root_suffix(data["company_id"]) if parent is None else None)
        if parent is not None and not suffix:
            raise ValueError("Informe o complemento do código do subitem.")
        code = ContractsCatalogService._compose_code(parent.code if parent else None, suffix)

        existing = ContractCatalogItem.query.filter(
            ContractCatalogItem.company_id == data["company_id"],
            ContractCatalogItem.code == code,
            ContractCatalogItem.deleted_at.is_(None),
        ).first()
        if existing:
            raise ValueError("Já existe item mestre com este código na empresa.")

        record = ContractCatalogItem(
            company_id=data["company_id"],
            parent_id=parent.id if parent else None,
            code=code,
            name=data["name"],
            item_kind=data["item_kind"],
            description=data.get("description"),
            unit_code=data.get("unit_code"),
            accepts_contracting=False,
            is_active=data["is_active"],
            metadata_json=dict(data.get("metadata_json") or {}),
        )
        record.accepts_contracting = ContractsCatalogService._is_selectable_level(record)
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def update_item(*, item: ContractCatalogItem, payload: dict):
        sanitized_payload = dict(payload or {})
        sanitized_payload.pop("company_id", None)
        data = ContractCatalogItemUpdateInput(**sanitized_payload).model_dump(exclude_unset=True)

        new_parent_id = data.get("parent_id", item.parent_id)
        if ContractsCatalogService._would_create_cycle(item.company_id, item.id, new_parent_id):
            raise ValueError("Não é permitido criar ciclo entre item e subitem.")
        parent = ContractsCatalogService._resolve_parent(item.company_id, new_parent_id)
        if new_parent_id and not parent:
            raise ValueError("Item pai não encontrado na empresa.")
        ContractsCatalogService._validate_hierarchy(item.company_id, parent, item)

        if "code_suffix" in data:
            suffix = data.get("code_suffix") or None
            if parent is not None and not suffix:
                raise ValueError("Informe o complemento do código do subitem.")
            if parent is None and not suffix:
                suffix = item.code.split(".")[0]
            new_code = ContractsCatalogService._compose_code(parent.code if parent else None, suffix)
            existing = ContractCatalogItem.query.filter(
                ContractCatalogItem.company_id == item.company_id,
                ContractCatalogItem.code == new_code,
                ContractCatalogItem.id != item.id,
                ContractCatalogItem.deleted_at.is_(None),
            ).first()
            if existing:
                raise ValueError("Já existe item mestre com este código na empresa.")
            item.code = new_code

        item.parent_id = parent.id if parent else None
        if "name" in data and data["name"] is not None:
            item.name = data["name"]
        if "item_kind" in data and data["item_kind"] is not None:
            item.item_kind = data["item_kind"]
        if "description" in data:
            item.description = data["description"]
        if "unit_code" in data:
            item.unit_code = data["unit_code"]
        if "is_active" in data and data["is_active"] is not None:
            item.is_active = data["is_active"]
        if "metadata_json" in data and data["metadata_json"] is not None:
            item.metadata_json = dict(data["metadata_json"] or {})
        item.accepts_contracting = ContractsCatalogService._is_selectable_level(item)
        db.session.commit()
        return item

    @staticmethod
    def toggle_item(*, item: ContractCatalogItem, is_active: bool):
        item.is_active = bool(is_active)
        db.session.commit()
        return item

    @staticmethod
    def delete_item(*, item: ContractCatalogItem):
        has_children = ContractCatalogItem.query.filter(
            ContractCatalogItem.parent_id == item.id,
            ContractCatalogItem.company_id == item.company_id,
            ContractCatalogItem.deleted_at.is_(None),
        ).first()
        if has_children:
            raise ValueError("Exclua ou reclassifique os subitens antes de remover este item.")
        item.deleted_at = db.func.now()
        db.session.commit()
        return item
