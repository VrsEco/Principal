import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set, Tuple
from urllib.parse import urlparse

from sqlalchemy import func

from models.user import User
from models.employee import Employee

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IdentityResolutionTrace:
    """Rastro seguro da identificação de usuário por canal.

    Mantém apenas dados operacionais necessários para auditoria e troubleshooting,
    sem carregar o objeto User nem executar decisão de empresa/tenant.
    """

    channel: str
    raw_identifier: str
    normalized_identifier: str
    supported_channel: bool
    strategy: str
    variants: Tuple[str, ...] = field(default_factory=tuple)
    user_id: Optional[int] = None
    matched: bool = False
    reason: str = "not_resolved"

    def to_safe_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "normalized_identifier": self.normalized_identifier,
            "supported_channel": self.supported_channel,
            "strategy": self.strategy,
            "variants_count": len(self.variants),
            "user_id": self.user_id,
            "matched": self.matched,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CompanyResolutionTrace:
    """Rastro da resolução tenant-safe de empresa a partir do usuário vinculado."""

    user_id: Optional[int]
    user_role: str
    selected_company_id: Optional[int]
    selected_employee_id: Optional[int]
    source: str
    candidate_count: int = 0
    reason: str = "not_resolved"

    def to_safe_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_role": self.user_role,
            "selected_company_id": self.selected_company_id,
            "selected_employee_id": self.selected_employee_id,
            "source": self.source,
            "candidate_count": self.candidate_count,
            "reason": self.reason,
        }


def _normalize_text(value: str) -> str:
    return (value or "").strip()


def _normalize_email(value: str) -> str:
    return _normalize_text(value).lower()


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _build_phone_variants(value: str) -> Set[str]:
    raw = _normalize_text(value)
    digits = _digits_only(raw)
    variants: Set[str] = set()

    if raw:
        variants.add(raw)
    if not digits:
        return variants

    variants.add(digits)

    # Normaliza com e sem DDI 55 (Brasil)
    local = digits[2:] if digits.startswith("55") and len(digits) > 11 else digits
    variants.add(local)
    variants.add(f"55{local}")

    # Compatibilidade 10/11 digitos (com ou sem nono digito)
    if len(local) == 10:
        local_with_nine = f"{local[:2]}9{local[2:]}"
        variants.add(local_with_nine)
        variants.add(f"55{local_with_nine}")
    elif len(local) == 11 and local[2] == "9":
        local_without_nine = f"{local[:2]}{local[3:]}"
        variants.add(local_without_nine)
        variants.add(f"55{local_without_nine}")

    for candidate in list(variants):
        if candidate and candidate[0].isdigit():
            variants.add(f"+{candidate}")

    return {v for v in variants if v}


def _build_instagram_variants(value: str) -> Set[str]:
    raw = _normalize_text(value).lower()
    variants: Set[str] = set()
    if not raw:
        return variants

    variants.add(raw)

    if raw.startswith("http://") or raw.startswith("https://"):
        try:
            parsed = urlparse(raw)
            path = (parsed.path or "").strip("/")
            if path:
                handle = path.split("/")[0].strip().lower()
                if handle:
                    variants.add(handle)
                    variants.add(f"@{handle}")
        except Exception:
            pass

    if raw.startswith("@"):
        variants.add(raw[1:])
    else:
        variants.add(f"@{raw}")

    return {v for v in variants if v}


def _find_user_by_whatsapp(identifier: str) -> Optional[User]:
    variants = _build_phone_variants(identifier)
    if not variants:
        return None

    user = (
        User.query.filter(
            User.is_active.is_(True),
            User.whatsapp.in_(list(variants)),
        )
        .order_by(User.id.asc())
        .first()
    )
    if user:
        return user

    digits_variants = {_digits_only(v) for v in variants if _digits_only(v)}
    if not digits_variants:
        return None

    # Fallback DB-side para formatos mascarados (ex: +55 (71) 99999-0000)
    try:
        user = (
            User.query.filter(User.is_active.is_(True), User.whatsapp.isnot(None))
            .filter(func.regexp_replace(User.whatsapp, r"\D", "", "g").in_(list(digits_variants)))
            .order_by(User.id.asc())
            .first()
        )
        if user:
            return user
    except Exception as err:
        logger.debug("regexp_replace indisponivel para User.whatsapp: %s", err)

    # Fallback em Python (quando DB nao suporta regexp_replace)
    candidates = (
        User.query.filter(User.is_active.is_(True), User.whatsapp.isnot(None))
        .order_by(User.id.asc())
        .all()
    )
    for candidate in candidates:
        if _digits_only(candidate.whatsapp) in digits_variants:
            return candidate
    return None


def _find_user_by_instagram(identifier: str) -> Optional[User]:
    variants = _build_instagram_variants(identifier)
    if not variants:
        return None

    return (
        User.query.filter(
            User.is_active.is_(True),
            User.instagram.isnot(None),
            func.lower(func.trim(User.instagram)).in_(list(variants)),
        )
        .order_by(User.id.asc())
        .first()
    )



