from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import requests

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.auth import AuthPage
from app32.tests.e2e.core.browser_session import managed_page
from app32.tests.e2e.core.evidence import EvidenceCollector, create_evidence_paths


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
            if self._session_is_authenticated():
                return {"success": True, "redirect": self.settings.post_login_path, "auth_source": "storage_state"}
            self.session.cookies.clear()
        try:
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
            payload = self._json_or_raise(response, operation="login")
            if not payload.get("success"):
                raise RuntimeError(f"Falha no login E2E: {payload}")
            return payload
        except Exception:
            return self._bootstrap_via_browser_login()

    def select_company(self) -> dict[str, Any] | None:
        if self.settings.company_id is None:
            return None
        response = self.session.post(
            f"{self.settings.base_url.rstrip('/')}/portal",
            json={"company_id": self.settings.company_id},
            timeout=30,
        )
        response.raise_for_status()
        payload = self._json_or_raise(response, operation="select_company")
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

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        response = self.request(method, path, json_payload=json_payload)
        response.raise_for_status()
        self.assert_not_login_redirect(response, operation=operation)
        payload = self._json_or_raise(response, operation=operation)
        if isinstance(payload, dict) and payload.get("success") is False:
            raise RuntimeError(f"Falha funcional em {operation}: {payload}")
        return payload

    def assert_not_login_redirect(self, response: requests.Response, *, operation: str) -> None:
        final_url = str(getattr(response, "url", "") or "")
        if "/login" in final_url:
            raise RuntimeError(
                f"Fluxo autenticado inválido em {operation}: resposta final redirecionou para login ({final_url})."
            )

    def _json_or_raise(self, response: requests.Response, *, operation: str) -> dict[str, Any]:
        try:
            return response.json()
        except Exception as exc:
            content_type = response.headers.get("Content-Type", "")
            text_preview = (response.text or "")[:180].replace("\n", " ").replace("\r", " ")
            raise RuntimeError(
                f"Resposta inválida em {operation}: esperado JSON e recebido "
                f"status={response.status_code} content_type={content_type!r} preview={text_preview!r}"
            ) from exc

    def _has_session_cookie(self) -> bool:
        cookie_name = "gv_session"
        return any(cookie.name == cookie_name for cookie in self.session.cookies)

    def _session_is_authenticated(self) -> bool:
        try:
            response = self.session.get(
                f"{self.settings.base_url.rstrip('/')}/portal",
                timeout=15,
            )
        except Exception:
            return False
        final_url = str(getattr(response, "url", "") or "")
        if "/login" in final_url:
            return False
        body = (response.text or "")[:400].lower()
        if "login | versus" in body:
            return False
        return response.status_code == 200

    def _bootstrap_via_browser_login(self) -> dict[str, Any]:
        evidence = create_evidence_paths(self.settings.outputs_dir / "http_auth_bootstrap")
        collector = EvidenceCollector(evidence)
        with managed_page(self.settings, evidence, collector) as (_, _, _, page):
            auth_page = AuthPage(page, self.settings)
            auth_page.open()
            auth_page.login()
            auth_page.ensure_authenticated_workspace()
        self.session.cookies.clear()
        self._load_storage_state_cookie()
        if not self._has_session_cookie():
            raise RuntimeError("Falha no bootstrap autenticado E2E: storage_state sem gv_session.")
        return {
            "success": True,
            "redirect": self.settings.post_login_path,
            "auth_source": "browser_bootstrap",
        }

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
