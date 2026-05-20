from __future__ import annotations

import re
import unicodedata
from typing import Any

from models import CompanyRolePermissionPreset, db
from services.rbac_permission_catalog_service import RbacPermissionCatalogService


class CompanyRolePermissionPresetService:
    """CRUD e serialização de presets RBAC escopados por empresa."""

    @staticmethod
    def _normalize_name(value: Any) -> str:
        return str(value or "").strip()

    @classmethod
    def _slugify(cls, value: Any) -> str:
        raw = unicodedata.normalize("NFKD", cls._normalize_name(value))
        ascii_value = raw.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value).strip("_").lower()
        return slug or "preset"

    @classmethod
    def _build_unique_key(
        cls,
        company_id: int,
        name: str,
        *,
        ignore_preset_id: int | None = None,
    ) -> str:
        base_key = f"company_{cls._slugify(name)}"
        candidate = base_key
        suffix = 2

        while True:
            query = CompanyRolePermissionPreset.query.filter_by(
                company_id=company_id,
                preset_key=candidate,
            )
            if ignore_preset_id is not None:
                query = query.filter(CompanyRolePermissionPreset.id != ignore_preset_id)
            if query.first() is None:
                return candidate
            candidate = f"{base_key}_{suffix}"
            suffix += 1

    @classmethod
    def validate_payload(cls, payload: dict[str, Any] | None) -> dict[str, Any]:
        raw = payload or {}
        name = cls._normalize_name(raw.get("name"))
        if not name:
            raise ValueError("Informe o nome do preset.")

        description = str(raw.get("description") or "").strip() or None
        permissions = RbacPermissionCatalogService.normalize_payload(raw.get("permissions"))
        flat = RbacPermissionCatalogService.permission_flat_map(permissions)
        if not flat:
            raise ValueError("Selecione ao menos uma permissão antes de salvar o preset.")

        return {
            "name": name[:120],
            "description": description,
            "permissions": permissions,
        }

    @classmethod
    def serialize_preset(cls, preset: CompanyRolePermissionPreset) -> dict[str, Any]:
        payload = preset.to_dict()
        payload["permission_flat"] = RbacPermissionCatalogService.permission_flat_map(
            preset.permissions
        )
        payload["permission_summary"] = RbacPermissionCatalogService.summarize_permissions(
            preset.permissions
        )
        payload["source"] = "company"
        payload["is_system"] = False
        payload["key"] = preset.preset_key
        payload["label"] = preset.name
        payload["grants"] = payload["permission_flat"]
        return payload

    @classmethod
    def list_presets(cls, company_id: int) -> list[dict[str, Any]]:
        presets = (
            CompanyRolePermissionPreset.query.filter_by(company_id=company_id)
            .order_by(CompanyRolePermissionPreset.name.asc(), CompanyRolePermissionPreset.id.asc())
            .all()
        )
        return [cls.serialize_preset(preset) for preset in presets]

    @classmethod
    def get_preset(cls, company_id: int, preset_id: int) -> CompanyRolePermissionPreset | None:
        return CompanyRolePermissionPreset.query.filter_by(
            id=preset_id,
            company_id=company_id,
        ).first()

    @classmethod
    def create_preset(
        cls,
        company_id: int,
        payload: dict[str, Any] | None,
        *,
        created_by_user_id: int | None = None,
    ) -> dict[str, Any]:
        normalized = cls.validate_payload(payload)
        preset = CompanyRolePermissionPreset(
            company_id=company_id,
            preset_key=cls._build_unique_key(company_id, normalized["name"]),
            name=normalized["name"],
            description=normalized["description"],
            permissions=normalized["permissions"],
            created_by_user_id=created_by_user_id,
        )
        db.session.add(preset)
        db.session.commit()
        return cls.serialize_preset(preset)

    @classmethod
    def update_preset(
        cls,
        preset: CompanyRolePermissionPreset,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized = cls.validate_payload(payload)
        preset.name = normalized["name"]
        preset.description = normalized["description"]
        preset.permissions = normalized["permissions"]
        preset.preset_key = cls._build_unique_key(
            preset.company_id,
            normalized["name"],
            ignore_preset_id=preset.id,
        )
        db.session.commit()
        return cls.serialize_preset(preset)

    @classmethod
    def delete_preset(cls, preset: CompanyRolePermissionPreset) -> None:
        db.session.delete(preset)
        db.session.commit()
