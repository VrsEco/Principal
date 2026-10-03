"""Sincronização app -> Google Calendar (OAuth por usuário, vale em todas as empresas; só requests).

Tokens ficam criptografados (Fernet). Cada registro do app vira um evento no Google,
com link de volta para a página de gestão.  A sincronização é idempotente: um hash do
conteúdo evita chamadas desnecessárias e vínculos órfãos são removidos do Google.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import requests
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

from models import GoogleCalendarConnection, GoogleCalendarEventLink, db
from services.unified_calendar_service import list_unified_events

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
SCOPES = "https://www.googleapis.com/auth/calendar.events openid email"
HTTP_TIMEOUT = 15
MAX_OPERATIONS = 300
REVALIDATE_MINUTES = 5
MAX_GOOGLE_EVENTS = 250
MAX_ALL_DAY_SPAN = 31
STATE_MAX_AGE_SECONDS = 600
TYPE_PREFIX = {"meeting": "Reunião", "project_task": "Atividade", "process_instance": "Instância"}


class GoogleCalendarError(Exception):
    """Erro de negócio exibível ao usuário."""


def is_configured() -> bool:
    return all(os.environ.get(k) for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
                                           "GOOGLE_OAUTH_REDIRECT_URI", "GOOGLE_CALENDAR_TOKEN_KEY"))


def _require_configured() -> None:
    if not is_configured():
        raise GoogleCalendarError("Integração com o Google Calendar não configurada neste ambiente.")


def _fernet() -> Fernet:
    try:
        return Fernet(os.environ["GOOGLE_CALENDAR_TOKEN_KEY"].encode())
    except (KeyError, ValueError) as exc:
        raise GoogleCalendarError("Chave de criptografia do Google Calendar inválida.") from exc


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise GoogleCalendarError("Não foi possível ler as credenciais salvas. Reconecte o Google.") from exc


# ------------------------------------------------------------------ OAuth
def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="gcal-oauth-state")


def build_auth_url(user_id: int, nonce: str) -> str:
    _require_configured()
    state = _state_serializer().dumps({"u": user_id, "n": nonce})
    params = {
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "redirect_uri": os.environ["GOOGLE_OAUTH_REDIRECT_URI"],
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def parse_state(state: str) -> dict[str, Any]:
    try:
        data = _state_serializer().loads(state, max_age=STATE_MAX_AGE_SECONDS)
    except BadData as exc:
        raise GoogleCalendarError("Autorização expirada ou inválida. Tente conectar novamente.") from exc
    if not isinstance(data, dict) or not {"u", "n"} <= set(data):
        raise GoogleCalendarError("Autorização inválida.")
    return data


def complete_connection(user_id: int, code: str) -> GoogleCalendarConnection:
    _require_configured()
    token = _token_request({
        "code": code,
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "redirect_uri": os.environ["GOOGLE_OAUTH_REDIRECT_URI"],
        "grant_type": "authorization_code",
    })
    scope = token.get("scope") or ""
    if "calendar.events" not in scope:
        raise GoogleCalendarError("Permissão de calendário não concedida no Google.")
    conn = GoogleCalendarConnection.query.filter_by(user_id=user_id).first()
    refresh = token.get("refresh_token")
    if not refresh and not conn:
        raise GoogleCalendarError("O Google não devolveu autorização offline. Remova o acesso e conecte novamente.")
    if not conn:
        conn = GoogleCalendarConnection(user_id=user_id, refresh_token_enc="")
        db.session.add(conn)
    if refresh:
        conn.refresh_token_enc = _encrypt(refresh)
    _store_access_token(conn, token)
    conn.scope = scope
    conn.status = "active"
    conn.last_error = None
    conn.google_email = _fetch_email(token["access_token"])
    db.session.commit()
    return conn


def _token_request(data: dict[str, str]) -> dict[str, Any]:
    try:
        resp = requests.post(TOKEN_URL, data=data, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise GoogleCalendarError("Falha de comunicação com o Google.") from exc
    body = _json(resp)
    if resp.status_code != 200 or "access_token" not in body:
        code = str(body.get("error") or f"http_{resp.status_code}")[:60]
        logger.warning("Google OAuth recusou a requisição de token: %s", code)  # nunca registrar o corpo/segredos
        if code == "invalid_grant":
            raise _InvalidGrant()
        raise GoogleCalendarError(f"O Google recusou a autorização ({code}).")
    return body


class _InvalidGrant(GoogleCalendarError):
    def __init__(self) -> None:
        super().__init__("Acesso ao Google revogado ou expirado. Reconecte a conta.")


def _fetch_email(access_token: str) -> str | None:
    try:
        resp = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=HTTP_TIMEOUT)
        return _json(resp).get("email") if resp.status_code == 200 else None
    except requests.RequestException:
        return None


def _store_access_token(conn: GoogleCalendarConnection, token: dict[str, Any]) -> None:
    conn.access_token_enc = _encrypt(token["access_token"])
    conn.token_expires_at = datetime.utcnow() + timedelta(seconds=int(token.get("expires_in") or 3600))


def _access_token(conn: GoogleCalendarConnection, *, force_refresh: bool = False) -> str:
    if (
        not force_refresh
        and conn.access_token_enc
        and conn.token_expires_at
        and conn.token_expires_at > datetime.utcnow() + timedelta(seconds=60)
    ):
        return _decrypt(conn.access_token_enc)
    try:
        token = _token_request({
            "refresh_token": _decrypt(conn.refresh_token_enc),
            "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
            "grant_type": "refresh_token",
        })
    except _InvalidGrant:
        conn.status = "revoked"
        conn.last_error = "Acesso revogado no Google."
        db.session.commit()
        raise
    _store_access_token(conn, token)
    db.session.commit()
    return token["access_token"]


def _json(resp: requests.Response) -> dict[str, Any]:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


# ------------------------------------------------------------------ conexão
def get_connection(user_id: int) -> GoogleCalendarConnection | None:
    return GoogleCalendarConnection.query.filter_by(user_id=user_id).first()


def check_connection(user_id: int) -> dict[str, Any]:
    """Status da conexão validando o token quando vencido, para avisar o usuário antes da próxima sincronização."""
    conn = get_connection(user_id)
    if conn and is_configured() and conn.status != "revoked":
        # Revalida no Google a cada ~5 min (não só quando o token vence), para o aviso aparecer logo após uma revogação.
        stale = not conn.updated_at or conn.updated_at < datetime.utcnow() - timedelta(minutes=REVALIDATE_MINUTES)
        try:
            _access_token(conn, force_refresh=stale)  # invalid_grant marca a conexão como revogada
        except GoogleCalendarError:
            pass  # falha de rede não invalida a conexão; revogação já foi registrada
    return connection_status(user_id)


def connection_status(user_id: int) -> dict[str, Any]:
    conn = get_connection(user_id)
    return {
        "configured": is_configured(),
        "connected": bool(conn and conn.status == "active"),
        "needs_reconnect": bool(conn and conn.status == "revoked"),
        "status": conn.status if conn else None,
        "email": conn.google_email if conn else None,
        "last_synced_at": conn.last_synced_at.isoformat() if conn and conn.last_synced_at else None,
        "last_error": conn.last_error if conn else None,
    }


def disconnect(user_id: int) -> bool:
    conn = get_connection(user_id)
    if not conn:
        return False
    try:  # revogar é melhor esforço; os dados locais são removidos de qualquer forma
        requests.post(REVOKE_URL, data={"token": _decrypt(conn.refresh_token_enc)}, timeout=HTTP_TIMEOUT)
    except (requests.RequestException, GoogleCalendarError):
        logger.info("Revogação no Google não confirmada para conexão %s", conn.id)
    GoogleCalendarEventLink.query.filter_by(connection_id=conn.id).delete()
    db.session.delete(conn)
    db.session.commit()
    return True


# ------------------------------------------------------------------ sincronização
def sync_range(user_id: int, targets: list[tuple[int, int]], start: date, end: date) -> dict[str, Any]:
    """Envia ao Google os compromissos do usuário nas empresas indicadas.

    ``targets`` é uma lista de ``(company_id, employee_id)``; uma empresa = sincronização da empresa,
    várias = sincronização global. Cada empresa só remove do Google os eventos que ela mesma enviou.
    """
    _require_configured()
    conn = get_connection(user_id)
    if not conn or conn.status == "revoked":
        raise GoogleCalendarError("Conecte sua conta Google antes de sincronizar.")

    totals = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0, "failed": 0}
    by_company: list[dict[str, Any]] = []
    session = _GoogleSession(conn)
    budget = [MAX_OPERATIONS]
    try:
        for company_id, employee_id in targets:
            stats = _sync_company(session, conn, company_id, employee_id, start, end, budget)
            by_company.append({"company_id": company_id, **stats})
            for key, value in stats.items():
                totals[key] += value
        conn.last_synced_at = datetime.utcnow()
        conn.status = "active"
        conn.last_error = None
    except GoogleCalendarError as exc:
        conn.status = "error" if conn.status != "revoked" else "revoked"
        conn.last_error = str(exc)[:500]
        db.session.commit()
        raise
    db.session.commit()
    return {**totals, "companies": by_company}


def _sync_company(session, conn, company_id: int, employee_id: int, start: date, end: date,
                  budget: list[int]) -> dict[str, int]:
    events = list_unified_events(company_id, start, end, employee_id=employee_id)
    links = {
        (l.source_type, l.source_id): l
        for l in GoogleCalendarEventLink.query.filter(
            GoogleCalendarEventLink.connection_id == conn.id,
            GoogleCalendarEventLink.company_id == company_id,
            GoogleCalendarEventLink.event_date.between(start, end),
        )
    }
    stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0, "failed": 0}
    seen: set[tuple[str, int]] = set()
    for event in events:
        key = (event["type"], event["id"])
        seen.add(key)
        body = _event_body(company_id, event)
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        link = links.get(key)
        if link and link.content_hash == digest:
            stats["unchanged"] += 1
            continue
        if budget[0] <= 0:
            stats["failed"] += 1
            continue
        budget[0] -= 1
        stats[_upsert_event(session, conn, company_id, event, body, digest, link)] += 1

    for key, link in links.items():
        if key in seen or budget[0] <= 0:
            continue
        budget[0] -= 1
        if session.delete(link.google_event_id):
            db.session.delete(link)
            stats["deleted"] += 1
        else:
            stats["failed"] += 1
    return stats


def _upsert_event(session, conn, company_id, event, body, digest, link) -> str:
    if link:
        status = session.patch(link.google_event_id, body)
        if status == 200:
            link.content_hash, link.event_date, link.last_synced_at = digest, date.fromisoformat(event["date"]), datetime.utcnow()
            return "updated"
        if status not in (404, 410):
            return "failed"
        db.session.delete(link)  # evento removido manualmente no Google: recria
        db.session.flush()
    created = session.insert(body)
    if not created:
        return "failed"
    db.session.add(GoogleCalendarEventLink(
        company_id=company_id, connection_id=conn.id, source_type=event["type"], source_id=event["id"],
        google_event_id=created["id"], event_date=date.fromisoformat(event["date"]), content_hash=digest,
    ))
    return "created"


def _event_body(company_id: int, event: dict[str, Any]) -> dict[str, Any]:
    tz = os.environ.get("GOOGLE_CALENDAR_TIMEZONE", "America/Sao_Paulo")
    day = date.fromisoformat(event["date"])
    prefix = "✔ " if event.get("closed") else ""
    body: dict[str, Any] = {
        "summary": f"{prefix}[{TYPE_PREFIX[event['type']]}] {event['title']}"[:1000],
        "extendedProperties": {"private": {"versus_source": f"{event['type']}:{event['id']}", "versus_company": str(company_id)}},
    }
    base = os.environ.get("APP_PUBLIC_BASE_URL", "").rstrip("/")
    lines = [part for part in (event.get("subtitle"), f"Status: {event.get('status')}" if event.get("status") else None) if part]
    if base and event.get("url"):
        lines.append(f"Abrir no Versus: {base}{event['url']}")
    body["description"] = "\n".join(lines)
    time_str = event.get("time")
    if time_str and not event.get("all_day"):
        try:
            hour, minute = (int(x) for x in time_str.split(":")[:2])
        except ValueError:
            hour = minute = None
    else:
        hour = minute = None
    if hour is None:
        body["start"] = {"date": day.isoformat()}
        body["end"] = {"date": (day + timedelta(days=1)).isoformat()}
    else:
        start_dt = datetime(day.year, day.month, day.day, hour, minute)
        end_dt = start_dt + timedelta(minutes=int(event.get("duration_minutes") or 60))
        body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": tz}
        body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz}
    return body


class _GoogleSession:
    """Chamadas à API de eventos com renovação automática do access token em 401."""

    def __init__(self, conn: GoogleCalendarConnection) -> None:
        self.conn = conn
        self.token = _access_token(conn)
        self.url = EVENTS_URL.format(calendar_id=requests.utils.quote(conn.calendar_id or "primary", safe=""))

    def _call(self, method: str, url: str, **kwargs) -> requests.Response:
        for attempt in (0, 1):
            try:
                resp = requests.request(method, url, headers={"Authorization": f"Bearer {self.token}"},
                                        timeout=HTTP_TIMEOUT, **kwargs)
            except requests.RequestException as exc:
                raise GoogleCalendarError("Falha de comunicação com o Google.") from exc
            if resp.status_code == 401 and attempt == 0:
                self.token = _access_token(self.conn, force_refresh=True)
                continue
            if resp.status_code == 403 and "rateLimit" in resp.text:
                raise GoogleCalendarError("Limite de requisições do Google atingido. Tente novamente em instantes.")
            return resp
        return resp

    def list_events(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        resp = self._call("GET", self.url, params=params)
        if resp.status_code != 200:
            raise GoogleCalendarError("Não foi possível ler os compromissos do Google.")
        items = _json(resp).get("items")
        return items if isinstance(items, list) else []

    @staticmethod
    def _log_failure(op: str, resp: requests.Response) -> None:
        error = _json(resp).get("error")
        reason = (error.get("message") if isinstance(error, dict) else error) or ""
        logger.warning("Google Calendar %s falhou: HTTP %s %s", op, resp.status_code, str(reason)[:200])

    def insert(self, body: dict[str, Any]) -> dict[str, Any] | None:
        resp = self._call("POST", self.url, json=body)
        if resp.status_code in (200, 201) and _json(resp).get("id"):
            return _json(resp)
        self._log_failure("insert", resp)
        return None

    def patch(self, event_id: str, body: dict[str, Any]) -> int:
        resp = self._call("PATCH", f"{self.url}/{requests.utils.quote(event_id, safe='')}", json=body)
        if resp.status_code not in (200, 404, 410):
            self._log_failure("patch", resp)
        return resp.status_code

    def delete(self, event_id: str) -> bool:
        resp = self._call("DELETE", f"{self.url}/{requests.utils.quote(event_id, safe='')}")
        if resp.status_code not in (200, 204, 404, 410):
            self._log_failure("delete", resp)
        return resp.status_code in (200, 204, 404, 410)


# ------------------------------------------------------------------ leitura Google -> app
def _tzinfo():
    name = os.environ.get("GOOGLE_CALENDAR_TIMEZONE", "America/Sao_Paulo")
    try:
        return ZoneInfo(name) if ZoneInfo else timezone.utc
    except Exception:  # tzdata ausente
        return timezone.utc


def list_google_events(user_id: int, start: date, end: date) -> list[dict[str, Any]]:
    """Compromissos do Google no período, somente leitura. Ignora os que o próprio Versus enviou."""
    _require_configured()
    conn = get_connection(user_id)
    if not conn or conn.status != "active":
        return []
    tz = _tzinfo()
    session = _GoogleSession(conn)
    items = session.list_events({
        "timeMin": datetime(start.year, start.month, start.day, tzinfo=tz).isoformat(),
        "timeMax": datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=tz).isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": MAX_GOOGLE_EVENTS,
    })
    events: list[dict[str, Any]] = []
    for item in items:
        private = (item.get("extendedProperties") or {}).get("private") or {}
        if item.get("status") == "cancelled" or private.get("versus_source"):
            continue
        events.extend(_normalize_google_event(item, tz, start, end))
    return events


def _normalize_google_event(item: dict[str, Any], tz, start: date, end: date) -> list[dict[str, Any]]:
    raw_start, raw_end = item.get("start") or {}, item.get("end") or {}
    base = {
        "type": "google_event",
        "id": item.get("id"),
        "title": item.get("summary") or "(sem título)",
        "status": item.get("status") or "confirmed",
        "closed": False,
        "priority": None,
        "subtitle": "Google Calendar",
        "url": item.get("htmlLink"),
        "external": True,
    }
    out: list[dict[str, Any]] = []
    if raw_start.get("date"):
        first = date.fromisoformat(raw_start["date"])
        last = date.fromisoformat(raw_end["date"]) - timedelta(days=1) if raw_end.get("date") else first
        day, count = max(first, start), 0
        while day <= min(last, end) and count < MAX_ALL_DAY_SPAN:
            out.append({**base, "key": f"google_event:{item.get('id')}:{day.isoformat()}", "date": day.isoformat(),
                        "time": None, "all_day": True, "duration_minutes": None})
            day += timedelta(days=1)
            count += 1
        return out
    try:
        begin = datetime.fromisoformat(raw_start["dateTime"]).astimezone(tz)
        finish = datetime.fromisoformat(raw_end["dateTime"]).astimezone(tz) if raw_end.get("dateTime") else None
    except (KeyError, ValueError):
        return []
    if not (start <= begin.date() <= end):
        return []
    minutes = int((finish - begin).total_seconds() // 60) if finish and finish > begin else None
    return [{**base, "key": f"google_event:{item.get('id')}", "date": begin.date().isoformat(),
             "time": begin.strftime("%H:%M"), "all_day": False, "duration_minutes": minutes}]
