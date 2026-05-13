from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeProfileSpec:
    key: str
    label: str
    default_surface: str
    actor_type: str
    requires_training: bool = True
    supports_personal_token: bool = False


_RUNTIME_PROFILE_ALIASES = {
    "cliente": "squad_cliente",
    "client": "squad_cliente",
    "squad_cliente": "squad_cliente",
    "squad-cliente": "squad_cliente",
    "versus": "squad_versus",
    "squad_versus": "squad_versus",
    "squad-versus": "squad_versus",
    "engineering": "engineering",
    "engenharia": "engineering",
    "squad_engenharia": "engineering",
    "squad-engenharia": "engineering",
}


_RUNTIME_PROFILES = {
    "squad_cliente": RuntimeProfileSpec(
        key="squad_cliente",
        label="Harness Squad Cliente",
        default_surface="user",
        actor_type="human_user",
        requires_training=True,
        supports_personal_token=True,
    ),
    "squad_versus": RuntimeProfileSpec(
        key="squad_versus",
        label="Harness Squad Versus",
        default_surface="admin",
        actor_type="versus_operator",
        requires_training=True,
        supports_personal_token=False,
    ),
    "engineering": RuntimeProfileSpec(
        key="engineering",
        label="Harness Squad de Engenharia",
        default_surface="ops",
        actor_type="engineering_operator",
        requires_training=True,
        supports_personal_token=False,
    ),
}


def normalize_runtime_profile(runtime_profile: str | None) -> str | None:
    normalized = str(runtime_profile or "").strip().lower()
    if not normalized:
        return None
    return _RUNTIME_PROFILE_ALIASES.get(normalized, normalized)


def get_runtime_profile_spec(runtime_profile: str | None) -> RuntimeProfileSpec | None:
    normalized = normalize_runtime_profile(runtime_profile)
    if normalized is None:
        return None
    return _RUNTIME_PROFILES.get(normalized)


__all__ = [
    "RuntimeProfileSpec",
    "get_runtime_profile_spec",
    "normalize_runtime_profile",
]
