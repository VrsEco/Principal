#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de relatório inspirado na página My Work.

A partir dos filtros e dados que alimentam o dashboard, monta um resumo
com cabeçalho, indicadores e a listagem de cartões de atividades/processos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from relatorios.generators.base import BaseReportGenerator
from services.my_work_service import (
    count_activities_by_scope,
    DELIVERY_TAGS,
    get_employee_from_user,
    get_filter_options,
    get_user_activities,
    get_user_stats,
)

DELIVERY_TAG_LABELS = {"open": "Em aberto", "completed": "Concluídas"}
SCOPE_LABELS = {"me": "Minhas atividades", "team": "Equipe", "company": "Empresa"}
FILTER_SHORTCUTS = {
    "today": "Hoje",
    "week": "Semana atual",
    "overdue": "Apenas atrasadas",
}
MAX_SUMMARY_ITEMS = 4


class MyWorkReport(BaseReportGenerator):
    """
    Relatório simplificado da tela My Work.

    Permite fornecer filtros e exibir:
    - Cabeçalho fixo com título e número de páginas
    - Seção de filtros ativos
    - Contadores/indicadores
    - Cards com as atividades e instâncias
    """

    REPORT_TITLE = "Gestão da Rotina"

    def __init__(self, report_model_id: Optional[int] = None):
        super().__init__(report_model_id)
        self._add_custom_styles()

    def get_report_title(self) -> str:
        return self.REPORT_TITLE

    def get_header(self) -> str:
        user_name = (self.data.get("user") or {}).get("name") or "Usuário"
        return f"""
        <div class="custom-report-header">
            <div class="header-grid">
                <div class="header-cell">
                    Gestão da Rotina
                </div>
                <div class="header-cell header-center">
                    {user_name}
                </div>
                <div class="header-cell header-right">
                    Página 1 de 1
                </div>
            </div>
        </div>
        """

    def get_footer(self) -> str:
        return """
        <div class="custom-report-footer">
            <div class="footer-grid">
                <div class="footer-cell">
                    Versus Gestão Corporativa - Todos os Direitos Reservados
                </div>
                <div class="footer-cell footer-right">
                    Emitido em: 10/12/2025 às 10:31
                </div>
            </div>
        </div>
        """

    def fetch_data(
        self,
        *,
        user_id: int,
        user_name: Optional[str] = None,
        employee_id: Optional[int] = None,
        scope: str = "me",
        company_id: Optional[int] = None,
        company_ids: Optional[Sequence[int]] = None,
        filters: Optional[Dict[str, Any]] = None,
        max_activities: Optional[int] = 40,
    ) -> None:
        """
        Busca dados de filtros, atividades e indicadores.

        Args:
            user_id: ID do usuário logado que acessa o dashboard.
            employee_id: Override para o colaborador (caso já saiba o ID).
            scope: Escopo a ser usado no dashboard.
            company_id: Empresa legada (opcional).
            company_ids: Lista de empresas selecionadas.
            filters: Dicionário com filtros adicionais.
            max_activities: Quantidade máxima de cards a mostrar.
        """
        employee_id = employee_id or get_employee_from_user(user_id)
        if not employee_id:
            raise ValueError("Usuário sem colaborador vinculado.")

        filters_payload = dict(filters or {})
        resolved_user_name = self._resolve_user_name(user_id, user_name)
        self.data["user"] = {"name": resolved_user_name}
        resolved_company_ids = self._resolve_company_ids(
            company_id, company_ids, filters_payload
        )
        if resolved_company_ids is not None:
            filters_payload["company_ids"] = resolved_company_ids
        filters_payload["scope"] = scope

        filter_options = get_filter_options(user_id)
        activities = get_user_activities(
            employee_id,
            scope,
            company_id=company_id,
            company_ids=resolved_company_ids,
            filters=filters_payload,
        )
        stats = get_user_stats(
            employee_id,
            scope=scope,
            company_id=company_id,
            company_ids=resolved_company_ids,
            filters=filters_payload,
        )
        counts = count_activities_by_scope(
            employee_id,
            company_id=company_id,
            company_ids=resolved_company_ids,
            filters=filters_payload,
        )

        limit = max(0, max_activities or 0)
        preview_activities = activities[:limit] if limit else []

        self.data["company"] = {
            "name": self._resolve_company_title(
                filter_options.get("companies") or [], resolved_company_ids
            )
        }
        self.data["filters_summary"] = self._build_filters_summary(
            filters_payload, filter_options, resolved_company_ids, scope
        )
        self.data["activities"] = preview_activities
        self.data["activities_total"] = len(activities)
        self.data["stats"] = stats
        self.data["counts"] = counts
        self.data["filters_payload"] = filters_payload

    def build_sections(self) -> None:
        self.clear_sections()
        self.add_section("Filtros", self._render_filters_section())
        self.add_section("Indicadores", self._render_indicators_section())
        self.add_section("Atividades e Instâncias", self._render_activities_section())

    # =============================================
    # Seções renderizadas
    # =============================================

    def _render_filters_section(self) -> str:
        summary = self.data.get("filters_summary") or []
        if not summary:
            return "<p>Nenhum filtro específico foi aplicado.</p>"

        items = "".join(
            f"<li><strong>{entry['label']}:</strong> {entry['value']}</li>"
            for entry in summary
        )
        return f"<ul class='filters-summary'>{items}</ul>"

    def _render_indicators_section(self) -> str:
        stats = self.data.get("stats") or {}
        counts = self.data.get("counts") or {}
        displayed = len(self.data.get("activities") or [])
        total = self.data.get("activities_total", 0)

        cells = []
        for label, key, note in [
            ("Em aberto", "pending", "Atualizado"),
            ("Em andamento", "in_progress", "Atualizado"),
            ("Atrasadas", "overdue", "Atualizado"),
            ("Concluídas", "completed", "Atualizado"),
            ("Escopo pessoal", "me", "Contador"),
            ("Escopo da equipe", "team", "Contador"),
            ("Escopo da empresa", "company", "Contador"),
        ]:
            value = stats.get(key, counts.get(key, 0))
            cells.append(
                f"""
                <td>
                    <div class="indicator-cell">
                        <div class="indicator-title">{label}</div>
                        <div class="indicator-number">{value}</div>
                        <div class="indicator-note">{note}</div>
                    </div>
                </td>
                """
            )

        rows_html = ""
        for i in range(0, len(cells), 3):
            row_cells = cells[i : i + 3]
            while len(row_cells) < 3:
                row_cells.append("<td></td>")
            rows_html += f"<tr>{''.join(row_cells)}</tr>"

        preview_note = f"<p class='activity-count'>Mostrando {displayed} de {total} registros.</p>"
        return f"<table class='indicator-table'>{rows_html}</table>{preview_note}"

    def _render_activities_section(self) -> str:
        activities = self.data.get("activities") or []
        if not activities:
            return "<p>Nenhuma atividade ou instância disponível.</p>"

        rows = []
        rows.append(
            "<tr><th>Tipo</th><th>Projeto / Processo</th><th>Atividade / Instância</th><th>Responsável</th><th>Prazo</th><th>Status</th></tr>"
        )
        for activity in activities:
            kind = "Processo" if activity.get("type") == "process" else "Projeto"
            primary = self._format_code_name(
                activity.get("process_code") if kind == "Processo" else activity.get("project_code"),
                activity.get("process_name") or activity.get("title") if kind == "Processo" else activity.get("project_title") or activity.get("plan_name")
            )
            secondary = self._format_code_name(
                activity.get("instance_code") if kind == "Processo" else activity.get("activity_code"),
                activity.get("title")
            )
            responsible = self._resolve_responsible_name(activity)
            deadline = activity.get("deadline") or "-"
            status = (activity.get("status") or "").title()
            rows.append(
                f"<tr><td>{kind}</td><td>{primary}</td><td>{secondary}</td><td>{responsible}</td><td>{deadline}</td><td>{status}</td></tr>"
            )
        return f"<table class='activity-table'>{''.join(rows)}</table>"

    # =============================================
    # Auxiliares de filtros
    # =============================================

    def _resolve_company_ids(
        self,
        explicit_company_id: Optional[int],
        explicit_company_ids: Optional[Sequence[int]],
        filters: Dict[str, Any],
    ) -> Optional[List[int]]:
        if explicit_company_ids:
            return list(explicit_company_ids)

        if explicit_company_id:
            return [explicit_company_id]

        candidate = filters.get("company_ids")
        if candidate:
            return [int(value) for value in candidate if value is not None]

        single = filters.get("company_id")
        if single is not None:
            return [int(single)]

        return None

    def _resolve_company_title(
        self,
        companies: List[Dict[str, Any]],
        selected_ids: Optional[List[int]],
    ) -> str:
        if selected_ids:
            matches = [
                comp
                for comp in companies
                if comp.get("company_id") in selected_ids
            ]
            if len(matches) == 1:
                return matches[0].get("company_name") or "Nome da Empresa"
            if matches:
                return matches[0].get("company_name") or "Nome da Empresa"

        if companies:
            return companies[0].get("company_name") or "Nome da Empresa"

        return "Nome da Empresa"

    def _build_filters_summary(
        self,
        filters: Dict[str, Any],
        options: Dict[str, List[Dict[str, Any]]],
        company_ids: Optional[List[int]],
        scope: str,
    ) -> List[Dict[str, str]]:
        summary: List[Dict[str, str]] = []

        if scope and scope != "me":
            label = SCOPE_LABELS.get(scope, scope.title())
            summary.append({"label": "Escopo", "value": label})

        companies = self._build_selection_summary(
            "Empresas", company_ids, options.get("companies") or [], "company_id", "company_name"
        )
        if companies:
            summary.append(companies)

        responsible = self._build_selection_summary(
            "Responsáveis",
            filters.get("responsible_ids"),
            options.get("collaborators") or [],
            "id",
            "name",
        )
        if responsible:
            summary.append(responsible)

        executor = self._build_selection_summary(
            "Executores",
            filters.get("executor_ids"),
            options.get("collaborators") or [],
            "id",
            "name",
        )
        if executor:
            summary.append(executor)

        projects = self._build_selection_summary(
            "Projetos",
            filters.get("project_ids"),
            options.get("projects") or [],
            "id",
            "title",
        )
        if projects:
            summary.append(projects)

        processes = self._build_selection_summary(
            "Processos",
            filters.get("process_ids"),
            options.get("processes") or [],
            "id",
            "title",
        )
        if processes:
            summary.append(processes)

        owners = self._ensure_list(filters.get("process_owner_ids"))
        if owners:
            summary.append(
                {
                    "label": "Donos de Processos",
                    "value": self._format_value_list(owners),
                }
            )

        delivery_tags = self._ensure_list(filters.get("delivery_tags"))
        if delivery_tags and set(delivery_tags) != set(DELIVERY_TAGS):
            values = [DELIVERY_TAG_LABELS.get(tag, tag) for tag in delivery_tags]
            summary.append({"label": "Entrega", "value": self._format_value_list(values)})

        due_start = filters.get("due_date_start")
        due_end = filters.get("due_date_end")
        if due_start or due_end:
            summary.append(
                {
                    "label": "Período",
                    "value": self._format_date_range(due_start, due_end),
                }
            )

        search = (filters.get("search") or "").strip()
        if search:
            summary.append({"label": "Busca", "value": search})

        quick_filter = (filters.get("filter") or "").lower()
        if quick_filter and quick_filter != "all":
            summary.append(
                {
                    "label": "Filtro rápido",
                    "value": FILTER_SHORTCUTS.get(quick_filter, quick_filter),
                }
            )

        types = self._ensure_list(filters.get("types"))
        if types:
            summary.append({"label": "Tipos", "value": self._format_value_list(types)})

        roles = self._ensure_list(filters.get("roles"))
        if roles:
            summary.append({"label": "Papéis", "value": self._format_value_list(roles)})

        return summary

    def _build_selection_summary(
        self,
        label: str,
        selected: Optional[Sequence[Any]],
        options: List[Dict[str, Any]],
        id_key: str,
        label_key: str,
    ) -> Optional[Dict[str, str]]:
        normalized = self._ensure_list(selected)
        values = self._map_ids_to_labels(normalized, options, id_key, label_key)
        if not values:
            return None
        available = [option.get(id_key) for option in options if option.get(id_key) is not None]
        if not self._should_show_selection(normalized, available):
            return None

        return {"label": label, "value": self._format_value_list(values)}

    def _map_ids_to_labels(
        self,
        selected: Optional[Sequence[Any]],
        options: List[Dict[str, Any]],
        id_key: str,
        label_key: str,
    ) -> List[str]:
        if not selected:
            return []
        mapping = {
            str(option.get(id_key)): (option.get(label_key) or "").strip()
            for option in options
            if option.get(id_key) is not None
        }
        results: List[str] = []
        seen = set()
        for value in selected:
            serialized = str(value).strip()
            if not serialized or serialized in seen:
                continue
            seen.add(serialized)
            label = mapping.get(serialized) or serialized
            results.append(label)
        return results

    def _should_show_selection(
        self, selected: Optional[Sequence[Any]], available: Sequence[Any]
    ) -> bool:
        if not selected:
            return False
        if not available:
            return True
        selected_set = {str(item).strip() for item in selected if item is not None}
        available_set = {str(item).strip() for item in available if item is not None}
        if not selected_set:
            return False
        if selected_set == available_set:
            return len(available_set) == 1
        return True

    def _format_value_list(self, values: Sequence[str]) -> str:
        normalized = [str(value).strip() for value in values if str(value).strip()]
        if not normalized:
            return ""
        unique = []
        seen = set()
        for entry in normalized:
            if entry in seen:
                continue
            seen.add(entry)
            unique.append(entry)
        if len(unique) <= MAX_SUMMARY_ITEMS:
            return ", ".join(unique)
        preview = unique[:MAX_SUMMARY_ITEMS]
        remaining = len(unique) - MAX_SUMMARY_ITEMS
        return f"{', '.join(preview)} e mais {remaining}"

    def _ensure_list(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    def _format_date_range(
        self, start: Optional[str], end: Optional[str]
    ) -> str:
        parts = []
        if start:
            parts.append(self._format_date(start))
        if end:
            parts.append(self._format_date(end))
        return " até ".join(parts) if parts else "Sem prazo"

    def _format_date(self, value: str) -> str:
        try:
            source = datetime.strptime(value, "%Y-%m-%d")
            return source.strftime("%d/%m/%Y")
        except Exception:
            return value

    def _resolve_user_name(self, user_id: int, override: Optional[str]) -> str:
        if override:
            sanitized = str(override).strip()
            if sanitized:
                return sanitized

        try:
            from models.user import User

            user = User.query.get(user_id)
            if user:
                candidate = user.name or user.email
                if candidate:
                    return str(candidate).strip()
        except Exception:
            pass

        return f"Usuário {user_id}"

    # =============================================
    # Atividades (cards)
    # =============================================

    def _format_activity_record(self, activity: Dict[str, Any]) -> str:
        kind = activity.get("type")
        if kind == "process":
            title = self._format_code_name(
                activity.get("process_code"), activity.get("process_name") or activity.get("title")
            )
            instance = self._format_code_name(activity.get("instance_code"), activity.get("title"))
            primary = f"Processo: {title}"
            secondary = f"Instância: {instance}"
        else:
            title = self._format_code_name(
                activity.get("project_code"), activity.get("project_title") or activity.get("plan_name")
            )
            secondary = self._format_code_name(activity.get("activity_code"), activity.get("title"))
            primary = f"Projeto: {title}"
            secondary = f"Atividade: {secondary}"

        responsible = self._resolve_responsible_name(activity)
        return f"{primary} | {secondary} | Responsável: {responsible}"

    def _format_code_name(self, code: Any, name: Any) -> str:
        parsed_code = str(code or "").strip()
        parsed_name = str(name or "").strip()
        if parsed_code and parsed_name:
            return f"{parsed_code} - {parsed_name}"
        if parsed_code:
            return parsed_code
        if parsed_name:
            return parsed_name
        return "Sem identificação"

    def _resolve_responsible_name(self, activity: Dict[str, Any]) -> str:
        sources = [
            activity.get("responsible_name"),
            activity.get("owner_name"),
            activity.get("process_owner_name"),
            activity.get("executor_name"),
        ]
        for entry in sources:
            if entry:
                return str(entry).strip()
        collaborator_value = self._extract_first_collaborator(activity)
        if collaborator_value:
            return collaborator_value
        return "Sem responsável definido"

    def _extract_first_collaborator(self, activity: Dict[str, Any]) -> Optional[str]:
        collaborators = activity.get("collaborators") or []
        if isinstance(collaborators, str):
            return collaborators.strip() or None
        for entry in collaborators:
            if isinstance(entry, dict):
                candidate = entry.get("name") or entry.get("full_name")
                if candidate:
                    return str(candidate).strip()
            elif isinstance(entry, str):
                sanitized = entry.strip()
                if sanitized:
                    return sanitized
        return None

    def _add_custom_styles(self) -> None:
        css = """
        .filters-summary {
            list-style: disc;
            padding-left: 1rem;
            font-size: 10pt;
            margin-bottom: 1rem;
        }

        .filter-section-title {
            font-weight: bold;
            margin-bottom: 0.4rem;
        }

        .indicator-table,
        .activity-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1rem;
            font-size: 10pt;
        }
        .indicator-table th,
        .indicator-table td,
        .activity-table th,
        .activity-table td {
            border: 1px solid #d1d5db;
            padding: 0.35rem 0.45rem;
        }

        .indicator-table td {
            width: 33%;
            background: #f9fafb;
        }

        .indicator-cell {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
            padding: 0.4rem 0;
        }

        .indicator-title {
            font-size: 0.75rem;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .indicator-number {
            font-size: 1.35rem;
            font-weight: 700;
        }

        .indicator-note {
            font-size: 0.7rem;
            color: #94a3b8;
        }

        .activity-table th {
            background: #f3f4f6;
        }

        .activity-table td {
            background: #ffffff;
        }

        .activity-count {
            font-size: 9pt;
            margin-top: 0;
        }
        """
        self.add_custom_style("my-work-report", css)
