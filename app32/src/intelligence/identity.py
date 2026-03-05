import logging
import re
from typing import Optional, Set
from urllib.parse import urlparse

from sqlalchemy import func

from models.user import User
from models.employee import Employee

logger = logging.getLogger(__name__)


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


def get_best_company_id(user: User) -> Optional[int]:
    """Retorna a empresa mais relevante para o contexto do usuario."""
    if not user:
        return None

    # 1) Preferencia por vinculo ativo do proprio usuario.
    active_employee = (
        Employee.query.filter_by(user_id=user.id, status="active")
        .order_by(Employee.company_id.asc(), Employee.id.asc())
        .first()
    )
    if active_employee:
        return active_employee.company_id

    # 2) Fallback para qualquer vinculo do usuario, mantendo determinismo.
    employee = (
        Employee.query.filter_by(user_id=user.id)
        .order_by(Employee.company_id.asc(), Employee.id.asc())
        .first()
    )
    if employee:
        return employee.company_id

    # 3) Admin sem vinculo explicito: primeira empresa ativa do tenant.
    if user.role == "admin":
        from models.company import Company

        first_company = Company.query.filter_by(is_active=True).order_by(Company.id.asc()).first()
        if first_company:
            return first_company.id

    return None
