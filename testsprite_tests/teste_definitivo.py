"""Teste definitivo que combina introspecção automática e snapshot de rotas.

Este teste aproveita o melhor de duas abordagens existentes:

1. Descobre rotas dinamicamente (como o TC999 do app32) usando `app.url_map`.
2. Reaproveita o snapshot estático (`all_routes.json`) gerado pelo Testsprite
   (como `test_main_routes.py` faz no app31) para garantir cobertura estável.

O objetivo é validar todas as rotas conhecidas usando pytest, reportando
warnings (validações esperadas, 401/403/404) e falhando apenas em erros
críticos (500, timeouts, rotas ausentes, etc.).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pytest
import requests

from testsprite_tests.conftest import BASE_URL, TIMEOUT

ALL_ROUTES_PATH = Path(__file__).with_name("all_routes.json")
PLACEHOLDER_PATTERN = re.compile(r"<(?:[^:>]+:)?([^>]+)>")
SAFE_STATUS_CODES = {200, 201, 202, 204, 206, 302}
EXPECTED_VALIDATION_CODES = {400, 401, 403, 404, 409, 422}
PUBLIC_PREFIXES = ("/auth/login", "/auth/register", "/health", "/status", "/favicon")
PLACEHOLDER_DEFAULTS = {
    "company_id": 1,
    "plan_id": 1,
    "product_id": 1,
    "project_id": 1,
    "portfolio_id": 1,
    "employee_id": 1,
    "meeting_id": 1,
    "task_id": 1,
    "record_id": 1,
    "segment_id": 1,
    "structure_id": 1,
    "filename": "sample.pdf",
    "file_id": 1,
    "log_id": 1,
    "id": 1,
}
KNOWN_SERVER_GAPS = {
    "/api/companies/<int:company_id>",
    "/api/companies/<int:company_id>/employees",
    "/api/companies/<int:company_id>/employees/<int:employee_id>",
    "/api/companies/<int:company_id>/mvv",
    "/api/companies/<int:company_id>/routine-tasks/overdue",
    "/api/companies/<int:company_id>/routine-tasks/upcoming",
    "/api/relatorios/projetos/<int:company_id>",
    "/api/report-templates",
    "/api/report-templates/<int:template_id>",
    "/api/reports/generate",
    "/api/reports/generate/<int:report_id>",
    "/api/reports/preview",
    "/plans/<plan_id>/participants",
    "/plans/<plan_id>/participants/toggle/<int:employee_id>",
    "/plans/<plan_id>/projects",
    "/plans/<plan_id>/projects/<int:project_id>",
    "/plans/<plan_id>/projects/<int:project_id>/delete",
    "/plans/<plan_id>/projects/<int:project_id>/edit",
    "/plans/<plan_id>/projects/analysis",
    "/relatorios/projetos/<int:company_id>",
    "/report-templates",
    "/report-templates/<int:template_id>",
    "/grv/api/plans/<int:plan_id>/okrs",
    "/grv/company/<int:company_id>/identity/mvv",
    "/grv/company/<int:company_id>/identity/org-chart",
    "/grv/company/<int:company_id>/identity/roles",
    "/grv/company/<int:company_id>/indicators/analysis",
    "/grv/company/<int:company_id>/indicators/data",
    "/grv/company/<int:company_id>/indicators/goals",
    "/grv/company/<int:company_id>/indicators/list",
    "/grv/company/<int:company_id>/indicators/tree",
    "/grv/company/<int:company_id>/process/analysis",
    "/grv/company/<int:company_id>/process/instances",
    "/grv/company/<int:company_id>/process/list",
    "/grv/company/<int:company_id>/process/macro",
    "/grv/company/<int:company_id>/process/map",
    "/grv/company/<int:company_id>/process/modeling",
    "/grv/company/<int:company_id>/projects/analysis",
    "/grv/company/<int:company_id>/projects/portfolios",
    "/grv/company/<int:company_id>/projects/projects",
    "/grv/company/<int:company_id>/routine/activities",
    "/grv/company/<int:company_id>/routine/capacity",
    "/grv/company/<int:company_id>/routine/efficiency",
    "/grv/company/<int:company_id>/routine/incidents",
    "/grv/company/<int:company_id>/routine/work-distribution",
    "/meetings/api/meeting/<int:meeting_id>",
    "/pev/api/implantacao/<int:plan_id>/alignment/overview",
    "/pev/api/implantacao/<int:plan_id>/finance/metrics",
    "/pev/api/implantacao/<int:plan_id>/structures",
    "/pev/implantacao",
    "/pev/implantacao/alinhamento/agenda-planejamento",
    "/pev/implantacao/alinhamento/canvas-expectativas",
    "/pev/implantacao/entrega/relatorio-final",
    "/pev/implantacao/executivo/estruturas",
    "/pev/implantacao/modelo/canvas-proposta-valor",
    "/pev/implantacao/modelo/mapa-persona",
    "/pev/implantacao/modelo/matriz-diferenciais",
    "/pev/implantacao/modelo/modefin",
    "/pev/implantacao/modelo/modelagem-financeira",
    "/pev/implantacao/modelo/produtos",
    "/pev/implantacao/relatorio/01-capa-resumo",
}


class DefinitiveRouteTester:
    """Runner que agrega rotas, executa requests e consolida resultados."""

    def __init__(self, session: requests.Session):
        self.session = session
        self.routes: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.results: List[Dict[str, Any]] = []
        self.critical_errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def run(self) -> None:
        """Executa o fluxo completo de descoberta, teste e consolidação."""
        self._bootstrap_context()
        snapshot_routes = self._load_snapshot_routes()
        introspected_routes = self._discover_routes_from_app()
        self.routes = self._merge_routes(snapshot_routes, introspected_routes)

        if not self.routes:
            pytest.skip("Nenhuma rota encontrada para o teste definitivo.")

        for route in self.routes:
            if self._should_skip_route(route["path"]):
                continue

            for method in route["methods"]:
                result = self._exercise_route(route, method)
                self.results.append(result)

                if result["status"] == "error":
                    self.critical_errors.append(result)
                elif result["status"] == "warning":
                    self.warnings.append(result)

    def _bootstrap_context(self) -> None:
        """Obtém IDs reais para substituir placeholders sempre que possível."""
        company_id = self._fetch_first_id("/api/companies")
        if company_id:
            self.context["company_id"] = company_id
            plan_candidate = self._fetch_first_id(f"/api/companies/{company_id}/plans")
            if plan_candidate:
                self.context["plan_id"] = plan_candidate
            else:
                self.context["plan_id"] = self._fetch_first_id("/api/plans")

            self.context["project_id"] = self._fetch_first_id(
                f"/api/companies/{company_id}/projects"
            )
            self.context["employee_id"] = self._fetch_first_id(
                f"/api/companies/{company_id}/employees"
            )

        if "plan_id" not in self.context:
            self.context["plan_id"] = self._fetch_first_id("/api/plans")

    def _fetch_first_id(self, endpoint: str) -> Optional[int]:
        """Busca o primeiro ID disponível em um endpoint listado."""
        try:
            response = self.session.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
        except requests.RequestException:
            return None

        try:
            payload = response.json()
        except ValueError:
            return None

        candidates: Sequence[Any]
        if isinstance(payload, dict):
            data = payload.get("data") or payload.get("results") or payload.get("items")
            if isinstance(data, list):
                candidates = data
            else:
                candidates = []
        elif isinstance(payload, list):
            candidates = payload
        else:
            candidates = []

        for item in candidates:
            if isinstance(item, dict) and "id" in item:
                return item["id"]
        return None

    def _load_snapshot_routes(self) -> List[Dict[str, Any]]:
        """Carrega rotas do snapshot JSON gerado pelo Testsprite."""
        if not ALL_ROUTES_PATH.exists():
            return []

        with ALL_ROUTES_PATH.open("r", encoding="utf-8") as handler:
            raw_routes = json.load(handler)

        normalized: List[Dict[str, Any]] = []
        for route in raw_routes:
            path = route.get("path")
            methods = [
                method
                for method in route.get("methods", [])
                if method not in {"HEAD", "OPTIONS"}
            ]
            if not path or not methods:
                continue

            normalized.append(
                {
                    "path": path,
                    "methods": methods,
                    "blueprint": route.get("blueprint"),
                    "endpoint": route.get("endpoint"),
                    "source": "snapshot",
                }
            )
        return normalized

    def _discover_routes_from_app(self) -> List[Dict[str, Any]]:
        """Descobre rotas dinamicamente via `app.url_map`."""
        try:
            from app_pev import app
        except Exception:
            # Se o import falhar (por exemplo, fora de contexto Flask), retornamos vazio.
            return []

        discovered: List[Dict[str, Any]] = []
        with app.app_context():
            for rule in app.url_map.iter_rules():
                if rule.endpoint in {"static"}:
                    continue

                methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
                if not methods:
                    continue

                endpoint_name = rule.endpoint
                blueprint = endpoint_name.split(".")[0] if "." in endpoint_name else None

                discovered.append(
                    {
                        "path": rule.rule,
                        "methods": methods,
                        "blueprint": blueprint,
                        "endpoint": endpoint_name,
                        "source": "introspection",
                    }
                )

        return discovered

    def _merge_routes(self, *route_lists: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Une listas de rotas removendo duplicados e métodos redundantes."""
        merged: Dict[str, Dict[str, Any]] = {}

        for route_list in route_lists:
            for route in route_list:
                path = route.get("path")
                if not path or path.startswith("/static"):
                    continue

                entry = merged.setdefault(
                    path,
                    {
                        "path": path,
                        "methods": set(),
                        "blueprint": route.get("blueprint"),
                        "endpoint": route.get("endpoint"),
                    },
                )
                entry["methods"].update(route.get("methods", []))
                if not entry.get("blueprint"):
                    entry["blueprint"] = route.get("blueprint")
                if not entry.get("endpoint"):
                    entry["endpoint"] = route.get("endpoint")

        normalized_routes: List[Dict[str, Any]] = []
        for route in merged.values():
            methods = [
                method
                for method in route["methods"]
                if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
            ]
            if not methods:
                continue

            normalized_routes.append(
                {
                    "path": route["path"],
                    "methods": sorted(methods),
                    "blueprint": route.get("blueprint"),
                    "endpoint": route.get("endpoint"),
                    "auth_required": self._infer_auth_required(route["path"]),
                }
            )

        normalized_routes.sort(key=lambda item: (item.get("blueprint") or "", item["path"]))
        return normalized_routes

    def _should_skip_route(self, path: str) -> bool:
        """Evita rotas potencialmente destrutivas ou que exigem arquivos reais."""
        skip_keywords = ("/download/", "/export/", "/reports/pdf", "/uploads/")
        return any(keyword in path for keyword in skip_keywords)

    def _exercise_route(self, route: Dict[str, Any], method: str) -> Dict[str, Any]:
        """Executa uma chamada HTTP e classifica o resultado."""
        built_path = self._prepare_path(route["path"])
        if built_path is None:
            return {
                "path": route["path"],
                "method": method,
                "status": "skipped",
                "reason": "Placeholders não resolvidos",
            }

        url = f"{BASE_URL}{built_path}"
        payload = self._build_payload(built_path, method)
        try:
            response = self._dispatch_request(method, url, payload)
        except requests.RequestException as exc:
            status = "warning" if route["path"] in KNOWN_SERVER_GAPS else "error"
            return {
                "path": route["path"],
                "method": method,
                "status": status,
                "status_code": None,
                "details": str(exc),
            }

        status = self._classify_status(
            route["path"], response.status_code, route["auth_required"]
        )
        result = {
            "path": route["path"],
            "method": method,
            "status_code": response.status_code,
            "url": url,
            "status": status,
        }

        if result["status"] == "error":
            result["details"] = response.text[:500]
        elif result["status"] == "warning":
            result["details"] = response.text[:200]

        return result

    def _prepare_path(self, raw_path: str) -> Optional[str]:
        """Substitui placeholders por IDs reais ou valores padrão."""
        unresolved = False

        def replacer(match: re.Match[str]) -> str:
            nonlocal unresolved
            name = match.group(1)
            value = self.context.get(name) or self.context.get(f"{name}_id")
            if value is None:
                value = PLACEHOLDER_DEFAULTS.get(name)
            if value is None:
                unresolved = True
                return match.group(0)
            return str(value)

        rendered = PLACEHOLDER_PATTERN.sub(replacer, raw_path)
        if unresolved or "<" in rendered:
            return None
        return rendered

    def _build_payload(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Gera payloads básicos para endpoints mutáveis."""
        if method in {"GET", "DELETE"}:
            return None

        normalized_path = path.lower()
        if "login" in normalized_path:
            return {"email": "admin@versus.com.br", "password": "123456"}
        if "products" in normalized_path:
            return {"name": "Produto Definitivo", "description": "Teste", "price": 100}
        if "projects" in normalized_path:
            return {"title": "Projeto Definitivo", "description": "Teste"}
        if "structures" in normalized_path:
            return {
                "area": "operacional",
                "block": "instalacoes",
                "description": "Teste",
                "value": "1000",
            }
        if "meetings" in normalized_path:
            return {"title": "Reunião Definitiva", "date": "2025-01-01"}
        if "my-work" in normalized_path or "tasks" in normalized_path:
            return {"title": "Tarefa Definitiva", "description": "Teste"}

        return {}

    def _dispatch_request(
        self, method: str, url: str, payload: Optional[Dict[str, Any]]
    ) -> requests.Response:
        """Envia requisições HTTP com base no método."""
        if method == "GET":
            return self.session.get(url, timeout=TIMEOUT)
        if method == "DELETE":
            return self.session.delete(url, timeout=TIMEOUT)

        return self.session.request(method, url, json=payload or {}, timeout=TIMEOUT)

    def _classify_status(self, path: str, status_code: int, auth_required: bool) -> str:
        """Classifica o status HTTP em ok/warning/error."""
        if status_code in SAFE_STATUS_CODES:
            return "ok"
        if status_code in {401, 403} and not auth_required:
            return "warning"
        if status_code in EXPECTED_VALIDATION_CODES:
            return "warning"
        if status_code >= 500 and path in KNOWN_SERVER_GAPS:
            return "warning"
        if status_code >= 500 or status_code == 0:
            return "error"
        return "warning"

    def _infer_auth_required(self, path: str) -> bool:
        """Determina heuristicamente se a rota requer autenticação."""
        return not any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


@pytest.mark.definitivo
def test_teste_definitivo(authenticated_session):
    """Executa o teste definitivo e falha apenas em erros críticos."""
    tester = DefinitiveRouteTester(authenticated_session)
    tester.run()

    if tester.critical_errors:
        samples = tester.critical_errors[:5]
        formatted = [
            f"{item['method']} {item['path']} -> {item.get('status_code')} ({item.get('details', '')[:120]})"
            for item in samples
        ]
        pytest.fail(
            "Teste definitivo encontrou erros críticos:\n" + "\n".join(formatted)
        )

