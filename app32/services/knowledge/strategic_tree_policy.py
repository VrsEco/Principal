from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategicTreeActor:
    user_id: int
    company_id: int
    profile: str = "collaborator"
    accessible_company_ids: tuple[int, ...] = ()

    @property
    def has_full_access(self) -> bool:
        return self.profile in {"administrator", "admin", "client", "consultant"}


class StrategicTreeAccessPolicy:
    @staticmethod
    def require_tenant(actor: StrategicTreeActor) -> None:
        allowed = set(actor.accessible_company_ids or ())
        if allowed and actor.company_id not in allowed:
            raise PermissionError("Empresa fora do escopo autorizado.")
        if not actor.company_id or not actor.user_id:
            raise PermissionError("Contexto de usuário e empresa é obrigatório.")

    @classmethod
    def require_read(cls, actor: StrategicTreeActor) -> None:
        cls.require_tenant(actor)

    @classmethod
    def require_contribute(cls, actor: StrategicTreeActor) -> None:
        cls.require_tenant(actor)

    @classmethod
    def require_manage(cls, actor: StrategicTreeActor) -> None:
        cls.require_tenant(actor)
        if not actor.has_full_access:
            raise PermissionError("Somente cliente, consultor ou administrador pode organizar a árvore.")

    @staticmethod
    def can_read_contribution(actor: StrategicTreeActor, contribution) -> bool:
        if contribution.company_id != actor.company_id:
            return False
        scope = str(contribution.visibility_scope or "company_authorized")
        if scope == "author_only":
            return contribution.author_user_id == actor.user_id
        if scope in {"consultant", "squad_client", "squad_versus"}:
            return actor.has_full_access or contribution.author_user_id == actor.user_id
        return True

    @classmethod
    def serialize_contribution(cls, actor: StrategicTreeActor, contribution) -> dict | None:
        if not cls.can_read_contribution(actor, contribution):
            return None
        content = contribution.raw_content
        if contribution.attribution_mode in {"confidential", "pseudonymized"} and not actor.has_full_access:
            if contribution.author_user_id != actor.user_id:
                content = contribution.sanitized_content or "Conteúdo confidencial disponível ao consultor autorizado."
        return contribution.to_dict(content=content)