def _identity_variants_for_channel(identifier: str, channel: str) -> Set[str]:
    channel = _normalize_text(channel).lower()
    if channel == "whatsapp":
        return _build_phone_variants(identifier)
    if channel == "instagram":
        return _build_instagram_variants(identifier)
    if channel == "email":
        normalized = _normalize_email(identifier)
        return {normalized} if normalized else set()
    if channel == "telegram":
        normalized = _normalize_text(identifier)
        return {normalized} if normalized else set()
    return set()


def build_identity_resolution_trace(identifier: str, channel: str, user: Optional[User] = None) -> IdentityResolutionTrace:
    """Monta rastro de resolução de identidade sem realizar consulta adicional.

    Deve ser usado por webhooks/canais para registrar o caminho de identificação:
    canal recebido, identificador normalizado, estratégia aplicada e usuário final.
    """

    normalized_channel = _normalize_text(channel).lower()
    normalized_identifier = _normalize_text(identifier)
    supported = normalized_channel in {"telegram", "whatsapp", "email", "instagram"}
    variants = tuple(sorted(_identity_variants_for_channel(normalized_identifier, normalized_channel)))
    strategy = f"{normalized_channel}_identity_lookup" if supported else "unsupported_channel"
    matched = bool(user)
    reason = "matched_active_user" if matched else ("empty_identifier" if not normalized_identifier else "not_found")
    if not supported:
        reason = "unsupported_channel"

    return IdentityResolutionTrace(
        channel=normalized_channel,
        raw_identifier=identifier or "",
        normalized_identifier=normalized_identifier,
        supported_channel=supported,
        strategy=strategy,
        variants=variants,
        user_id=getattr(user, "id", None),
        matched=matched,
        reason=reason,
    )


def resolve_user_identity_with_trace(identifier: str, channel: str) -> Tuple[Optional[User], IdentityResolutionTrace]:
    """Resolve usuário e retorna também o rastro seguro da identificação."""

    user = resolve_user_identity(identifier, channel)
    return user, build_identity_resolution_trace(identifier, channel, user=user)


def resolve_user_identity(identifier: str, channel: str) -> Optional[User]:
    """
    Resolve a identidade de um usuario baseado em um identificador de canal.
    Canais suportados: telegram, whatsapp, email, instagram.
    Politica de seguranca: somente usuarios ativos cadastrados em `users`.
    """
    if not identifier:
        return None

    channel = _normalize_text(channel).lower()
    identifier = _normalize_text(identifier)
    if not identifier:
        return None

    if channel == "telegram":
        return (
            User.query.filter(
                User.is_active.is_(True),
                func.trim(User.telegram) == identifier,
            )
            .order_by(User.id.asc())
            .first()
        )

    if channel == "whatsapp":
        return _find_user_by_whatsapp(identifier)

    if channel == "email":
        normalized_email = _normalize_email(identifier)
        return (
            User.query.filter(
                User.is_active.is_(True),
                func.lower(User.email) == normalized_email,
            )
            .order_by(User.id.asc())
            .first()
        )

    if channel == "instagram":
        return _find_user_by_instagram(identifier)

    logger.warning("Canal de identidade nao suportado: %s", channel)
    return None


def get_company_resolution_with_trace(user: User) -> Tuple[Optional[int], CompanyResolutionTrace]:
    """Resolve empresa vinculada ao usuário sem fallback global cross-tenant.

    A seleção é determinística e limitada aos vínculos do próprio usuário em
    `Employee`. Admin sem vínculo explícito não recebe empresa por aproximação.
    """

    if not user:
        trace = CompanyResolutionTrace(
            user_id=None,
            user_role="",
            selected_company_id=None,
            selected_employee_id=None,
            source="no_user",
            reason="user_not_resolved",
        )
        return None, trace

    user_id = getattr(user, "id", None)
    user_role = getattr(user, "role", "") or ""

    active_employees = (
        Employee.query.filter_by(user_id=user_id, status="active")
        .order_by(Employee.company_id.asc(), Employee.id.asc())
        .all()
    )
    if active_employees:
        selected = active_employees[0]
        trace = CompanyResolutionTrace(
            user_id=user_id,
            user_role=user_role,
            selected_company_id=selected.company_id,
            selected_employee_id=selected.id,
            source="active_employee_link",
            candidate_count=len(active_employees),
            reason="matched_active_employee",
        )
        return selected.company_id, trace

    employees = (
        Employee.query.filter_by(user_id=user_id)
        .order_by(Employee.company_id.asc(), Employee.id.asc())
        .all()
    )
    if employees:
        selected = employees[0]
        trace = CompanyResolutionTrace(
            user_id=user_id,
            user_role=user_role,
            selected_company_id=selected.company_id,
            selected_employee_id=selected.id,
            source="employee_link",
            candidate_count=len(employees),
            reason="matched_any_employee",
        )
        return selected.company_id, trace

    trace = CompanyResolutionTrace(
        user_id=user_id,
        user_role=user_role,
        selected_company_id=None,
        selected_employee_id=None,
        source="no_employee_link",
        candidate_count=0,
        reason="admin_without_employee_link" if user_role == "admin" else "user_without_employee_link",
    )
    return None, trace


def get_best_company_id(user: User) -> Optional[int]:
    """Retorna a empresa mais relevante para o contexto do usuario."""

    company_id, trace = get_company_resolution_with_trace(user)
    logger.info("SAPIENS COMPANY RESOLUTION TRACE: %s", trace.to_safe_dict())
    return company_id
