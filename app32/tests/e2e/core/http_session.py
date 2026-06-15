from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode
from app32.tests.e2e.core.auth import AuthPage
from app32.tests.e2e.core.browser_session import managed_page
from app32.tests.e2e.core.evidence import EvidenceCollector, create_evidence_paths
from app32.tests.e2e.core.prod_safe_session_bootstrap import bootstrap_remote_prod_safe_storage_state


@dataclass
class AuthenticatedHTTPSession:
    settings: E2EEnvironmentSettings
    session: requests.Session
    local_client: Any | None = None

    @classmethod
    def create(cls, settings: E2EEnvironmentSettings) -> "AuthenticatedHTTPSession":
        http = requests.Session()
        http.headers.update({"Content-Type": "application/json"})
        instance = cls(settings=settings, session=http)
        instance._load_storage_state_cookie()
        return instance

    def login(self) -> dict[str, Any]:
        if self.settings.execution_mode is E2EExecutionMode.PROD_SAFE:
            return self._bootstrap_via_remote_internal_session()
        if self.settings.user_id is not None:
            return self._bootstrap_via_remote_internal_session()

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
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = self._json_or_raise(response, operation="login")
            if not payload.get("success"):
                raise RuntimeError(f"Falha no login E2E: {payload}")
            return payload
        except Exception:
            try:
                return self._bootstrap_via_remote_internal_session()
            except Exception:
                return self._bootstrap_via_browser_login()

    def select_company(self) -> dict[str, Any] | None:
        if self.settings.company_id is None:
            return None
        if self._has_session_cookie() and (
            self.settings.execution_mode is E2EExecutionMode.PROD_SAFE
            or self.settings.user_id is not None
        ):
            return {"success": True, "redirect": self.settings.post_login_path, "auth_source": "remote_internal_bootstrap"}
        response = self.session.post(
            f"{self.settings.base_url.rstrip('/')}/portal",
            json={"company_id": self.settings.company_id},
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = self._json_or_raise(response, operation="select_company")
        if not payload.get("success"):
            raise RuntimeError(f"Falha ao selecionar empresa E2E: {payload}")
        return payload

    def request(self, method: str, path: str, *, json_payload: dict[str, Any] | None = None) -> requests.Response:
        if self.local_client is not None:
            return _LocalResponse(
                self.local_client.open(
                    path,
                    method=method.upper(),
                    json=json_payload,
                )
            )
        return self.session.request(
            method=method.upper(),
            url=f"{self.settings.base_url.rstrip('/')}{path}",
            json=json_payload,
            timeout=self.settings.request_timeout_seconds,
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
                timeout=min(self.settings.request_timeout_seconds, 30),
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
        with managed_page(self.settings, evidence, collector, use_storage_state=False) as (_, _, _, page):
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

    def _bootstrap_via_remote_internal_session(self) -> dict[str, Any]:
        bootstrap_remote_prod_safe_storage_state(self.settings)
        if self.settings.execution_mode is E2EExecutionMode.DEV_FULL and self.settings.user_id is not None:
            self._bootstrap_local_flask_client()
        self.session.cookies.clear()
        self._load_storage_state_cookie()
        if not self._has_session_cookie():
            raise RuntimeError("Falha no bootstrap remoto PROD_SAFE: storage_state sem gv_session.")
        return {
            "success": True,
            "redirect": self.settings.post_login_path,
            "auth_source": "remote_internal_bootstrap",
        }

    def _bootstrap_local_flask_client(self) -> None:
        hostname = urlparse(self.settings.base_url).hostname or ""
        if not hostname.endswith("gestaoversus.com.br"):
            return
        try:
            from app import create_app
        except ModuleNotFoundError:
            from app32.app import create_app

        app = create_app("production")
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(self.settings.user_id)
            sess["_fresh"] = True
            sess["active_company_id"] = self.settings.company_id
        self.local_client = client

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


class _LocalResponse:
    def __init__(self, response: Any):
        self._response = response
        self.status_code = int(getattr(response, "status_code", 0) or 0)
        self.headers = getattr(response, "headers", {}) or {}
        self.url = ""
        self.text = response.get_data(as_text=True)

    def json(self) -> Any:
        return self._response.get_json(silent=False)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error", response=self)  # type: ignore[arg-type]
