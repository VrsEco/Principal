"""
Serviço responsável por executar o teste de conformidade do aplicativo
com base no catálogo de páginas/elementos (endereçamento UI).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from models import db
from models.app_compliance_report import AppComplianceReport, AppComplianceReportItem
from services.ui_reference_service_v2 import UIReferenceServiceV2

logger = logging.getLogger(__name__)


class AppComplianceService:
    """Executa verificações estruturais usando o catálogo de UI como fonte única."""

    STATUS_ORDER = {"ok": 0, "warn": 1, "fail": 2}
    DEFAULT_TEST_CONTEXT = {
        "company_id": 13,
        "plan_id": 1,
        "project_id": 1,
        "process_id": 1,
        "instance_id": 1,
        "routine_id": 1,
        "meeting_id": 1,
    }

    def __init__(self) -> None:
        if not current_app:
            raise RuntimeError("AppComplianceService requer um contexto do Flask ativo.")

        template_folder = current_app.template_folder or "templates"
        self.templates_root = Path(current_app.root_path) / template_folder
        self.actions_config = self._load_actions_config()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def run(
        self,
        scope: str = "full",
        page_code: Optional[str] = None,
        probe_routes: bool = False,
        probe_user_id: Optional[int] = None,
        persist: bool = False,
        test_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executa o escaneamento de conformidade e retorna um relatório estruturado."""

        try:
            catalog_pages = UIReferenceServiceV2.get_all_pages()
        except Exception as exc:  # pragma: no cover - log para troubleshooting
            logger.exception("Erro ao consultar catálogo de UI: %s", exc)
            raise RuntimeError("Não foi possível acessar o catálogo de UI.") from exc

        normalized_scope = (scope or "full").lower()
        pages = self._filtrar_paginas(catalog_pages, normalized_scope, page_code)

        merged_context = dict(self.DEFAULT_TEST_CONTEXT)
        if test_context:
            for key, value in test_context.items():
                if value not in (None, "", []):
                    merged_context[key] = value

        resultados: List[Dict[str, Any]] = []
        for page in pages:
            try:
                resultados.append(
                    self._inspecionar_pagina(page, probe_routes, probe_user_id, merged_context)
                )
            except Exception as exc:  # pragma: no cover - falha inesperada em página específica
                logger.exception("Falha ao inspecionar página %s: %s", page.get("page_code"), exc)
                resultados.append(
                    {
                        "page_code": page.get("page_code"),
                        "page_name": page.get("page_name"),
                        "page_route": page.get("page_route"),
                        "template_file": page.get("template_file"),
                        "status": "fail",
                        "checks": [
                            {
                                "item": "runtime",
                                "status": "fail",
                                "detail": f"Erro inesperado ao analisar esta página: {exc}",
                            }
                        ],
                        "primary_issue": "Erro inesperado durante a análise.",
                    }
                )

        overview = self._gerar_resumo(resultados)
        overview_with_context = dict(overview)
        overview_with_context["test_context"] = merged_context

        relatorio = {
            "scope": normalized_scope,
            "requested_code": self._normalize_code(page_code) if page_code else None,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "overview": overview_with_context,
            "results": resultados,
            "test_context": merged_context,
        }

        if persist:
            report = self._persist_report(relatorio, probe_user_id)
            if report:
                relatorio["report_id"] = report.id

        return relatorio

    def format_message(
        self,
        relatorio: Dict[str, Any],
        highlight_limit: int = 5,
        severity: str = "all",
    ) -> str:
        """Gera uma mensagem amigável para ser usada pelo agente."""
        overview = relatorio.get("overview") or {}
        results = relatorio.get("results") or []
        filtered = self._filter_results(results, severity)
        filtro_label = self._describe_filter(severity)

        lines = [
            "📋 Teste de Conformidade concluído.",
            f"• Escopo original: {overview.get('total_pages', 0)} páginas (OK: {overview.get('ok', 0)} | ⚠️ {overview.get('warn', 0)} | ❌ {overview.get('fail', 0)})",
            f"• Filtro aplicado: {filtro_label} → exibindo {len(filtered)} item(s)",
        ]

        scope = relatorio.get("scope")
        if scope == "page" and filtered:
            lines.append(
                f"• Página analisada: {filtered[0].get('page_code')} - {filtered[0].get('page_name') or 'sem nome'}"
            )

        if not filtered:
            lines.append("Nenhuma página corresponde ao filtro escolhido.")
            return "\n".join(lines)

        lines.append("")
        lines.append("Principais apontamentos:")

        for result in filtered[: max(1, highlight_limit)]:
            icon = self._status_icon(result.get("status"))
            issue = result.get("primary_issue") or "Sem pendências registradas."
            page_code = result.get("page_code") or "---"
            page_name = result.get("page_name") or "Página sem título"
            lines.append(f"{icon} {page_code} • {page_name}: {issue}")

        if len(filtered) > highlight_limit:
            lines.append(f"... +{len(filtered) - highlight_limit} páginas adicionais no relatório.")

        return "\n".join(lines)

    def generate_text_report(self, relatorio: Dict[str, Any], severity: str = "all") -> str:
        filtered = self._filter_results(relatorio.get("results") or [], severity)
        overview = relatorio.get("overview") or {}
        context = relatorio.get("test_context") or overview.get("test_context") or {}
        filtro_label = self._describe_filter(severity)

        lines = [
            "==========================",
            "RELATÓRIO DE CONFORMIDADE",
            "==========================",
            f"Gerado em: {relatorio.get('generated_at') or 'agora mesmo'}",
            f"Escopo: {relatorio.get('scope') or 'full'}",
            f"Filtro aplicado: {filtro_label}",
            f"Registros exibidos: {len(filtered)}",
            f"Total original: {overview.get('total_pages', 0)} (OK: {overview.get('ok', 0)} | ⚠️ {overview.get('warn', 0)} | ❌ {overview.get('fail', 0)})",
        ]

        if context:
            lines.append(
                "Contexto usado: "
                + ", ".join(f"{k}={v}" for k, v in context.items())
            )

        lines.append("")

        for result in filtered:
            lines.append(f"[{result.get('status', '').upper()}] Página {result.get('page_code')}: {result.get('page_name')}")
            lines.append(f"Rota: {result.get('page_route')}")
            for check in result.get("checks", []):
                lines.append(f"  - {check.get('item')}: {check.get('detail')}")
            lines.append("")

        return "\n".join(lines) or "Relatório vazio."

    def generate_pdf_report(self, relatorio: Dict[str, Any], severity: str = "all") -> bytes:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except Exception as exc:
            raise RuntimeError(
                "Biblioteca reportlab não está instalada. Instale 'reportlab' para gerar PDF."
            ) from exc

        import io

        text_report = self.generate_text_report(relatorio, severity)
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 40

        for line in text_report.splitlines():
            if y <= 40:
                c.showPage()
                y = height - 40
            c.drawString(40, y, line[:120])
            y -= 14

        c.save()
        buffer.seek(0)
        return buffer.read()

    def build_preview(self, relatorio: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Gera um pequeno resumo para ser usado como preview no chat."""
        overview = relatorio.get("overview") or {}
        if not overview:
            return None

        preview = {
            "Páginas avaliadas": overview.get("total_pages", 0),
            "OK": overview.get("ok", 0),
            "Com alertas": overview.get("warn", 0),
            "Com falhas": overview.get("fail", 0),
        }
        ctx = relatorio.get("test_context") or overview.get("test_context")
        if ctx:
            preview["Contexto"] = f"company_id={ctx.get('company_id', '-')}, plan_id={ctx.get('plan_id', '-')}"

        first_issue = next(
            (
                result
                for result in relatorio.get("results", [])
                if result.get("status") in {"warn", "fail"}
            ),
            None,
        )
        if first_issue:
            preview["Primeira ocorrência"] = (
                f"{first_issue.get('page_code')} - {first_issue.get('primary_issue')}"
            )

        return preview

    def _load_actions_config(self) -> Dict[str, Any]:
        config_name = current_app.config.get(
            "COMPLIANCE_ACTIONS_CONFIG", "config/compliance_actions.json"
        )
        config_path = Path(current_app.root_path) / config_name
        if not config_path.exists():
            return {}
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception as exc:  # pragma: no cover
            logger.error("N?o foi poss?vel carregar %s: %s", config_path, exc)
            return {}

    # ------------------------------------------------------------------
    # Funções auxiliares
    # ------------------------------------------------------------------
    def _filtrar_paginas(
        self,
        pages: List[Dict[str, Any]],
        scope: str,
        page_code: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not pages:
            return []

        if scope == "page":
            normalized = self._normalize_code(page_code)
            filtered = [page for page in pages if page.get("page_code") == normalized]
            if not filtered:
                raise ValueError(f"Página {normalized} não encontrada no catálogo de UI.")
            return filtered

        if scope in {"active", "ativos"}:
            return [page for page in pages if page.get("active")]

        return pages

    def _normalize_code(self, code: Optional[str]) -> Optional[str]:
        if not code:
            return None
        clean = str(code).strip()
        if clean.isdigit():
            return clean.zfill(3)
        return clean[:3]

    def _inspecionar_pagina(
        self,
        page: Dict[str, Any],
        probe_routes: bool,
        probe_user_id: Optional[int],
        test_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        checks: List[Dict[str, str]] = []
        overall_status = "ok"

        def add_check(item: str, status: str, detail: str) -> None:
            nonlocal overall_status
            checks.append({"item": item, "status": status, "detail": detail})
            if self.STATUS_ORDER[status] > self.STATUS_ORDER[overall_status]:
                overall_status = status

        # Verificar template em disco
        template_file = page.get("template_file")
        if template_file:
            template_path = self.templates_root / Path(template_file)
            if template_path.exists():
                add_check("template", "ok", f"Template encontrado ({template_file})")
            else:
                add_check(
                    "template",
                    "fail",
                    f"Template não encontrado na pasta templates ({template_file})",
                )
        else:
            add_check("template", "warn", "Página sem template associado no catálogo.")

        # Verificar rota registrada no Flask
        page_route = (page.get("page_route") or "").strip()
        test_route = None
        if page_route:
            normalized_route = page_route if page_route.startswith("/") else f"/{page_route}"
            if self._route_exists(normalized_route):
                add_check("rota", "ok", f"Rota registrada: {normalized_route}")
                test_route, route_info = self._prepare_route_for_testing(normalized_route, test_context)
                if route_info["status"] == "missing":
                    add_check(
                        "rota_parametros",
                        "warn",
                        f"Defina parâmetros para testar esta rota: {', '.join(route_info['missing'])}",
                    )
                    test_route = None
                elif route_info["status"] == "applied":
                    replacements = ", ".join(f"{k}={v}" for k, v in route_info["replacements"].items())
                    add_check(
                        "rota_parametros",
                        "ok",
                        f"Rota dinâmica testada usando {replacements}",
                    )
                else:
                    test_route = normalized_route

                if probe_routes and probe_user_id and (test_route or "<" not in normalized_route):
                    route_to_test = test_route or normalized_route
                    result = self._probe_route(route_to_test, probe_user_id)
                    detail = result["detail"]
                    if result.get("stack"):
                        detail += f" | Stack: {result['stack'].splitlines()[-1]}"
                    elif result.get("body_excerpt"):
                        detail += f" | Resposta: {result['body_excerpt'][:180]}"
                    add_check("rota_execucao", result["status"], detail)
            else:
                add_check(
                    "rota",
                    "warn",
                    f"Rota {normalized_route} não encontrada no mapa de URLs do aplicativo.",
                )
        else:
            add_check("rota", "warn", "Esta página não possui rota definida no catálogo.")

        # Verificar elementos vinculados
        try:
            elements = UIReferenceServiceV2.get_elements_by_page(page.get("page_code"))
        except Exception as exc:
            logger.warning(
                "Falha ao buscar elementos da página %s: %s",
                page.get("page_code"),
                exc,
            )
            add_check("componentes", "warn", "Não foi possível verificar os elementos desta página.")
        else:
            if elements:
                ativos = [element for element in elements if element.get("active", True)]
                add_check(
                    "componentes",
                    "ok",
                    f"{len(ativos)} elemento(s) mapeado(s) no catálogo.",
                )
            else:
                add_check("componentes", "warn", "Nenhum elemento mapeado para esta página.")

        if probe_routes and probe_user_id:
            action_checks = self._run_configured_actions(
                page.get("page_code"),
                probe_user_id,
                test_context,
            )
            for action_check in action_checks:
                add_check(action_check["item"], action_check["status"], action_check["detail"])

        return {
            "page_code": page.get("page_code"),
            "page_name": page.get("page_name"),
            "page_route": page_route or None,
            "template_file": template_file,
            "status": overall_status,
            "checks": checks,
            "primary_issue": self._resumir_issue(checks),
        }

    def _route_exists(self, target_route: str) -> bool:
        for rule in current_app.url_map.iter_rules():
            if rule.rule == target_route:
                return True
        return False

    def _get_authenticated_client(self, user_id: int):
        client = current_app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        return client

    def _prepare_route_for_testing(
        self, route_template: str, test_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        if "<" not in route_template:
            return route_template, {"status": "static"}

        pattern = re.compile(r"<([^>]+)>")
        replacements: Dict[str, Any] = {}
        missing: List[str] = []

        def _replace(match: re.Match) -> str:
            token = match.group(1).strip()
            key = token.split(":")[-1].strip()
            value = test_context.get(key)
            if value is None:
                missing.append(key)
                return match.group(0)
            replacements[key] = value
            return str(value)

        new_route = pattern.sub(_replace, route_template)
        if missing:
            return route_template, {"status": "missing", "missing": missing}
        return new_route, {"status": "applied", "replacements": replacements}

    def _run_configured_actions(
        self,
        page_code: Optional[str],
        user_id: int,
        test_context: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        actions = self.actions_config.get(page_code or "") or []
        if not actions:
            return []

        checks: List[Dict[str, str]] = []
        client = self._get_authenticated_client(user_id)
        original_testing = current_app.testing
        current_app.testing = True
        try:
            for action in actions:
                description = action.get("description") or action.get("path") or "Ação configurada"
                required = action.get("required_context") or []
                missing = [
                    key for key in required if test_context.get(key) in (None, "", [], {})
                ]
                if missing:
                    checks.append(
                        {
                            "item": f"acao:{description}",
                            "status": "warn",
                            "detail": f"Parâmetros ausentes para executar a ação: {', '.join(missing)}",
                        }
                    )
                    continue

                path_template = action.get("path")
                if not path_template:
                    checks.append(
                        {
                            "item": f"acao:{description}",
                            "status": "warn",
                            "detail": "Ação configurada sem caminho/path.",
                        }
                    )
                    continue

                try:
                    rendered_path = path_template.format(**test_context)
                except KeyError as exc:
                    checks.append(
                        {
                            "item": f"acao:{description}",
                            "status": "warn",
                            "detail": f"Contexto insuficiente para montar a rota ({exc}).",
                        }
                    )
                    continue

                json_payload = action.get("json")
                data_payload = action.get("data")
                try:
                    if json_payload is not None:
                        json_payload = self._render_action_value(json_payload, test_context)
                    if data_payload is not None:
                        data_payload = self._render_action_value(data_payload, test_context)
                except KeyError as exc:
                    checks.append(
                        {
                            "item": f"acao:{description}",
                            "status": "warn",
                            "detail": f"Contexto insuficiente para montar o payload ({exc}).",
                        }
                    )
                    continue

                method = (action.get("method") or "GET").upper()
                try:
                    response = client.open(
                        rendered_path,
                        method=method,
                        json=json_payload,
                        data=data_payload,
                    )
                    status_code = response.status_code
                    body_excerpt = response.get_data(as_text=True)[:300]
                    is_ok = self._matches_expected_status(status_code, action.get("expected_status"))
                    detail = f"{method} {rendered_path} -> {status_code}"
                    if body_excerpt:
                        detail += f" | Resposta: {body_excerpt}"
                    checks.append(
                        {
                            "item": f"acao:{description}",
                            "status": "ok" if is_ok else "fail",
                            "detail": detail,
                        }
                    )
                except Exception as exc:  # pragma: no cover - execução defensiva
                    checks.append(
                        {
                            "item": f"acao:{description}",
                            "status": "fail",
                            "detail": f"Erro ao executar ação: {exc}",
                        }
                    )
        finally:
            current_app.testing = original_testing

        return checks

    def _render_action_value(self, value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str):
            return value.format(**context)
        if isinstance(value, list):
            return [self._render_action_value(item, context) for item in value]
        if isinstance(value, dict):
            return {k: self._render_action_value(v, context) for k, v in value.items()}
        return value

    def _matches_expected_status(self, status: int, expected: Optional[Any]) -> bool:
        if expected is None:
            return 200 <= status < 300
        if isinstance(expected, int):
            return status == expected
        if isinstance(expected, str) and expected.endswith("xx") and expected[:-2].isdigit():
            return status // 100 == int(expected[:-2])
        if isinstance(expected, (list, tuple, set)):
            return any(self._matches_expected_status(status, item) for item in expected)
        if isinstance(expected, dict):
            min_status = expected.get("min")
            max_status = expected.get("max")
            if min_status is not None and status < int(min_status):
                return False
            if max_status is not None and status > int(max_status):
                return False
            return True
        return False

    def _filter_results(self, results: List[Dict[str, Any]], severity: str) -> List[Dict[str, Any]]:
        severity = (severity or "all").lower()
        if severity == "errors":
            allowed = {"fail"}
        elif severity == "warnings":
            allowed = {"warn"}
        else:
            allowed = None

        if not allowed:
            return list(results)
        return [item for item in results if item.get("status") in allowed]

    def _describe_filter(self, severity: str) -> str:
        mapping = {
            "errors": "apenas erros (❌)",
            "warnings": "apenas alertas (⚠️)",
            "all": "completo",
        }
        return mapping.get((severity or "all").lower(), "personalizado")

    def _probe_route(self, target_route: str, user_id: int) -> Dict[str, str]:
        client = self._get_authenticated_client(user_id)
        original_testing = current_app.testing
        current_app.testing = True
        try:
            response = client.get(target_route, follow_redirects=False)
            status_code = response.status_code
            body_excerpt = response.get_data(as_text=True)[:500] if status_code >= 400 else None

            if 200 <= status_code < 300:
                return {
                    "status": "ok",
                    "detail": f"GET {target_route} respondeu {status_code}",
                }
            if 300 <= status_code < 400:
                return {
                    "status": "warn",
                    "detail": f"GET {target_route} redirecionou com status {status_code}",
                }
            return {
                "status": "fail",
                "detail": f"GET {target_route} retornou erro {status_code}",
                "body_excerpt": body_excerpt,
            }
        except Exception as exc:  # pragma: no cover - dificuldade em simular erros externos
            return {
                "status": "fail",
                "detail": f"Erro ao acessar {target_route}: {exc}",
                "stack": traceback.format_exc(),
            }
        finally:
            current_app.testing = original_testing

    def _resumir_issue(self, checks: List[Dict[str, str]]) -> str:
        first_issue = next((check for check in checks if check["status"] != "ok"), None)
        if not first_issue:
            return "Todos os itens passaram na verificação."
        return f"{first_issue['item']}: {first_issue['detail']}"

    def _gerar_resumo(self, resultados: List[Dict[str, Any]]) -> Dict[str, int]:
        totals = {"total_pages": len(resultados), "ok": 0, "warn": 0, "fail": 0}
        for result in resultados:
            status = result.get("status", "warn")
            if status in totals:
                totals[status] += 1
            else:
                totals["warn"] += 1
        return totals

    def _persist_report(self, relatorio: Dict[str, Any], user_id: Optional[int]) -> Optional[AppComplianceReport]:
        overview = relatorio.get("overview") or {}
        try:
            report = AppComplianceReport(
                user_id=user_id,
                scope=relatorio.get("scope"),
                requested_code=relatorio.get("requested_code"),
                total_pages=overview.get("total_pages", 0),
                ok_count=overview.get("ok", 0),
                warn_count=overview.get("warn", 0),
                fail_count=overview.get("fail", 0),
                overview=overview,
            )
            db.session.add(report)
            db.session.flush()

            for item in relatorio.get("results", []):
                db.session.add(
                    AppComplianceReportItem(
                        report_id=report.id,
                        page_code=item.get("page_code"),
                        page_name=item.get("page_name"),
                        page_route=item.get("page_route"),
                        status=item.get("status"),
                        primary_issue=item.get("primary_issue"),
                        checks=item.get("checks"),
                    )
                )

            db.session.commit()
            return report
        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.error("Erro ao salvar relatório de conformidade: %s", exc)
            return None

    def persist_report(self, relatorio: Dict[str, Any], user_id: Optional[int] = None) -> Optional[int]:
        report = self._persist_report(relatorio, user_id)
        return report.id if report else None

    def _status_icon(self, status: Optional[str]) -> str:
        return {
            "ok": "✅",
            "warn": "⚠️",
            "fail": "❌",
        }.get(status or "warn", "⚠️")
