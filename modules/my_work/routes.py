import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

"""
Rotas do Módulo My Work
APIs e páginas para gestão de atividades
"""

from flask import Response, render_template, jsonify, request, url_for, send_file
from flask_login import login_required, current_user
from . import my_work_bp
from services.my_work_service import (
    add_comment,
    add_work_hours,
    count_activities_by_scope,
    get_company_overview,
    get_employee_from_user,
    get_filter_options,
    get_occurrences_summary,
    get_team_overview,
    get_user_activities,
    get_user_employees,
    get_user_stats,
    complete_activity,
    process_my_work_filters,
    DELIVERY_TAGS,
)
from middleware.auto_log_decorator import auto_log_crud
from relatorios.generators.my_work_report import MyWorkReport, MyWorkReportCompact
from io import BytesIO
from openpyxl import Workbook

logger = logging.getLogger(__name__)

SELECTION_MODE_NONE = "none"


# ============================================================================
# PÃGINAS
# ============================================================================


@my_work_bp.route("/")
@login_required
def dashboard():
    """
    PÃ¡gina principal - My Work Dashboard
    """
    return render_template("my_work.html", active_nav="my_work")


@my_work_bp.route("/report")
@login_required
def my_work_report():
    """
    Gera o HTML simplificado do relatório inspirado na tela My Work.
    """
    scope = request.args.get("scope", "me")
    raw_filters = request.args.get("filters")
    filters_payload = {}
    if raw_filters:
        try:
            filters_payload = json.loads(raw_filters)
        except ValueError:
            filters_payload = {}

    raw_max = request.args.get("max")
    max_activities = None
    if raw_max is not None:
        try:
            parsed = int(raw_max)
            max_activities = parsed if parsed > 0 else None
        except ValueError:
            max_activities = None

    report = MyWorkReport()
    try:
        html = report.generate_html(
            user_id=current_user.id,
            user_name=current_user.name or current_user.email,
            scope=scope,
            filters=filters_payload,
            max_activities=max_activities,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("Erro ao gerar relatório My Work: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

    return Response(html, mimetype="text/html")


@my_work_bp.route("/report-compact")
@login_required
def my_work_report_compact():
    """
    Gera a versão compacta (v2) do relatório My Work.
    """
    scope = request.args.get("scope", "me")
    raw_filters = request.args.get("filters")
    filters_payload = {}
    if raw_filters:
        try:
            filters_payload = json.loads(raw_filters)
        except ValueError:
            filters_payload = {}

    raw_max = request.args.get("max")
    max_activities = None
    if raw_max is not None:
        try:
            parsed = int(raw_max)
            max_activities = parsed if parsed > 0 else None
        except ValueError:
            max_activities = None

    qs = request.query_string.decode("utf-8")
    query_suffix = f"?{qs}" if qs else ""
    export_links = {
        "pdf": url_for("my_work.my_work_report_compact_pdf") + query_suffix,
        "excel": url_for("my_work.my_work_report_compact_excel") + query_suffix,
    }

    report = MyWorkReportCompact()
    try:
        html = report.generate_html(
            user_id=current_user.id,
            user_name=current_user.name or current_user.email,
            scope=scope,
            filters=filters_payload,
            max_activities=max_activities,
            export_links=export_links,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("Erro ao gerar relatório My Work (compacto): %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

    return Response(html, mimetype="text/html")


@my_work_bp.route("/report-compact.pdf")
@login_required
def my_work_report_compact_pdf():
    scope = request.args.get("scope", "me")
    raw_filters = request.args.get("filters")
    filters_payload = {}
    if raw_filters:
        try:
            filters_payload = json.loads(raw_filters)
        except ValueError:
            filters_payload = {}

    raw_max = request.args.get("max")
    max_activities = None
    if raw_max is not None:
        try:
            parsed = int(raw_max)
            max_activities = parsed if parsed > 0 else None
        except ValueError:
            max_activities = None

    report = MyWorkReportCompact()
    try:
        report.fetch_data(
            user_id=current_user.id,
            user_name=current_user.name or current_user.email,
            scope=scope,
            filters=filters_payload,
            max_activities=max_activities,
        )
    except Exception as exc:
        logger.error("Erro ao buscar dados para PDF My Work: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

    activities = report.data.get("all_activities") or []
    filters_summary = report.data.get("filters_summary") or []
    metrics = report._compute_metrics()
    user_label = report.data.get("user", {}).get("name") or (current_user.name or current_user.email)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            BaseDocTemplate,
            PageTemplate,
            Frame,
            Paragraph,
            Table,
            TableStyle,
            Spacer,
        )
        from reportlab.pdfgen import canvas
    except Exception:
        return jsonify({"success": False, "error": "reportlab não está instalado. pip install reportlab"}), 500

    buffer = BytesIO()

    # Paginador: cabeçalho/rodapé com paginação e marca
    generated_at = datetime.now(timezone(timedelta(hours=-3)))
    timestamp = generated_at.strftime("%d/%m/%Y %H:%M")

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            self.user_label = user_label
            self.timestamp = timestamp
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_header_footer(page_count)
                super().showPage()
            super().save()

        def draw_header_footer(self, page_count):
            width, height = A4
            self.saveState()
            # Header
            self.setFont("Helvetica-Bold", 11)
            self.drawString(18, height - 24, "Gestão da Rotina")
            self.setFont("Helvetica", 9)
            self.drawRightString(width - 18, height - 24, f"Usuário: {self.user_label}")
            # Footer
            self.setFont("Helvetica", 8)
            self.drawString(18, 16, "Versus Gestão Corporativa - Todos os direitos reservados")
            self.drawRightString(width - 18, 16, f"Em: {self.timestamp} | Página {self._pageNumber} de {page_count}")
            self.restoreState()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18,
        rightMargin=18,
        topMargin=42,
        bottomMargin=32,
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )
    doc.addPageTemplates([PageTemplate(id="report", frames=frame)])

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="CellBold", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5))

    body = []

    # Filtros
    if filters_summary:
        filt_text = " | ".join(f"{entry.get('label')}: {entry.get('value')}" for entry in filters_summary)
    else:
        filt_text = "Sem filtros específicos"
    body.append(Paragraph(f"<b>Filtros:</b> {filt_text}", styles["Normal"]))
    body.append(Spacer(1, 8))

    # Indicadores
    perf_display = f"{int(metrics.get('performance_percent', 0))}%"
    occ_balance = int(metrics.get("occ_pos", 0)) - int(metrics.get("occ_neg", 0))
    indicators = [
        ["Abertas", "Atrasadas (em aberto)", "Concluídas", "Total", "Performance", "Ocorrências"],
        [
            int(metrics.get("open_count", 0)),
            int(metrics.get("overdue", 0)),
            int(metrics.get("completed", 0)),
            int(metrics.get("total", 0)),
            perf_display,
            occ_balance,
        ],
    ]
    t = Table(indicators, colWidths=[60, 60, 70, 60, 70, 70], repeatRows=0)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    body.append(t)
    body.append(Spacer(1, 12))

    # Tabela de atividades com quebra de linha nas células
    table_data = [
        [
            Paragraph("Tipo", styles["CellBold"]),
            Paragraph("Projeto / Processo", styles["CellBold"]),
            Paragraph("Atividade / Instância", styles["CellBold"]),
            Paragraph("Responsável", styles["CellBold"]),
            Paragraph("Prazo", styles["CellBold"]),
            Paragraph("Status", styles["CellBold"]),
        ]
    ]
    for activity in activities:
        kind = "Processo" if activity.get("type") == "process" else "Projeto"
        primary = report._format_code_name(
            activity.get("process_code") if kind == "Processo" else activity.get("project_code"),
            activity.get("process_name") or activity.get("title") if kind == "Processo" else activity.get("project_title") or activity.get("plan_name"),
        )
        secondary = report._format_code_name(
            activity.get("instance_code") if kind == "Processo" else activity.get("activity_code"),
            activity.get("title"),
        )
        responsible = report._resolve_responsible_name(activity)
        deadline_raw = activity.get("deadline")
        deadline = report._format_date(deadline_raw) if deadline_raw else "-"
        status = report._translate_status(activity.get("status"))
        table_data.append(
            [
                Paragraph(str(kind), styles["Cell"]),
                Paragraph(str(primary), styles["Cell"]),
                Paragraph(str(secondary), styles["Cell"]),
                Paragraph(str(responsible), styles["Cell"]),
                Paragraph(str(deadline), styles["Cell"]),
                Paragraph(str(status), styles["Cell"]),
            ]
        )

    col_widths = [55, 110, 110, 90, 60, 60]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ]
        )
    )
    body.append(table)

    try:
        doc.build(body, canvasmaker=NumberedCanvas)
    except Exception as exc:
        logger.error("Erro ao gerar PDF My Work com reportlab: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

    buffer.seek(0)
    filename = f"my-work-report-{scope}.pdf"
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@my_work_bp.route("/report-compact.xlsx")
@login_required
def my_work_report_compact_excel():
    scope = request.args.get("scope", "me")
    raw_filters = request.args.get("filters")
    filters_payload = {}
    if raw_filters:
        try:
            filters_payload = json.loads(raw_filters)
        except ValueError:
            filters_payload = {}

    raw_max = request.args.get("max")
    max_activities = None
    if raw_max is not None:
        try:
            parsed = int(raw_max)
            max_activities = parsed if parsed > 0 else None
        except ValueError:
            max_activities = None

    report = MyWorkReportCompact()
    try:
        report.fetch_data(
            user_id=current_user.id,
            user_name=current_user.name or current_user.email,
            scope=scope,
            filters=filters_payload,
            max_activities=max_activities,
        )
    except Exception as exc:
        logger.error("Erro ao buscar dados para Excel My Work: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

    activities = report.data.get("all_activities") or []
    filters_summary_raw = report.data.get("filters_summary") or []
    filters_summary = filters_summary_raw if isinstance(filters_summary_raw, list) else []
    metrics = report._compute_metrics()

    def _safe_int(value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    wb = Workbook()
    ws = wb.active
    ws.title = "Atividades"

    # Cabeçalho superior
    user_label = report.data.get("user", {}).get("name") or (current_user.name or current_user.email)
    ws.append(["Gestão da Rotina", "", "", "", f"Usuário: {user_label}"])
    ws.append([])

    # Resumo de filtros
    filt_text = "Sem filtros específicos"
    if filters_summary and isinstance(filters_summary, list):
        try:
            filt_text = " | ".join(f"{str(entry.get('label', '')).strip()}: {str(entry.get('value', '')).strip()}" for entry in filters_summary)
        except Exception:
            filt_text = "Sem filtros específicos"
    ws.append([f"Filtros: {filt_text}"])
    ws.append([])

    # Indicadores
    ws.append(["Abertas", "Atrasadas (em aberto)", "Concluídas", "Total", "Performance", "Ocorrências"])
    performance_display = f"{_safe_int(metrics.get('performance_percent', 0))}%"
    occ_balance = _safe_int(metrics.get("occ_pos", 0)) - _safe_int(metrics.get("occ_neg", 0))
    ws.append([
        _safe_int(metrics.get("open_count")),
        _safe_int(metrics.get("overdue")),
        _safe_int(metrics.get("completed")),
        _safe_int(metrics.get("total")),
        performance_display,
        occ_balance,
    ])
    ws.append([])

    # Dados das atividades
    ws.append(["Tipo", "Projeto / Processo", "Atividade / Instância", "Responsável", "Prazo", "Status"])
    for activity in activities:
        kind = "Processo" if activity.get("type") == "process" else "Projeto"
        primary = report._format_code_name(
            activity.get("process_code") if kind == "Processo" else activity.get("project_code"),
            activity.get("process_name") or activity.get("title") if kind == "Processo" else activity.get("project_title") or activity.get("plan_name"),
        )
        secondary = report._format_code_name(
            activity.get("instance_code") if kind == "Processo" else activity.get("activity_code"),
            activity.get("title"),
        )
        responsible = report._resolve_responsible_name(activity)
        deadline_raw = activity.get("deadline")
        deadline = report._format_date(deadline_raw) if deadline_raw else "-"
        status = report._translate_status(activity.get("status"))
        ws.append([
            str(kind),
            str(primary),
            str(secondary),
            str(responsible),
            str(deadline),
            str(status),
        ])

    output = BytesIO()
    try:
        wb.save(output)
    except Exception as exc:
        logger.error("Erro ao gerar Excel My Work: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

    output.seek(0)
    filename = f"my-work-report-{scope}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


# ============================================================================
# APIs - LISTAGEM
# ============================================================================


@my_work_bp.route("/api/companies/debug", methods=["GET"])
@login_required
def debug_user_companies():
    """Endpoint de debug para diagnosticar problema de empresas"""
    from models.user import User
    from models.employee import Employee
    from models.company import Company
    from models import db
    from database.postgres_helper import connect as pg_connect
    from sqlalchemy import func
    
    debug_info = {
        "user_id": current_user.id,
        "user_email": current_user.email,
        "employees_by_user_id": [],
        "employees_by_email_sqlalchemy": [],
        "employees_by_email_sql": [],
        "companies_found": []
    }
    
    # Buscar por user_id
    employees_by_user_id = Employee.query.filter_by(user_id=current_user.id).all()
    debug_info["employees_by_user_id"] = [
        {"id": e.id, "name": e.name, "email": e.email, "company_id": e.company_id, "user_id": e.user_id}
        for e in employees_by_user_id
    ]
    
    # Buscar por email com SQLAlchemy
    if current_user.email:
        employees_by_email = Employee.query.filter(
            func.lower(Employee.email) == current_user.email.lower()
        ).all()
        debug_info["employees_by_email_sqlalchemy"] = [
            {"id": e.id, "name": e.name, "email": e.email, "company_id": e.company_id, "user_id": e.user_id}
            for e in employees_by_email
        ]
        
        # Buscar por email com SQL direto
        conn = pg_connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, company_id, user_id 
            FROM employees 
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
        """, (current_user.email,))
        rows = cursor.fetchall()
        debug_info["employees_by_email_sql"] = [
            {"id": row[0], "name": row[1], "email": row[2], "company_id": row[3], "user_id": row[4]}
            for row in rows
        ]
        conn.close()
    
    # Buscar empresas
    all_employee_ids = set()
    for emp in employees_by_user_id:
        all_employee_ids.add(emp.id)
    for emp in employees_by_email if current_user.email else []:
        all_employee_ids.add(emp.id)
    
    for emp_id in all_employee_ids:
        emp = Employee.query.get(emp_id)
        if emp and emp.company_id:
            company = Company.query.get(emp.company_id)
            if company:
                debug_info["companies_found"].append({
                    "employee_id": emp.id,
                    "company_id": company.id,
                    "company_name": company.name
                })
    
    return jsonify(debug_info)


@my_work_bp.route("/api/companies", methods=["GET"])
@login_required
def get_user_companies():
    """
    API: Lista empresas vinculadas ao usuário
    """
    try:
        logger.info(f"🔍 API /api/companies chamada para user_id: {current_user.id}, email: {current_user.email}")
        companies = get_user_employees(current_user.id)
        
        logger.info(f"📊 Retornando {len(companies)} empresas para o frontend")
        for comp in companies:
            logger.info(f"   - {comp.get('company_name')} (ID: {comp.get('company_id')})")
        
        # Sempre retornar sucesso, mesmo se lista vazia
        # O frontend vai tratar lista vazia adequadamente
        response_data = {"success": True, "data": companies or []}
        logger.info(f"✅ Resposta da API: success={response_data['success']}, data_count={len(response_data['data'])}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ Erro ao buscar empresas do usuário {current_user.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Retornar lista vazia em caso de erro, não erro 500
        # Isso permite que o seletor apareça mesmo com erro
        return jsonify({
            "success": True, 
            "data": [],
            "error": str(e)  # Incluir erro para debug, mas não falhar
        })


@my_work_bp.route("/api/filter-options", methods=["GET"])
@login_required
def api_filter_options():
    """Return directories used by the filter dashboard."""
    try:
        data = get_filter_options(current_user.id)
        return jsonify({"success": True, "data": data})
    except Exception as exc:
        logger.error("Erro ao gerar opções de filtro: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@my_work_bp.route("/api/activities")
@login_required
def get_activities():
    """
    API: Lista de atividades conforme escopo

    Query Params:
        - scope: 'me', 'team' ou 'company'
        - filter: 'all', 'today', 'week', 'overdue'
        - search: texto de busca
        - sort: 'deadline', 'priority', 'status'
        - company_id: ID da empresa para filtrar (opcional)
        - company_ids: IDs das empresas para filtrar (separados por vírgula)
        
    Regras por role:
        - admin: vê todas as atividades de todas as empresas (se nenhuma empresa selecionada)
        - client: vê atividades de todos os usuários das empresas vinculadas
        - collaborator: vê apenas atividades atribuídas a ele
    """
    try:
        # Converter request.args para dicionário (a função compartilhada espera um dict)
        # request.args é um MultiDict, então precisamos converter corretamente
        request_args_dict = {}
        for key, value in request.args.items():
            # Se houver múltiplos valores, pegar o primeiro (como request.args.get faz)
            if isinstance(value, list) and len(value) > 0:
                request_args_dict[key] = value[0]
            else:
                request_args_dict[key] = value
        
        # Processar filtros usando função compartilhada
        try:
            processed = process_my_work_filters(
                current_user.id,
                request_args_dict,
                SELECTION_MODE_NONE=SELECTION_MODE_NONE,
            )
        except ValueError as exc:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": str(exc),
                    }
                ),
                404,
            )
        
        # Se não houver empresas disponíveis, retornar vazio
        if processed["has_no_companies"]:
            empty_stats = {"pending": 0, "in_progress": 0, "overdue": 0, "completed": 0}
            empty_counts = {"me": 0, "team": 0, "company": 0}
            return jsonify({"success": True, "data": [], "stats": empty_stats, "counts": empty_counts})
        
        employee_id = processed["employee_id"]
        scope = processed["scope"]
        company_ids = processed["company_ids"]
        employee_ids = processed["employee_ids"]
        filters = processed["filters"]
        
        # DEBUG: Log dos filtros recebidos
        logger.info(
            f"🔍 API - Filtros processados - scope: {scope}, company_ids: {company_ids}, employee_ids: {employee_ids}, filters_keys: {list(filters.keys())}"
        )

        # Buscar atividades
        activities = get_user_activities(
            employee_id,
            scope,
            filters,
            company_ids=company_ids,
            employee_ids=employee_ids,
        )

        # Buscar estatísticas
        stats = get_user_stats(
            employee_id,
            scope,
            company_id=None,
            company_ids=company_ids,
            filters=filters,
            employee_ids=employee_ids,
        )

        # Contadores das abas
        counts = count_activities_by_scope(
            employee_id,
            company_id=None,
            company_ids=company_ids,
            filters=filters,
            employee_ids=employee_ids,
        )

        # DEBUG: Log dos resultados
        logger.info(f"📊 Stats calculadas: {stats}")
        logger.info(f"🔢 Counts: {counts}")
        logger.info(f"📝 Total atividades retornadas: {len(activities)}")

        return jsonify(
            {"success": True, "data": activities, "stats": stats, "counts": counts}
        )

    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        logger.error(f"Erro ao buscar atividades: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@my_work_bp.route("/api/team-overview")
@login_required
def api_team_overview():
    """
    API: Dados do Team Overview
    
    Query Params:
        - company_id: ID da empresa para filtrar (opcional)
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        company_id = request.args.get("company_id", type=int)

        data = get_team_overview(employee_id, company_id)

        return jsonify({"success": True, "data": data})

    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@my_work_bp.route("/api/company-overview")
@login_required
def api_company_overview():
    """
    API: Dados executivos para Company Overview
    
    Query Params:
        - company_id: ID da empresa para filtrar (opcional)
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        company_id = request.args.get("company_id", type=int)

        data = get_company_overview(employee_id, company_id)

        return jsonify({"success": True, "data": data})

    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@my_work_bp.route("/api/occurrences/summary")
@login_required
def api_occurrences_summary():
    """Resumo de ocorrências para o card do My Work."""

    try:
        employee_id = get_employee_from_user(current_user.id)
        if employee_id is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Usuário não vinculado a um colaborador. Solicite ao administrador.",
                    }
                ),
                404,
            )

        def _parse_ints(raw_value: Optional[str]) -> List[int]:
            if not raw_value:
                return []
            values = []
            for chunk in raw_value.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                try:
                    values.append(int(chunk))
                except ValueError:
                    continue
            return values

        company_ids = _parse_ints(request.args.get("company_ids"))

        def _collect_employee_ids(primary_id: Optional[int]) -> List[int]:
            collected: List[int] = []
            if primary_id:
                collected.append(primary_id)

            try:
                companies = get_user_employees(current_user.id) or []
            except Exception as exc:  # pragma: no cover - defensivo
                logger.warning(
                    "Falha ao buscar colaboradores do usuário %s: %s",
                    current_user.id,
                    exc,
                )
                companies = []

            for company in companies:
                extra_id = company.get("employee_id")
                if extra_id and extra_id not in collected:
                    collected.append(extra_id)
            return collected

        employee_ids = _collect_employee_ids(employee_id)

        summary = get_occurrences_summary(
            employee_id,
            company_ids=company_ids,
            employee_ids=employee_ids,
        )
        return jsonify({"success": True, "data": summary})
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        logger.error("Erro ao obter resumo de ocorrências: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# APIs - AÇÕES
# ============================================================================


@login_required
@my_work_bp.route("/api/work-hours", methods=["POST"])
@login_required
@auto_log_crud("activity_work_log")
def api_add_work_hours():
    """
    API: Adicionar horas trabalhadas

    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "work_date": "2025-10-21",
            "hours": 2.5,
            "description": "..."
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)

        data = request.get_json()

        # ValidaÃ§Ãµes
        if not data:
            return jsonify({"success": False, "error": "Dados nÃ£o fornecidos"}), 400

        if "activity_type" not in data or "activity_id" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "activity_type e activity_id obrigatÃ³rios",
                    }
                ),
                400,
            )

        if "hours" not in data or data["hours"] <= 0:
            return (
                jsonify({"success": False, "error": "Horas devem ser maior que zero"}),
                400,
            )

        # Adicionar horas
        result = add_work_hours(
            employee_id,
            data["activity_type"],
            data["activity_id"],
            {
                "work_date": data.get("work_date", datetime.now().date().isoformat()),
                "hours": data["hours"],
                "description": data.get("description"),
            },
        )

        return jsonify({"success": True, "data": result, "message": result["message"]})

    except Exception as e:
        logger.info(f"Erro ao adicionar horas: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@my_work_bp.route("/api/comments", methods=["POST"])
@login_required
@auto_log_crud("activity_comment")
def api_add_comment():
    """
    API: Adicionar comentÃ¡rio em atividade

    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "comment_type": "note",
            "comment": "...",
            "is_private": false
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)

        data = request.get_json()

        # ValidaÃ§Ãµes
        if not data:
            return jsonify({"success": False, "error": "Dados nÃ£o fornecidos"}), 400

        if "activity_type" not in data or "activity_id" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "activity_type e activity_id obrigatÃ³rios",
                    }
                ),
                400,
            )

        if "comment" not in data or not data["comment"].strip():
            return (
                jsonify({"success": False, "error": "ComentÃ¡rio nÃ£o pode ser vazio"}),
                400,
            )

        # Adicionar comentÃ¡rio
        result = add_comment(
            employee_id,
            data["activity_type"],
            data["activity_id"],
            {
                "comment_type": data.get("comment_type", "note"),
                "comment": data["comment"],
                "is_private": data.get("is_private", False),
            },
        )

        return jsonify({"success": True, "data": result, "message": result["message"]})

    except Exception as e:
        logger.info(f"Erro ao adicionar comentÃ¡rio: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@my_work_bp.route("/api/complete", methods=["POST"])
@login_required
@auto_log_crud("activity")
def api_complete_activity():
    """
    API: Finalizar atividade

    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "completion_comment": "..." (opcional)
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)

        data = request.get_json()

        # ValidaÃ§Ãµes
        if not data:
            return jsonify({"success": False, "error": "Dados nÃ£o fornecidos"}), 400

        if "activity_type" not in data or "activity_id" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "activity_type e activity_id obrigatÃ³rios",
                    }
                ),
                400,
            )

        # Finalizar
        result = complete_activity(
            employee_id,
            data["activity_type"],
            data["activity_id"],
            {"completion_comment": data.get("completion_comment")},
        )

        return jsonify({"success": True, "data": result, "message": result["message"]})

    except Exception as e:
        logger.info(f"Erro ao finalizar atividade: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# APIs - DETALHAMENTO
# ============================================================================


@my_work_bp.route("/activity/<int:activity_id>")
@login_required
def view_project_activity(activity_id):
    """
    PÃ¡gina de detalhes da atividade de projeto
    """
    # TODO: Implementar pÃ¡gina de detalhamento
    return f"<h1>Detalhes da Atividade de Projeto #{activity_id}</h1><p>Em desenvolvimento...</p>"


@my_work_bp.route("/process-instance/<int:instance_id>")
@login_required
def view_process_instance(instance_id):
    """
    PÃ¡gina de detalhes da instÃ¢ncia de processo
    """
    # TODO: Implementar pÃ¡gina de detalhamento
    return f"<h1>Detalhes da InstÃ¢ncia de Processo #{instance_id}</h1><p>Em desenvolvimento...</p>"
