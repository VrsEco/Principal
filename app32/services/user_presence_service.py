from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import MutableMapping

from flask import current_app
from sqlalchemy import delete, or_
from sqlalchemy.exc import IntegrityError

from models import Company, User, UserPresenceSession, db


class UserPresenceService:
    """Registra e consulta presença web sem persistir o cookie de autenticação."""

    SESSION_TOKEN_KEY = "user_presence_token"
    SESSION_COMPANY_KEY = "user_presence_company_id"
    ONLINE_SECONDS = 180
    IDLE_SECONDS = 900
    RETENTION_HOURS = 24

    @classmethod
    def ensure_session_token(cls, session_state: MutableMapping) -> str:
        """Materializa o identificador opaco antes do primeiro heartbeat."""
        token = str(session_state.get(cls.SESSION_TOKEN_KEY) or "").strip()
        if not token:
            token = secrets.token_urlsafe(32)
            session_state[cls.SESSION_TOKEN_KEY] = token
        return token

    @classmethod
    def _digest(cls, value: str) -> str:
        secret = str(current_app.config.get("SECRET_KEY") or "")
        if not secret:
            raise RuntimeError("SECRET_KEY é obrigatória para registrar presença.")
        return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def _ip_digest(cls, ip_address: str | None) -> str | None:
        value = str(ip_address or "").strip()
        return cls._digest(f"ip:{value}") if value else None

    @staticmethod
    def _device_metadata(user_agent: str | None) -> tuple[str, str]:
        value = str(user_agent or "")
        lowered = value.lower()
        if any(token in lowered for token in ("iphone", "android", "mobile")):
            device = "mobile"
        elif any(token in lowered for token in ("ipad", "tablet")):
            device = "tablet"
        else:
            device = "desktop"

        if "edg/" in lowered:
            browser = "Edge"
        elif "chrome/" in lowered and "chromium" not in lowered:
            browser = "Chrome"
        elif "firefox/" in lowered:
            browser = "Firefox"
        elif "safari/" in lowered and "chrome/" not in lowered:
            browser = "Safari"
        else:
            browser = "Outro"
        return device, browser

    @classmethod
    def heartbeat(
        cls,
        *,
        user_id: int,
        company_id: int,
        session_state: MutableMapping,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Cria ou renova a presença da sessão no tenant ativo."""
        user_id = int(user_id)
        company_id = int(company_id)
        now = datetime.utcnow()
        token = str(session_state.get(cls.SESSION_TOKEN_KEY) or "").strip()
        previous_company_id = session_state.get(cls.SESSION_COMPANY_KEY)

        if token and previous_company_id and int(previous_company_id) != company_id:
            cls._close_by_token(
                user_id=user_id,
                company_id=int(previous_company_id),
                token=token,
                closed_at=now,
            )
            token = ""

        if not token:
            token = cls.ensure_session_token(session_state)

        session_state[cls.SESSION_COMPANY_KEY] = company_id
        session_hash = cls._digest(token)
        presence = (
            UserPresenceSession.query
            .filter_by(
                company_id=company_id,
                user_id=user_id,
                session_hash=session_hash,
                logout_at=None,
                revoked_at=None,
            )
            .first()
        )
        device_type, browser = cls._device_metadata(user_agent)

        if presence is None:
            presence = UserPresenceSession(
                company_id=company_id,
                user_id=user_id,
                session_hash=session_hash,
                login_at=now,
                last_seen_at=now,
                expires_at=now + timedelta(seconds=cls.IDLE_SECONDS),
                device_type=device_type,
                browser=browser,
                ip_hash=cls._ip_digest(ip_address),
            )
            db.session.add(presence)
        else:
            presence.last_seen_at = now
            presence.expires_at = now + timedelta(seconds=cls.IDLE_SECONDS)
            presence.device_type = device_type
            presence.browser = browser
            presence.updated_at = now

        try:
            db.session.commit()
        except IntegrityError:
            # Duas abas podem publicar o primeiro heartbeat simultaneamente.
            # A constraint tenant-safe arbitra a corrida; a segunda requisição
            # reaproveita a linha vencedora em vez de falhar para o usuário.
            db.session.rollback()
            presence = (
                UserPresenceSession.query
                .filter_by(
                    company_id=company_id,
                    user_id=user_id,
                    session_hash=session_hash,
                    logout_at=None,
                    revoked_at=None,
                )
                .first()
            )
            if presence is None:
                raise
            presence.last_seen_at = now
            presence.expires_at = now + timedelta(seconds=cls.IDLE_SECONDS)
            presence.device_type = device_type
            presence.browser = browser
            presence.updated_at = now
            db.session.commit()
        return {
            "status": "online",
            "company_id": company_id,
            "last_seen_at": cls._iso_utc(now),
            "expires_at": cls._iso_utc(presence.expires_at),
        }

    @classmethod
    def close_current(
        cls,
        *,
        user_id: int,
        session_state: MutableMapping,
    ) -> bool:
        token = str(session_state.get(cls.SESSION_TOKEN_KEY) or "").strip()
        company_id = session_state.get(cls.SESSION_COMPANY_KEY)
        try:
            if not token or not company_id:
                return False
            return cls._close_by_token(
                user_id=int(user_id),
                company_id=int(company_id),
                token=token,
                closed_at=datetime.utcnow(),
            )
        finally:
            session_state.pop(cls.SESSION_TOKEN_KEY, None)
            session_state.pop(cls.SESSION_COMPANY_KEY, None)

    @classmethod
    def _close_by_token(
        cls,
        *,
        user_id: int,
        company_id: int,
        token: str,
        closed_at: datetime,
    ) -> bool:
        presence = (
            UserPresenceSession.query
            .filter_by(
                company_id=company_id,
                user_id=user_id,
                session_hash=cls._digest(token),
                logout_at=None,
                revoked_at=None,
            )
            .first()
        )
        if presence is None:
            return False
        presence.logout_at = closed_at
        presence.expires_at = closed_at
        presence.updated_at = closed_at
        db.session.commit()
        return True

    @classmethod
    def list_company_presence(
        cls,
        *,
        company_id: int,
        status: str | None = None,
        search: str | None = None,
        limit: int = 200,
    ) -> dict:
        """Consulta estritamente uma empresa; escopo global não é aceito."""
        company_id = int(company_id)
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=cls.RETENTION_HOURS)
        cls.purge_expired(company_id=company_id, cutoff=cutoff)
        query = (
            db.session.query(UserPresenceSession, User, Company)
            .join(User, User.id == UserPresenceSession.user_id)
            .join(Company, Company.id == UserPresenceSession.company_id)
            .filter(
                UserPresenceSession.company_id == company_id,
                UserPresenceSession.last_seen_at >= cutoff,
            )
        )
        normalized_search = str(search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            query = query.filter(or_(User.name.ilike(pattern), User.email.ilike(pattern)))

        records = query.order_by(UserPresenceSession.last_seen_at.desc()).limit(max(1, min(limit, 500))).all()
        all_items = [cls._serialize(item, user, company, now) for item, user, company in records]

        normalized_status = str(status or "").strip().lower()
        items = (
            [item for item in all_items if item["status"] == normalized_status]
            if normalized_status in {"online", "idle", "offline", "revoked"}
            else all_items
        )

        priority = {"online": 4, "idle": 3, "offline": 2, "revoked": 1}
        user_status: dict[int, str] = {}
        for item in all_items:
            user_id = int(item["user_id"])
            current = user_status.get(user_id)
            if current is None or priority[item["status"]] > priority[current]:
                user_status[user_id] = item["status"]

        return {
            "company_id": company_id,
            "generated_at": cls._iso_utc(now),
            "thresholds": {
                "online_seconds": cls.ONLINE_SECONDS,
                "idle_seconds": cls.IDLE_SECONDS,
            },
            "summary": {
                "online": sum(value == "online" for value in user_status.values()),
                "idle": sum(value == "idle" for value in user_status.values()),
                "offline": sum(value == "offline" for value in user_status.values()),
                "revoked": sum(value == "revoked" for value in user_status.values()),
                "sessions": len(all_items),
            },
            "items": items,
        }

    @classmethod
    def purge_expired(cls, *, company_id: int, cutoff: datetime | None = None) -> int:
        """Remove presença transitória expirada sem atravessar o tenant."""
        company_id = int(company_id)
        cutoff = cutoff or (datetime.utcnow() - timedelta(hours=cls.RETENTION_HOURS))
        result = db.session.execute(
            delete(UserPresenceSession).where(
                UserPresenceSession.company_id == company_id,
                UserPresenceSession.last_seen_at < cutoff,
            )
        )
        db.session.commit()
        return int(result.rowcount or 0)

    @classmethod
    def _serialize(cls, presence, user, company, now: datetime) -> dict:
        return {
            "id": presence.id,
            "company_id": presence.company_id,
            "company_name": company.name,
            "user_id": presence.user_id,
            "user_name": user.name,
            "user_email": user.email,
            "status": cls._status_for(presence, now),
            "device_type": presence.device_type or "desktop",
            "browser": presence.browser or "Outro",
            "login_at": cls._iso_utc(presence.login_at),
            "last_seen_at": cls._iso_utc(presence.last_seen_at),
            "expires_at": cls._iso_utc(presence.expires_at),
            "logout_at": cls._iso_utc(presence.logout_at),
        }

    @classmethod
    def _status_for(cls, presence, now: datetime) -> str:
        if presence.revoked_at is not None:
            return "revoked"
        if presence.logout_at is not None or presence.expires_at <= now:
            return "offline"
        elapsed = max(0, int((now - presence.last_seen_at).total_seconds()))
        if elapsed <= cls.ONLINE_SECONDS:
            return "online"
        if elapsed <= cls.IDLE_SECONDS:
            return "idle"
        return "offline"

    @staticmethod
    def _iso_utc(value: datetime | None) -> str | None:
        return f"{value.isoformat()}Z" if value else None
