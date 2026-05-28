from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import requests

from app32.tests.e2e.config.environments import E2EEnvironmentSettings


@dataclass
class AuthenticatedHTTPSession:
    settings: E2EEnvironmentSettings
    session: requests.Session

    @classmethod
    def create(cls, settings: E2EEnvironmentSettings) -> "AuthenticatedHTTPSession":
        http = requests.Session()
        http.headers.update({"Content-Type": "application/json"})
        instance = cls(settings=settings, session=http)
        instance._load_storage_state_cookie()
        return instance

    def login(self) -> dict[str, Any]:
        if self._has_session_cookie():
            return {"success": True, "redirect": self.settings.post_login_path, "auth_source": "storage_state"}
        response = self.session.post(
            self.settings.login_url,
            json={
                "email": self.settings.username,
                "password": self.settings.password,
                "next": self.settings.post_login_path,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"Falha no login E2E: {payload}")
        return payload

    def select_company(self) -> dict[str, Any] | None:
        if self.settings.company_id is None:
            return None
        response = self.session.post(
            f"{self.settings.base_url.rstrip('/')}/portal",
            json={"company_id": self.settings.company_id},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"Falha ao selecionar empresa E2E: {payload}")
        return payload

    def request(self, method: str, path: str, *, json_payload: dict[str, Any] | None = None) -> requests.Response:
        return self.session.request(
            method=method.upper(),
            url=f"{self.settings.base_url.rstrip('/')}{path}",
            json=json_payload,
            timeout=30,
        )

    def _has_session_cookie(self) -> bool:
        cookie_name = "gv_session"
        return any(cookie.name == cookie_name for cookie in self.session.cookies)

    def _load_storage_state_cookie(self) -> None:
        storage_path = Path(self.settings.storage_state_path)
        if not storage_path.exists():
            return
        try:
            payload = json.loads(storage_path.read_text(encoding="utf-8"))
        except Exception:
            return
        for cookie in payload.get("cookies", []) or []:
            name = str(cookie.get("name") or "").strip()
            value = str(cookie.get("value") or "")
            if not name or not value:
                continue
            domain = str(cookie.get("domain") or "").lstrip(".")
            path = str(cookie.get("path") or "/") or "/"
            self.session.cookies.set(name, value, domain=domain or None, path=path)
