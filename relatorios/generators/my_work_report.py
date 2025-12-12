#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de relatório inspirado na página My Work.

A partir dos filtros e dados que alimentam o dashboard, monta um resumo
com cabeçalho, indicadores e a listagem de cartões de atividades/processos.
"""

from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Sequence

from relatorios.generators.base import BaseReportGenerator
from services.my_work_service import (
    count_activities_by_scope,
    DELIVERY_TAGS,
    get_employee_from_user,
    get_filter_options,
    get_user_activities,
    get_user_stats,
    get_occurrences_summary,
    process_my_work_filters,
)

DELIVERY_TAG_LABELS = {"open": "Em aberto", "completed": "Concluídas"}
SCOPE_LABELS = {"me": "Minhas atividades", "team": "Equipe", "company": "Empresa"}
FILTER_SHORTCUTS = {
    "today": "Hoje",
    "week": "Semana atual",
    "overdue": "Apenas atrasadas",
}
STATUS_LABELS = {
    "pending": "Pendente",
    "in_progress": "Em andamento",
    "open": "Em aberto",
    "overdue": "Atrasada",
    "late": "Atrasada",
    "completed": "Concluída",
    "done": "Concluída",
    "cancelled": "Cancelada",
    "canceled": "Cancelada",
    "archived": "Arquivada",
    "blocked": "Bloqueada",
    "on_hold": "Em espera",
    "in_review": "Em revisão",
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
                    Página <span class="page-number"></span> de <span class="total-pages"></span>
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
        max_activities: Optional[int] = None,
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
            max_activities: Quantidade máxima de cards a mostrar. Se None ou 0,
                exibe todos os registros retornados pelos filtros.
        """
        # Preparar request_args_dict a partir dos parâmetros recebidos
        # A função compartilhada espera um dicionário como request.args
        request_args_dict = {}
        
        # Adicionar scope se fornecido
        if scope:
            request_args_dict["scope"] = scope
        
        # Adicionar company_id e company_ids se fornecidos
        if company_id:
            request_args_dict["company_id"] = str(company_id)
        if company_ids:
            request_args_dict["company_ids"] = ",".join(str(cid) for cid in company_ids)
        
        # Adicionar filtros fornecidos
        # IMPORTANTE: A página só envia filtros quando há uma seleção PARCIAL (não todos)
        # Se filters estiver vazio ou None, não adicionar nada (como a página faz)
        if filters:
            # Normalizar filtros que podem vir como strings da URL
            normalized_filters = self._normalize_filters(dict(filters))
            for key, value in normalized_filters.items():
                if value is None:
                    continue
                # Filtrar valores None de listas (como process_owner_ids: [null])
                if isinstance(value, (list, tuple)):
                    # Remover None/null da lista
                    clean_value = [v for v in value if v is not None]
                    if not clean_value:
                        continue
                    request_args_dict[key] = ",".join(str(v) for v in clean_value)
                elif isinstance(value, date):
                    request_args_dict[key] = value.strftime("%Y-%m-%d")
                else:
                    request_args_dict[key] = str(value)
        
        # Processar filtros usando função compartilhada (exatamente como a API faz)
        try:
            processed = process_my_work_filters(
                user_id,
                request_args_dict,
                SELECTION_MODE_NONE="none",
            )
        except ValueError as exc:
            raise ValueError(str(exc))
        
        # Se não houver empresas disponíveis, retornar dados vazios
        if processed["has_no_companies"]:
            self.data["user"] = {"name": self._resolve_user_name(user_id, user_name)}
            self.data["company"] = {"name": ""}
            self.data["filters_summary"] = []
            self.data["activities"] = []
            self.data["activities_total"] = 0
            self.data["all_activities"] = []
            self.data["stats"] = {"pending": 0, "in_progress": 0, "overdue": 0, "completed": 0}
            self.data["counts"] = {"me": 0, "team": 0, "company": 0}
            self.data["occurrences"] = {"positive": {"count": 0}, "negative": {"count": 0}}
            self.data["filters_payload"] = processed["filters"]
            return
        
        employee_id = processed["employee_id"]
        scope = processed["scope"]
        resolved_company_ids = processed["company_ids"]
        employee_ids_list = processed["employee_ids"]
        filters_payload = processed["filters"]
        
        # DEBUG: Log dos filtros processados
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"🔍 RELATÓRIO - Filtros processados - scope: {scope}, company_ids: {resolved_company_ids}, employee_ids: {employee_ids_list}, filters_keys: {list(filters_payload.keys())}"
        )

        resolved_user_name = self._resolve_user_name(user_id, user_name)
        self.data["user"] = {"name": resolved_user_name}
        
        filter_options = get_filter_options(user_id)
        
        # Usar exatamente os mesmos dados que a página My Work usa
        # A API /my-work/api/activities retorna activities e stats já calculados
        # IMPORTANTE: A ordem dos parâmetros deve ser exatamente como a API chama
        activities = get_user_activities(
            employee_id,
            scope,
            filters_payload,  # filters como terceiro parâmetro posicional (como a API faz)
            company_id=None,  # Não usar legado, usar apenas company_ids
            company_ids=resolved_company_ids,
            employee_ids=employee_ids_list,
        )
        stats = get_user_stats(
            employee_id,
            scope,
            company_id=None,  # Não usar legado, usar apenas company_ids
            company_ids=resolved_company_ids,
            filters=filters_payload,
            employee_ids=employee_ids_list,
        )
        counts = count_activities_by_scope(
            employee_id,
            company_id=None,  # Não usar legado, usar apenas company_ids
            company_ids=resolved_company_ids,
            filters=filters_payload,
            employee_ids=employee_ids_list,
        )
        
        # Buscar ocorrências (mesma chamada que a página faz)
        occurrences = get_occurrences_summary(
            employee_id,
            company_ids=resolved_company_ids,
            employee_ids=employee_ids_list,
        )

        # Exibir todos se max_activities não for definido ou for zero/negativo
        limit = len(activities) if not max_activities or max_activities <= 0 else max_activities
        preview_activities = activities[:limit]
        
        # Guardar todas as atividades para cálculos (como a página faz)
        self.data["all_activities"] = activities

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
        self.data["occurrences"] = occurrences
        self.data["filters_payload"] = filters_payload

    def build_sections(self) -> None:
        self.clear_sections()
        self.add_section("Filtros", self._render_filters_section(), section_class="filters-section")
        self.add_section("Indicadores", self._render_indicators_section(), section_class="indicators-section")
        self.add_section("Atividades e Instâncias", self._render_activities_section(), section_class="activities-section")

    # =============================================
    # Seções renderizadas
    # =============================================

    def _render_filters_section(self) -> str:
        summary = self.data.get("filters_summary") or []
        filters_payload = self.data.get("filters_payload") or {}
        
        # Se não houver summary construído, tentar mostrar informações básicas dos filtros
        if not summary:
            basic_info = []
            scope = filters_payload.get("scope", "me")
            if scope and scope not in ("me", "company"):
                label = SCOPE_LABELS.get(scope, scope.title())
                basic_info.append({"label": "Escopo", "value": label})
            
            # Verificar outros filtros comuns
            search = (filters_payload.get("search") or "").strip()
            if search:
                basic_info.append({"label": "Busca", "value": search})
            
            quick_filter = (filters_payload.get("filter") or "").lower()
            if quick_filter and quick_filter != "all":
                value = FILTER_SHORTCUTS.get(quick_filter, quick_filter)
                basic_info.append({"label": "Filtro rápido", "value": value})
            
            due_start = filters_payload.get("due_date_start")
            due_end = filters_payload.get("due_date_end")
            if due_start or due_end:
                date_range = self._format_date_range(due_start, due_end)
                basic_info.append({"label": "Período", "value": date_range})
            
            if basic_info:
                items = " | ".join(
                    f"<strong>{entry['label']}:</strong> {entry['value']}"
                    for entry in basic_info
                )
                return f"<p class='filters-summary'>{items}</p>"
            
            return "<p>Nenhum filtro específico foi aplicado.</p>"

        # Formato em linha horizontal com separadores "|"
        items = " | ".join(
            f"<strong>{entry['label']}:</strong> {entry['value']}"
            for entry in summary
        )
        return f"<p class='filters-summary'>{items}</p>"

    def _render_indicators_section(self) -> str:
        # Usar exatamente os mesmos dados que a página My Work usa
        stats = self.data.get("stats") or {}
        occurrences = self.data.get("occurrences") or {}
        all_activities = self.data.get("all_activities") or []

        # Calcular exatamente como a página faz (updateStats)
        # Em aberto = pending + in_progress (como updateStats faz)
        pending = int(stats.get("pending", 0) or 0)
        in_progress = int(stats.get("in_progress", 0) or 0)
        open_count = pending + in_progress
        
        # Atrasadas = overdue (como updateStats faz)
        overdue = int(stats.get("overdue", 0) or 0)
        
        # Performance Score e Taxa de Conclusão: calcular como a página (updateInsightCards)
        # A página usa filteredActivities (que são todas as atividades retornadas após filtros)
        # completedCount = atividades com status 'completed'
        def is_completed(activity):
            status = (activity.get("status") or "").lower()
            return status in ("completed", "done")
        
        total_activities = len(all_activities)
        completed_count = sum(1 for act in all_activities if is_completed(act))
        total_count = open_count + completed_count
        
        # Performance Score: formato "X de Y pts (Z.Z%)" - exatamente como updatePerformanceCard
        safe_total = max(0, total_activities)
        safe_completed = max(0, completed_count)
        if safe_total > 0:
            percent = (safe_completed / safe_total) * 100
            performance_display = f"{safe_completed} de {safe_total} pts ({percent:.1f}%)"
        else:
            performance_display = "0 de 0 pts (0.0%)"
        
        # Taxa de Conclusão: mesmo formato que Performance Score
        if safe_total > 0:
            completion_percent = (safe_completed / safe_total) * 100
            completion_display = f"{safe_completed} de {safe_total} pts ({completion_percent:.1f}%)"
        else:
            completion_display = "0 de 0 pts (0.0%)"
        
        # Ocorrências: formato "+X -Y = Z" (pontos positivos, negativos, resultado)
        positive_occ = int(occurrences.get("positive", {}).get("count", 0) or 0)
        negative_occ = int(occurrences.get("negative", {}).get("count", 0) or 0)
        occurrences_result = positive_occ - negative_occ
        occurrences_display = f"+{positive_occ} -{negative_occ} = {occurrences_result:+d}"

        # Criar células com os 5 indicadores
        indicators = [
            ("Em aberto", open_count),
            ("Atrasadas", overdue),
            ("Total", total_count),
            ("Ocorrências", occurrences_display),
            ("Performance Score", performance_display),
            ("Taxa de Conclusão", completion_display),
        ]
        
        cells = []
        for label, value in indicators:
            cells.append(
                f"""
                <td>
                    <div class="indicator-cell">
                        <div class="indicator-title">{label}</div>
                        <div class="indicator-number">{value}</div>
                    </div>
                </td>
                """
            )

        # Organizar em linhas de 3 colunas
        rows_html = ""
        for i in range(0, len(cells), 3):
            row_cells = cells[i : i + 3]
            while len(row_cells) < 3:
                row_cells.append("<td></td>")
            rows_html += f"<tr>{''.join(row_cells)}</tr>"

        displayed = len(self.data.get("activities") or [])
        preview_note = f"<p class='activity-count'>Mostrando {displayed} de {total_activities} registros.</p>"
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
            deadline_raw = activity.get("deadline")
            if deadline_raw:
                deadline = self._format_date(deadline_raw)
            else:
                deadline = "-"
            status = self._translate_status(activity.get("status"))
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

        # Sempre mostrar o escopo se não for "me"
        if scope and scope not in ("me", "company"):
            label = SCOPE_LABELS.get(scope, scope.title())
            summary.append({"label": "Escopo", "value": label})

        # Empresas - usar company_ids do parâmetro ou dos filtros
        effective_company_ids = company_ids
        if not effective_company_ids:
            effective_company_ids = self._ensure_list(filters.get("company_ids"))
        if not effective_company_ids:
            effective_company_ids = self._ensure_list(filters.get("company_id"))
        
        def _with_code(opts: List[Dict[str, Any]], code_key: str, name_key: str) -> List[Dict[str, Any]]:
            decorated = []
            for opt in opts or []:
                code = (opt.get(code_key) or "").strip() if isinstance(opt.get(code_key), str) else opt.get(code_key)
                name = opt.get(name_key) or ""
                label = f"{code}-{name}" if code else name
                decorated.append({**opt, name_key: label.strip()})
            return decorated

        companies_opts = _with_code(options.get("companies") or [], "company_code", "company_name")
        companies = self._build_selection_summary(
            "Empresas", effective_company_ids, companies_opts, "company_id", "company_name"
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

        projects_opts = _with_code(options.get("projects") or [], "code", "title")
        projects = self._build_selection_summary(
            "Projetos",
            filters.get("project_ids"),
            projects_opts,
            "id",
            "title",
        )
        if projects:
            summary.append(projects)

        processes_opts = _with_code(options.get("processes") or [], "code", "title")
        processes = self._build_selection_summary(
            "Processos",
            filters.get("process_ids"),
            processes_opts,
            "id",
            "title",
        )
        if processes:
            summary.append(processes)

        # Donos de Processos - só mostrar se houver opções disponíveis e filtros aplicados
        owners = self._ensure_list(filters.get("process_owner_ids"))
        if owners:
            # Verificar se há opções de process_owners disponíveis
            process_owners_options = options.get("process_owners") or options.get("processOwners") or []
            if process_owners_options:
                # Verificar se os IDs selecionados correspondem a opções válidas
                owner_labels = self._map_ids_to_labels(owners, process_owners_options, "id", "name")
                if owner_labels:
                    summary.append(
                        {
                            "label": "Donos de Processos",
                            "value": self._format_value_list(owner_labels),
                        }
                    )
            # Se não houver opções disponíveis, não mostrar o filtro (mesmo que tenha sido aplicado)

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

    def _normalize_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza filtros que podem vir como strings da URL JSON."""
        normalized = {}
        for key, value in filters.items():
            if value is None:
                continue
            # Se for string que parece JSON, tentar parsear
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    normalized[key] = parsed
                except (ValueError, TypeError):
                    normalized[key] = value
            else:
                normalized[key] = value
        return normalized

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

    def _translate_status(self, status_value: Any) -> str:
        raw = (status_value or "").strip()
        if not raw:
            return "-"
        key = raw.lower()
        translated = STATUS_LABELS.get(key)
        if translated:
            return translated
        return raw.title()


    def _add_custom_styles(self) -> None:
        css = """
        /* Margens de 5 mm em todos os lados */
        @page {
            margin: 5mm;
        }
        
        body {
            margin: 0; /* evitar acúmulo de margens externas */
        }
        
        .report-content {
            margin: 0;
            padding: 0 5mm;
            padding-top: calc(var(--report-header-offset) + 2mm);
            padding-bottom: calc(var(--report-footer-offset) + 2mm);
        }

        /* Espaços dedicados entre cabeçalho/rodapé e o conteúdo */
        .custom-report-header,
        .report-header {
            margin-bottom: 3mm;
        }

        .custom-report-footer,
        .report-footer {
            margin-top: 3mm;
        }

        /* Seções gerais */
        .report-section {
            margin-bottom: 8mm;
            page-break-inside: avoid;
        }

        .report-section h1 {
            font-size: 18px;
            line-height: 1.3;
            margin: 0 0 6px 0;
            padding: 0;
            page-break-after: avoid;
        }

        .report-section .section-content {
            page-break-inside: avoid;
        }

        /* Seções específicas */
        .report-section.activities-section {
            page-break-inside: auto;
            margin-bottom: 6mm;
        }

        .report-section.activities-section h1 {
            page-break-after: avoid;
        }

        .report-section.activities-section .section-content {
            page-break-inside: auto;
        }
        
        .filters-summary {
            font-size: 10pt;
            margin-bottom: 1rem;
            line-height: 1.5;
        }
        
        .filters-summary strong {
            font-weight: bold;
        }

        .filter-section-title {
            font-weight: bold;
            margin-bottom: 0.4rem;
        }

        .indicator-table,
        .activity-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 0.5rem;
            font-size: 10pt;
            border: 1px solid #d1d5db;
            page-break-inside: avoid;
        }
        .indicator-table th,
        .indicator-table td,
        .activity-table th,
        .activity-table td {
            border: 1px solid #d1d5db;
            padding: 0.35rem 0.45rem;
            page-break-inside: avoid;
        }

        .indicator-table td {
            width: 33%;
            background: #f9fafb;
            border: 1px solid #d1d5db;
        }
        
        .indicator-table tr {
            border: 1px solid #d1d5db;
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

        .activity-table th {
            background: #f3f4f6;
        }

        .activity-table td {
            background: #ffffff;
        }

        .activity-count {
            font-size: 9pt;
            margin-top: 2px;
            margin-bottom: 0;
        }

        /* Evitar quebras abruptas em linhas de tabela */
        .activity-table tr {
            page-break-inside: avoid;
        }
        """
        self.add_custom_style("my-work-report", css)
