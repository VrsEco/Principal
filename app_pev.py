#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PEVAPP22 - Modular Application with Database Abstraction
Easy switching between different database backends
"""

import logging
import sys
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    abort,
    send_file,
    send_from_directory,
)
from config_database import get_db, db_config
from config import Config
from datetime import datetime, date
from flask import request, jsonify
from flask_login import current_user, login_required
from functools import wraps
import os

try:
    from dateutil import parser as _date_parser
except Exception:
    _date_parser = None
import os
import json
import re
from database.postgres_helper import connect as pg_connect
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple
from services.ai_service import ai_service

# models_db import moved to after init_app() call below
from werkzeug.routing import BuildError
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from database.postgresql_db import (
    ensure_integrations_tables,
    list_integrations,
    get_integration,
    create_integration,
    update_integration,
    delete_integration,
    set_agent_integrations,
    get_agent_integrations,
)
from utils.project_activity_utils import normalize_project_activities

try:
    from celery import Celery
except ImportError:
    Celery = None


def _force_utf8_stdio():
    """Ensure stdout/stderr accept UTF-8 even on cp1252 consoles."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


_force_utf8_stdio()

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "dev-secret-key-change-in-production"


def make_celery(flask_app):
    """Create Celery instance bound to the Flask app context."""
    if Celery is None:
        raise RuntimeError("Celery dependency is not installed.")

    broker_url = flask_app.config.get("CELERY_BROKER_URL")
    result_backend = flask_app.config.get("CELERY_RESULT_BACKEND")

    celery_app = Celery(
        flask_app.import_name, broker=broker_url, backend=result_backend
    )
    celery_app.conf.update(flask_app.config)

    class FlaskContextTask(celery_app.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return super().__call__(*args, **kwargs)

    celery_app.Task = FlaskContextTask
    return celery_app


# Configure encoding for proper UTF-8 handling
app.config["JSON_AS_ASCII"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True


# Decorador customizado para APIs que retorna JSON ao invés de redirect
def api_login_required(f):
    """Decorador para rotas API que retorna JSON 401 ao invés de redirecionar"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Não autenticado. Faça login novamente.",
                        "code": "AUTHENTICATION_REQUIRED",
                    }
                ),
                401,
            )
        return f(*args, **kwargs)

    return decorated_function


# Custom helper utilities
def ensure_routine_collaborators_sequence(cursor: Any) -> None:
    """Ensure routine_collaborators.id uses a PostgreSQL sequence."""
    cursor.execute(
        """
        SELECT column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'routine_collaborators'
          AND column_name = 'id'
        """
    )
    row = cursor.fetchone()
    column_default = row[0] if row else None

    if column_default and "nextval" in str(column_default):
        return

    cursor.execute("CREATE SEQUENCE IF NOT EXISTS routine_collaborators_id_seq")
    cursor.execute(
        """
        ALTER TABLE routine_collaborators
        ALTER COLUMN id SET DEFAULT nextval('routine_collaborators_id_seq')
        """
    )
    cursor.execute(
        """
        SELECT setval(
            'routine_collaborators_id_seq',
            COALESCE((SELECT MAX(id) FROM routine_collaborators), 0) + 1,
            false
        )
        """
    )
    try:
        cursor.fetchone()
    except Exception:
        pass
    cursor.execute(
        """
        ALTER SEQUENCE routine_collaborators_id_seq
        OWNED BY routine_collaborators.id
        """
    )


# Custom Jinja2 filter for parsing JSON
@app.template_filter("from_json")
def from_json_filter(json_string):
    """Parse JSON string to Python object"""
    try:
        if isinstance(json_string, str):
            # Remove any potential BOM or extra characters
            json_string = json_string.strip()
            if json_string.startswith("\ufeff"):
                json_string = json_string[1:]
            return json.loads(json_string)
        elif isinstance(json_string, dict):
            return json_string
        elif json_string is None:
            return {}
        else:
            return {}
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.info(f"Error parsing JSON: {e}, input: {json_string}")
        return {}


# Load configuration
app.config.from_object(Config)

if Celery is not None:
    try:
        celery = make_celery(app)
        logger.info("Celery inicializado com sucesso.")
    except Exception as celery_init_error:
        logger.info(f"Aviso: Celery não pôde ser inicializado: {celery_init_error}")
        celery = Celery(app.import_name, broker="memory://", backend="cache+memory://")
        celery.conf.update(task_always_eager=True)
else:
    Celery = None

logger = logging.getLogger(__name__)

# Initialize database and Flask-Login using models.init_app()
from models import init_app

db, login_manager, migrate = init_app(app)
models_db = db  # Alias for backward compatibility with existing code


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    try:
        from models.user import User

        return User.query.get(int(user_id))
    except Exception as exc:
        return None


# Register blueprints for PEV and GRV modules at import time
try:
    from modules.pev import pev_bp
    from modules.grv import grv_bp
    from modules.meetings import meetings_bp
    from modules.my_work import my_work_bp

    app.register_blueprint(pev_bp)
    app.register_blueprint(grv_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(my_work_bp)

    logger.info("[OK] My Work module registered at /my-work")
except Exception as _bp_err:
    logger.info("Aviso: Blueprints PEV/GRV/Meetings/MyWork não registrados:", _bp_err)
    # Expor detalhe no log para facilitar diagnóstico
    try:
        import traceback as _tb

        _tb.print_exc()
    except Exception:
        pass

# Import and register authentication and logs blueprints
try:
    from api.auth import auth_bp
    from api.logs import logs_bp
    from api.route_audit import route_audit_bp
    from middleware.audit_middleware import init_audit_middleware

    app.register_blueprint(auth_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(route_audit_bp)

    # Initialize audit middleware
    init_audit_middleware(app)

    logger.info("Sistema de logs de usuários integrado com sucesso!")
    logger.info("Sistema de auditoria de rotas integrado com sucesso!")
except Exception as e:
    logger.info(f"Aviso: Sistema de logs não integrado: {e}")


# Add custom Jinja2 filters
@app.template_filter("nl2br")
def nl2br(value):
    """Convert newlines to <br> tags"""
    if not value:
        return ""
    return value.replace("\n", "<br>")


# Favicon route to prevent 404 errors
@app.route("/favicon.ico")
def favicon():
    """Serve favicon from static folder"""
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


# === Admin Danger Zone: Purge all companies except Versus (defined after app init) ===
@app.route("/admin/purge/companies", methods=["POST"])
@login_required
def purge_companies_except_versus():
    try:
        # Role check
        if getattr(current_user, "role", None) != "admin":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Acesso negado: apenas administradores.",
                    }
                ),
                403,
            )

        # Environment guard
        allow_danger = os.environ.get("ALLOW_DANGEROUS_OPS", "false").lower() == "true"
        is_production = not app.config.get("DEBUG", False) and not app.config.get(
            "TESTING", False
        )
        if is_production and not allow_danger:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Operação desabilitada em produção. Defina ALLOW_DANGEROUS_OPS=true para habilitar.",
                    }
                ),
                403,
            )

        payload = request.get_json(silent=True) or {}
        password = payload.get("password")
        phrase = payload.get("phrase", "")
        expected_phrase = "APAGAR TUDO EXCETO VERSUS"

        # Password re-entry
        if not password or not current_user.check_password(password):
            return jsonify({"success": False, "message": "Senha inválida."}), 400

        # Typed phrase
        if phrase.strip().upper() != expected_phrase:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f'Digite a frase de confirmação: "{expected_phrase}"',
                    }
                ),
                400,
            )

        from models import company as company_model
        from models import plan as plan_model

        Company = company_model.Company
        Plan = plan_model.Plan
        db_session = models_db.session

        # Identify Versus company ids
        versus_id_env = os.environ.get("VERSUS_COMPANY_ID")
        versus_ids = set()
        if versus_id_env and str(versus_id_env).isdigit():
            versus_ids.add(int(versus_id_env))

        keep_companies = Company.query.filter(Company.name.ilike("versus%")).all()
        for c in keep_companies:
            versus_ids.add(c.id)

        if not versus_ids:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Empresa Versus não encontrada. Configure VERSUS_COMPANY_ID ou cadastre a empresa.",
                    }
                ),
                400,
            )

        # Delete plans (cascade) and companies not in Versus set
        to_delete_companies = Company.query.filter(
            ~Company.id.in_(list(versus_ids))
        ).all()

        deleted_plans = 0
        deleted_companies = 0
        for comp in to_delete_companies:
            comp_plans = Plan.query.filter(Plan.company_id == comp.id).all()
            for p in comp_plans:
                db_session.delete(p)
                deleted_plans += 1
            db_session.flush()
            db_session.delete(comp)
            deleted_companies += 1

        db_session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Dados excluídos com sucesso.",
                "deleted_companies": deleted_companies,
                "deleted_plans": deleted_plans,
                "kept_company_ids": list(versus_ids),
            }
        )
    except Exception as exc:
        try:
            models_db.session.rollback()
        except Exception:
            pass
        return (
            jsonify(
                {"success": False, "message": f"Erro ao executar limpeza: {str(exc)}"}
            ),
            500,
        )


# Formatting helpers for brazilian number display
_DECIMAL_STRIP_RE = re.compile(r"[^0-9,.-]")


def _to_decimal(value):
    # Convert incoming numeric-like values to Decimal
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        text_value = value.strip()
        if not text_value:
            return None
        cleaned = _DECIMAL_STRIP_RE.sub("", text_value)
        if not cleaned:
            return None
        if cleaned.count(",") == 1 and cleaned.rfind(",") > cleaned.rfind("."):
            normalized = cleaned.replace(".", "").replace(",", ".")
        else:
            normalized = cleaned.replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None
    return None


def _format_decimal_br(decimal_value: Decimal, decimals: int = 2) -> str:
    # Format Decimal values using brazilian separators
    decimals = max(0, int(decimals))
    quantize_pattern = "1" if decimals == 0 else "1." + ("0" * decimals)
    quantized = decimal_value.quantize(
        Decimal(quantize_pattern), rounding=ROUND_HALF_UP
    )
    formatted = f"{quantized:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("format_number_br")
def format_number_br(value, decimals: int = 2):
    # Format numbers with brazilian decimal notation
    decimal_value = _to_decimal(value)
    if decimal_value is None:
        return "-"
    return _format_decimal_br(decimal_value, decimals)


@app.template_filter("format_percent_br")
def format_percent_br(value, decimals: int = 2):
    # Format percentage values for brazilian notation
    decimal_value = _to_decimal(value)
    if decimal_value is None:
        return "-"
    return f"{_format_decimal_br(decimal_value, decimals)}%"


_CNPJ_DIGITS_RE = re.compile(r"\D")


@app.template_filter("format_cnpj")
def format_cnpj(value):
    # Format CNPJ identifiers using the standard mask
    if not value:
        return ""
    digits = _CNPJ_DIGITS_RE.sub("", str(value))
    if len(digits) != 14:
        return str(value)
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _calculate_financial_totals(financial_items):
    # Return total revenue and weighted average margin for financial entries
    total_revenue = Decimal("0")
    weighted_margin = Decimal("0")
    has_rows = False
    for item in financial_items or []:
        if not isinstance(item, dict):
            continue
        revenue_decimal = _to_decimal(item.get("revenue"))
        margin_decimal = _to_decimal(item.get("margin"))
        if revenue_decimal is None:
            continue
        has_rows = True
        total_revenue += revenue_decimal
        if margin_decimal is not None:
            weighted_margin += revenue_decimal * (margin_decimal / Decimal("100"))
    if not has_rows:
        return None, None
    average_margin = Decimal("0")
    if total_revenue > 0:
        average_margin = (weighted_margin / total_revenue) * Decimal("100")
    return total_revenue, average_margin


# Ensure upload folder exists
upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder, exist_ok=True)
process_flow_folder = os.path.join(upload_folder, "process_flows")
if not os.path.exists(process_flow_folder):
    os.makedirs(process_flow_folder, exist_ok=True)
process_activity_folder = os.path.join(upload_folder, "process_activities")
if not os.path.exists(process_activity_folder):
    os.makedirs(process_activity_folder, exist_ok=True)

PROCESS_FLOW_ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "svg", "gif", "webp"}
PROCESS_ACTIVITY_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "svg", "gif", "webp"}

# Get database instance
db = get_db()


# Utility functions
def _plan_for(plan_id):
    """Get plan and company data"""
    plan_identifier = int(plan_id)
    plan_data = db.get_plan_with_company(plan_identifier)
    if not plan_data:
        ensured = db.ensure_plan_seed(plan_identifier)
        if ensured:
            plan_data = db.get_plan_with_company(plan_identifier)

    if not plan_data:
        abort(404)

    plan = {
        "id": plan_data["id"],
        "name": plan_data["name"],
        "year": plan_data["year"],
        "status": plan_data["status"],
        "company": plan_data["company_name"],
        "company_id": plan_data["company_id"],
        "plan_mode": (plan_data.get("plan_mode") or "evolucao").lower(),
    }

    company = {"id": plan_data["company_id"], "name": plan_data["company_name"]}

    return plan, company


def _navigation(plan_id, active_section):
    """Generate navigation data"""
    return [
        {
            "id": "dashboard",
            "name": "Dashboard",
            "url": f"/plans/{plan_id}",
            "active": active_section == "dashboard",
        },
        {
            "id": "company",
            "name": "Dados da Organização",
            "url": f"/plans/{plan_id}/company",
            "active": active_section == "company",
        },
        {
            "id": "participants",
            "name": "Participantes",
            "url": f"/plans/{plan_id}/participants",
            "active": active_section == "participants",
        },
        {
            "id": "drivers",
            "name": "Direcionadores",
            "url": f"/plans/{plan_id}/drivers",
            "active": active_section == "drivers",
        },
        {
            "id": "okr-global",
            "name": "OKRs Globais",
            "url": f"/plans/{plan_id}/okr-global",
            "active": active_section == "okr-global",
        },
        {
            "id": "okr-area",
            "name": "OKRs de Área",
            "url": f"/plans/{plan_id}/okr-area",
            "active": active_section == "okr-area",
        },
        {
            "id": "projects",
            "name": "Projetos",
            "url": f"/plans/{plan_id}/projects",
            "active": active_section == "projects",
        },
        {
            "id": "reports",
            "name": "Relatórios",
            "url": f"/plans/{plan_id}/reports",
            "active": active_section == "reports",
        },
    ]


def _indicator_navigation(company_id: Optional[int]) -> List[Dict[str, Any]]:
    """Build navigation subset for indicator management sidebar."""
    try:
        from modules.grv import (
            grv_navigation,
        )  # Lazy import to avoid circular dependencies

        nav_groups = grv_navigation() or []
        for group in nav_groups:
            title = (group.get("title") or "").strip().lower()
            if "indicador" in title:
                return [group]
    except Exception as exc:
        logger.info(
            f"Error building indicator navigation for company {company_id}: {exc}"
        )
    return []


def _parse_datetime(value):
    """Parse various date/datetime inputs into a datetime object for templates"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    # Strings
    try:
        value = value.replace("Z", "+00:00")
    except AttributeError:
        pass
    try:
        return datetime.fromisoformat(value)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
    # Fallback to dateutil if available
    if _date_parser is not None:
        try:
            return _date_parser.parse(str(value))
        except Exception:
            return None
    return None


@app.template_filter("format_date_br")
def format_date_br(value, include_time: bool = False):
    dt = _parse_datetime(value)
    if not dt:
        return "-"
    return dt.strftime("%d/%m/%Y %H:%M") if include_time else dt.strftime("%d/%m/%Y")


def _extract_key_results_from_form(form, prefix="okr_kr_"):
    """Build key results payload from dynamic form fields"""
    indexes = []
    for key in form.keys():
        if key.startswith(prefix):
            remainder = key[len(prefix) :]
            if remainder.isdigit():
                indexes.append(int(remainder))
    key_results = []
    for index in sorted(set(indexes)):
        label = form.get(f"{prefix}{index}", "").strip()
        target = form.get(f"{prefix}{index}_target", "").strip()
        deadline = form.get(f"{prefix}{index}_deadline", "").strip()
        owner = form.get(f"{prefix}{index}_owner", "").strip()
        owner_id_raw = (form.get(f"{prefix}{index}_owner_id") or "").strip()
        indicator_id_raw = (form.get(f"{prefix}{index}_indicator_id") or "").strip()
        indicator_label = (form.get(f"{prefix}{index}_indicator_label") or "").strip()
        owner_id = int(owner_id_raw) if owner_id_raw.isdigit() else None
        indicator_id = int(indicator_id_raw) if indicator_id_raw.isdigit() else None
        if label:
            key_results.append(
                {
                    "label": label,
                    "target": target,
                    "deadline": deadline,
                    "owner_id": owner_id,
                    "owner": owner,
                    "indicator_id": indicator_id,
                    "indicator_label": indicator_label,
                    "position": len(key_results),
                }
            )
    return key_results


def _normalize_indicator_code_value(code: Optional[str]) -> str:
    """Normalize indicator code formatting for display purposes."""
    if not code:
        return ""
    return str(code).replace(".IND.", ".").strip()


def _load_company_indicators(company_id: int) -> List[Dict[str, Any]]:
    """Retrieve indicators for a company from the shared GRV database."""
    indicators: List[Dict[str, Any]] = []
    try:
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, code, name
            FROM indicators
            WHERE company_id = %s
            ORDER BY LOWER(COALESCE(code, '') || ' ' || name)
            """,
            (company_id,),
        )
        for row in cursor.fetchall():
            code = _normalize_indicator_code_value(row["code"])
            name = (row["name"] or "").strip()
            label_parts = [part for part in (code, name) if part]
            label = " - ".join(label_parts) if label_parts else "Indicador"
            indicators.append(
                {"id": row["id"], "code": code, "name": name, "label": label}
            )
        conn.close()
    except Exception as exc:
        logger.info(f"Error loading indicators for company {company_id}: {exc}")
    return indicators


def _build_participant_lookup(plan_id: int) -> Dict[str, Dict[str, Any]]:
    """Create a lookup of participants by ID for quick access to names and roles."""
    lookup: Dict[str, Dict[str, Any]] = {}
    try:
        participants = db.get_participants(int(plan_id))
        for participant in participants or []:
            participant_id = participant.get("id")
            if participant_id is None:
                continue
            lookup[str(participant_id)] = participant
    except Exception as exc:
        logger.info(f"Error building participant lookup for plan {plan_id}: {exc}")
    return lookup


def _build_indicator_lookup(company_id: Optional[int]) -> Dict[str, Dict[str, Any]]:
    """Create a lookup of indicators by ID for display metadata."""
    if company_id is None:
        return {}
    indicators = _load_company_indicators(company_id)
    return {str(indicator["id"]): indicator for indicator in indicators}


def _build_participant_context(
    plan_id: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Build participant options for templates and a simple name lookup."""
    options: List[Dict[str, Any]] = []
    name_lookup: Dict[str, str] = {}
    try:
        participants = db.get_participants(int(plan_id)) or []
        for participant in participants:
            participant_id = participant.get("id")
            if participant_id is None:
                continue
            participant_name = (participant.get("name") or "").strip() or "Participante"
            role = (participant.get("role") or "").strip()
            label_parts = [participant_name]
            if role:
                label_parts.append(role)
            participant_id_str = str(participant_id)
            options.append(
                {
                    "id": participant_id_str,
                    "name": participant_name,
                    "role": role,
                    "label": " - ".join(label_parts),
                }
            )
            name_lookup[participant_id_str] = participant_name
    except Exception as exc:
        logger.info(f"Error building participant context for plan {plan_id}: {exc}")
    return options, name_lookup


def _normalize_area_okr_payload(
    records: List[Dict[str, Any]],
    participant_lookup: Dict[str, str],
    indicator_lookup: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Normalize OKR payloads stored in section notes for consistent template consumption."""
    normalized_records: List[Dict[str, Any]] = []
    for record in records:
        item = dict(record)
        owner_id_val = item.get("owner_id")
        if owner_id_val is not None and owner_id_val != "":
            owner_id_str = str(owner_id_val)
            item["owner_id"] = owner_id_str
            owner_name = participant_lookup.get(owner_id_str)
            if owner_name:
                item["owner"] = owner_name
        else:
            item["owner_id"] = ""
        normalized_key_results: List[Dict[str, Any]] = []
        for kr in item.get("key_results", []):
            normalized_kr = dict(kr)
            kr_owner_id = normalized_kr.get("owner_id")
            if kr_owner_id is not None and kr_owner_id != "":
                kr_owner_str = str(kr_owner_id)
                normalized_kr["owner_id"] = kr_owner_str
                owner_name = participant_lookup.get(kr_owner_str)
                if owner_name and not normalized_kr.get("owner"):
                    normalized_kr["owner"] = owner_name
            else:
                normalized_kr["owner_id"] = ""
            indicator_id_val = normalized_kr.get("indicator_id")
            if indicator_id_val is not None and indicator_id_val != "":
                indicator_id_str = str(indicator_id_val)
                normalized_kr["indicator_id"] = indicator_id_str
                indicator_display = indicator_lookup.get(indicator_id_str)
                if indicator_display:
                    normalized_kr["indicator_display"] = indicator_display
            else:
                normalized_kr["indicator_id"] = ""
                if normalized_kr.get("indicator_label"):
                    normalized_kr["indicator_display"] = normalized_kr[
                        "indicator_label"
                    ]
            normalized_key_results.append(normalized_kr)
        item["key_results"] = normalized_key_results
        normalized_records.append(item)
    return normalized_records


def _load_directionals(plan_id: int):
    """Load consolidated directionals for a plan."""
    directionals = []

    # Prefer the dedicated directional_records table (new flow)
    try:
        raw_directionals = db.get_directional_records(plan_id) or []
    except Exception as exc:
        logger.info(f"Error fetching directional_records: {exc}")
        raw_directionals = []

    normalized = []
    seen_ids = set()
    allowed_statuses = {"approved", "final", "active", "consolidated"}

    for idx, directional in enumerate(raw_directionals):
        if not isinstance(directional, dict):
            continue
        status = (directional.get("status") or "").lower()
        if status and status not in allowed_statuses:
            continue

        title = directional.get("title") or directional.get("name") or ""
        description = (
            directional.get("description")
            or directional.get("insight")
            or directional.get("notes")
            or ""
        )
        if not title and not description:
            continue

        item = directional.copy()
        norm_id = (
            item.get("id")
            or item.get("directional_id")
            or item.get("uuid")
            or title
            or f"directional-{plan_id}-{idx}"
        )
        norm_id = str(norm_id)
        if norm_id in seen_ids:
            norm_id = f"{norm_id}-{idx}"
        seen_ids.add(norm_id)

        item["id"] = norm_id
        item["title"] = title or "Direcionador"
        item["insight"] = description
        item["description"] = description
        item["type"] = item.get("type") or item.get("category") or ""
        normalized.append(item)

    if normalized:
        return normalized

    # Legacy fallback: load from plan_sections storage
    status = db.get_section_status(plan_id, "directionals-approvals")
    if not status or not status.get("notes"):
        return directionals
    try:
        directionals_data = json.loads(status["notes"])
        raw_directionals = (
            directionals_data.get("directionals", [])
            if isinstance(directionals_data, dict)
            else []
        )
        if isinstance(raw_directionals, str):
            raw_directionals = json.loads(raw_directionals)
        if isinstance(raw_directionals, list):
            seen_ids.clear()
            for idx, directional in enumerate(raw_directionals):
                if not isinstance(directional, dict):
                    continue
                item = directional.copy()
                norm_id = (
                    item.get("id")
                    or item.get("directional_id")
                    or item.get("uuid")
                    or item.get("title")
                )
                if not norm_id:
                    norm_id = f"directional-{plan_id}-{idx}"
                norm_id = str(norm_id)
                if norm_id in seen_ids:
                    norm_id = f"{norm_id}-{idx}"
                seen_ids.add(norm_id)
                item["id"] = norm_id
                item["type"] = item.get("type") or item.get("category") or ""
                directionals.append(item)
    except Exception as exc:
        logger.info(f"Error loading directionals: {exc}")
    return directionals


def _okr_type_display(okr_type: str) -> str:
    return "Estruturante" if okr_type == "estruturante" else "Aceleracao"


def _has_directionals(plan_id: int) -> bool:
    return bool(_load_directionals(plan_id))


# Routes
@app.route("/")
def index():
    """Redirect to login page"""
    return redirect(url_for("login"))


# User logs system routes are handled by blueprints


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page and authentication - Unified login route with original design"""
    from services.auth_service import auth_service
    from flask_login import current_user

    if request.method == "GET":
        # If already logged in, redirect to main
        if current_user and current_user.is_authenticated:
            return redirect(url_for("main"))
        return render_template("login.html")

    elif request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get("email", "").strip()
            password = data.get("password", "")

            if not email or not password:
                return (
                    jsonify(
                        {"success": False, "message": "Email e senha são obrigatórios"}
                    ),
                    400,
                )

            # Authenticate user using auth_service
            user = auth_service.authenticate_user(email, password)

            if user:
                # Login user with session
                remember = data.get("remember", False)
                auth_service.login_user_session(user, remember=remember)

                return jsonify(
                    {
                        "success": True,
                        "message": "Login realizado com sucesso",
                        "user": user.to_dict(),
                        "redirect": url_for("main"),
                    }
                )
            else:
                return (
                    jsonify({"success": False, "message": "Email ou senha incorretos"}),
                    401,
                )

        except Exception as e:
            return (
                jsonify({"success": False, "message": f"Erro no login: {str(e)}"}),
                500,
            )


@app.route("/main")
@login_required
def main():
    """Ecossistema Versus - Página principal"""
    module_links = {}
    module_endpoints = {
        "pev": "pev.pev_dashboard",
        "grv": "grv.grv_dashboard",
    }

    for key, endpoint in module_endpoints.items():
        try:
            module_links[key] = url_for(endpoint)
        except BuildError as exc:
            logger.info(f"[WARN] Endpoint indisponivel '{endpoint}': {exc}")

    return render_template("ecosystem.html", module_links=module_links)


@app.route("/integrations")
@login_required
def integrations():
    """Página de Integrações e Serviços"""
    return render_template("integrations.html")


@app.route("/configs")
@login_required
def system_configs():
    """Página de Configurações do Sistema"""
    return render_template("configurations.html")


@app.route("/configs/system")
@login_required
def system_configs_system():
    """Central de Sistema e Auditoria dentro das configurações"""
    from services.route_audit_service import route_audit_service
    from services.log_service import log_service
    from datetime import datetime, timedelta

    # Obter estatísticas de auditoria de rotas
    try:
        audit_summary = route_audit_service.get_audit_summary()
    except Exception as exc:
        audit_summary = {
            "total_routes": 0,
            "routes_with_logging": 0,
            "routes_without_logging": 0,
            "coverage_percentage": 0,
        }

    # Obter estatísticas de logs
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        log_stats = log_service.get_log_stats(start_date=start_date, end_date=end_date)
    except Exception as exc:
        log_stats = {"total_logs": 0, "actions": {}, "entities": {}, "top_users": {}}

    return render_template(
        "configs_system.html", audit_summary=audit_summary, log_stats=log_stats
    )


@app.route("/configs/system/audit")
@login_required
def system_configs_audit():
    """Página de Auditoria de Rotas dentro das configurações"""
    # Apenas administradores podem acessar
    if current_user.role != "admin":
        flash("Acesso negado. Apenas administradores podem acessar.", "error")
        return redirect(url_for("system_configs"))

    return render_template("configs_system_audit.html")


@app.route("/configs/ai")
@login_required
def system_configs_ai():
    """Central de Inteligência Artificial dentro das configurações"""
    db = get_db()
    companies = db.get_companies()

    companies_with_plans = []
    for company in companies:
        plans = db.get_plans_by_company(company["id"])
        company_with_plans = company.copy()
        company_with_plans["plans"] = [
            {"id": plan["id"], "name": plan["name"]} for plan in plans
        ]
        companies_with_plans.append(company_with_plans)

    highlights = [
        {"title": "Planejamentos Ativos", "value": "3", "trend": "+1"},
        {"title": "Participantes", "value": "15", "trend": "+3"},
        {"title": "Projetos em Andamento", "value": "8", "trend": "+2"},
    ]

    timeline = [
        {
            "date": "2025-01-15",
            "event": "Início do planejamento estratégico",
            "status": "completed",
        },
        {
            "date": "2025-02-01",
            "event": "Entrevistas com participantes",
            "status": "in_progress",
        },
        {
            "date": "2025-03-15",
            "event": "Definição de direcionadores",
            "status": "pending",
        },
        {
            "date": "2025-04-30",
            "event": "Aprovação final do plano",
            "status": "pending",
        },
    ]

    return render_template(
        "plan_selector.html",
        user_name="Fabiano Ferreira",
        companies=companies_with_plans,
        highlights=highlights,
        timeline=timeline,
        show_ai_only=True,
    )


# Sistema de relatórios complexo removido - usando sistema simplificado

# ========================================
# SETTINGS ROUTES FOR REPORT SYSTEM
# ========================================


@app.route("/settings/reports")
@login_required
def settings_reports():
    """Página de configurações de relatórios"""
    try:
        from modules.report_models import ReportModelsManager

        # Inicializa o gerenciador de modelos
        manager = ReportModelsManager()

        # Busca todos os modelos salvos
        raw_models = manager.get_all_models()

        # Transforma os dados para o formato esperado pelo template
        page_styles = []
        for model in raw_models:
            if model:  # Verifica se o modelo não é None
                # Garante que os valores de margem sejam números válidos
                margin_top = model.get("margin_top")
                margin_right = model.get("margin_right")
                margin_bottom = model.get("margin_bottom")
                margin_left = model.get("margin_left")

                # Converte para int se necessário e aplica valores padrão
                try:
                    margin_top = int(margin_top) if margin_top is not None else 20
                    margin_right = int(margin_right) if margin_right is not None else 15
                    margin_bottom = (
                        int(margin_bottom) if margin_bottom is not None else 15
                    )
                    margin_left = int(margin_left) if margin_left is not None else 20
                except (ValueError, TypeError):
                    margin_top = 20
                    margin_right = 15
                    margin_bottom = 15
                    margin_left = 20

                # Cria o objeto margins no formato esperado
                margins = {
                    "top": margin_top,
                    "right": margin_right,
                    "bottom": margin_bottom,
                    "left": margin_left,
                }

                # Garante que header_height e footer_height sejam números válidos
                header_height = model.get("header_height")
                footer_height = model.get("footer_height")

                try:
                    header_height = (
                        int(header_height) if header_height is not None else 25
                    )
                    footer_height = (
                        int(footer_height) if footer_height is not None else 12
                    )
                except (ValueError, TypeError):
                    header_height = 25
                    footer_height = 12

                # Cria o objeto sections (pode ser vazio por enquanto)
                sections = ["Introdução", "Dados", "Conclusões"]  # Seções padrão

                # Gera código do modelo
                model_code = f"MODEL_{model.get('id', 'N/A')}"

                # Monta o objeto no formato esperado
                formatted_model = {
                    "id": model.get("id"),
                    "name": model.get("name", "Sem nome"),
                    "description": model.get("description", "Sem descrição"),
                    "code": model_code,
                    "paper_size": model.get("paper_size", "A4"),
                    "orientation": model.get("orientation", "Retrato"),
                    "margins": margins,
                    "header_height": header_height,
                    "footer_height": footer_height,
                    "sections": sections,
                }

                page_styles.append(formatted_model)

        return render_template("report_settings.html", page_styles=page_styles)

    except Exception as e:
        logger.info(f"Erro ao carregar página de configurações de relatórios: {e}")
        # Retorna página com lista vazia em caso de erro
        return render_template("report_settings.html", page_styles=[])


# ========================================
# API ROUTES FOR REPORT SYSTEM
# ========================================


@app.route("/api/reports/preview", methods=["POST"])
@login_required
def api_report_preview():
    """Gera preview de relatório com base no modelo e dados fictícios"""
    try:
        from modules.report_generator import ReportGenerator

        data = request.get_json() or {}
        model_config = data.get("model_config", {})
        model_id = data.get("model_id")

        generator = ReportGenerator()
        html_preview = generator.generate_html_preview(model_config, model_id)

        return jsonify({"success": True, "html_preview": html_preview})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/generate", methods=["POST"])
@login_required
def api_report_generate():
    """Gera PDF do relatório com base no modelo e dados fictícios"""
    try:
        from modules.report_generator import ReportGenerator

        data = request.get_json() or {}
        model_config = data.get("model_config", {})
        model_id = data.get("model_id")

        generator = ReportGenerator()
        pdf_path = generator.generate_pdf_report(model_config, model_id)

        # Cria URL de download
        download_url = f"/api/reports/download/{os.path.basename(pdf_path)}"

        return jsonify(
            {"success": True, "download_url": download_url, "file_path": pdf_path}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/download/<filename>")
@login_required
def api_report_download(filename):
    """Download de arquivo de relatório gerado"""
    try:
        reports_dir = os.path.join(os.getcwd(), "temp_pdfs")
        return send_from_directory(reports_dir, filename, as_attachment=True)
    except Exception as e:
        abort(404)


@app.route("/api/reports/models", methods=["POST"])
@login_required
def api_save_report_model():
    """Salva um novo modelo de relatório"""
    try:
        from modules.report_models import ReportModelsManager

        data = request.get_json() or {}
        manager = ReportModelsManager()
        model_id = manager.save_model(data)

        return jsonify({"success": True, "model_id": model_id})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/models/<int:model_id>", methods=["GET"])
@login_required
def api_get_report_model(model_id):
    """Busca um modelo de relatório pelo ID"""
    try:
        from modules.report_models import ReportModelsManager

        manager = ReportModelsManager()
        model = manager.get_model(model_id)

        if model:
            # Formata os dados para o formato esperado pelo JavaScript
            formatted_model = {
                "id": model.get("id"),
                "name": model.get("name", "Sem nome"),
                "description": model.get("description", "Sem descrição"),
                "paper_size": model.get("paper_size", "A4"),
                "orientation": model.get("orientation", "Retrato"),
                "margins": {
                    "top": model.get("margin_top", 20),
                    "right": model.get("margin_right", 15),
                    "bottom": model.get("margin_bottom", 15),
                    "left": model.get("margin_left", 20),
                },
                "header": {
                    "height": model.get("header_height", 25),
                    "rows": model.get("header_rows", 2),
                    "columns": model.get("header_columns", 3),
                    "content": model.get("header_content", ""),
                },
                "footer": {
                    "height": model.get("footer_height", 12),
                    "rows": model.get("footer_rows", 1),
                    "columns": model.get("footer_columns", 2),
                    "content": model.get("footer_content", ""),
                },
            }

            return jsonify({"success": True, "model": formatted_model})
        else:
            return jsonify({"success": False, "error": "Model not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/models/<int:model_id>", methods=["PUT"])
@login_required
def api_update_report_model(model_id):
    """Atualiza um modelo de relatório existente"""
    try:
        from modules.report_models import ReportModelsManager

        data = request.get_json() or {}
        manager = ReportModelsManager()
        result = manager.update_model(model_id, data)

        if result:
            return jsonify(
                {
                    "success": True,
                    "message": "Model updated successfully",
                    "model_id": model_id,
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to update model"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/models/<int:model_id>/conflicts", methods=["GET"])
@login_required
def api_check_model_conflicts(model_id):
    """Verifica conflitos de um modelo (relatórios associados)"""
    try:
        from modules.report_models import ReportModelsManager

        manager = ReportModelsManager()
        conflicts = manager.check_conflicts(model_id)

        return jsonify({"success": True, "conflicts": conflicts})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reports/models/<int:model_id>", methods=["DELETE"])
@login_required
def api_delete_report_model(model_id):
    """Exclui um modelo de relatório"""
    try:
        from modules.report_models import ReportModelsManager

        manager = ReportModelsManager()
        result = manager.delete_model(model_id)

        if result:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to delete model"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ROTAS PARA SISTEMA DE TEMPLATES DE RELATÓRIOS
# ============================================================================


@app.route("/report-templates")
@login_required
def report_templates_manager():
    """Página de gerenciamento de templates de relatórios"""
    return render_template("report_templates_manager.html")


@app.route("/api/report-templates", methods=["GET"])
@login_required
def api_get_report_templates():
    """Lista todos os templates de relatórios"""
    try:
        from modules.report_templates import ReportTemplatesManager

        manager = ReportTemplatesManager()
        templates = manager.get_all_templates()

        return jsonify(templates)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/report-templates", methods=["POST"])
@login_required
def api_create_report_template():
    """Cria um novo template de relatório"""
    try:
        from modules.report_templates import ReportTemplatesManager

        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        # Validação dos campos obrigatórios
        required_fields = ["name", "report_type", "page_config_id"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Campo obrigatório: {field}"}), 400

        # Converte page_config_id para int
        try:
            data["page_config_id"] = int(data["page_config_id"])
        except (ValueError, TypeError):
            return jsonify({"error": "page_config_id deve ser um número"}), 400

        manager = ReportTemplatesManager()
        template_id = manager.save_template(data)

        return jsonify({"success": True, "template_id": template_id})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report-templates/<int:template_id>", methods=["GET"])
@login_required
def api_get_report_template(template_id):
    """Busca um template específico"""
    try:
        from modules.report_templates import ReportTemplatesManager

        manager = ReportTemplatesManager()
        template = manager.get_template(template_id)

        if template:
            return jsonify(template)
        else:
            return jsonify({"error": "Template não encontrado"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/report-templates/<int:template_id>", methods=["PUT"])
@login_required
def api_update_report_template(template_id):
    """Atualiza um template existente"""
    try:
        from modules.report_templates import ReportTemplatesManager

        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        manager = ReportTemplatesManager()
        result = manager.update_template(template_id, data)

        if result.get("success"):
            return jsonify({"success": True})
        else:
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "unknown_error")}
                ),
                400,
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report-templates/<int:template_id>", methods=["DELETE"])
@login_required
def api_delete_report_template(template_id):
    """Exclui um template"""
    try:
        from modules.report_templates import ReportTemplatesManager

        manager = ReportTemplatesManager()
        result = manager.delete_template(template_id)

        if result.get("success"):
            return jsonify({"success": True})
        else:
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "unknown_error")}
                ),
                400,
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report-templates/<int:template_id>/generate", methods=["POST"])
@login_required
def api_generate_report_from_template(template_id):
    """Gera um relatório usando um template específico"""
    try:
        from modules.report_templates import ReportTemplateGenerator

        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        generator = ReportTemplateGenerator()
        result = generator.generate_report_from_template(
            template_id, data.get("data_context", {})
        )

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        return jsonify(
            {
                "success": True,
                "html": result["html"],
                "template_name": result["template_name"],
                "page_config_name": result["page_config_name"],
                "report_type": result["report_type"],
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report-templates/by-type/<report_type>", methods=["GET"])
@login_required
def api_get_templates_by_type(report_type):
    """Lista templates por tipo de relatório"""
    try:
        from modules.report_templates import ReportTemplatesManager

        manager = ReportTemplatesManager()
        templates = manager.get_templates_by_type(report_type)

        return jsonify(templates)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports/models", methods=["GET"])
@login_required
def api_get_report_models():
    """Lista todas as configurações de página"""
    try:
        from modules.report_models import ReportModelsManager

        manager = ReportModelsManager()
        models = manager.get_all_models()

        return jsonify(models)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/companies")
@login_required
def companies_page():
    """Lista de empresas"""
    companies = db.get_companies()
    return render_template("companies.html", companies=companies)


@app.route("/companies/new")
@login_required
def companies_new():
    """Formulário de nova empresa"""
    return render_template("company_form.html", form_mode="create", company_data=None)


@app.route("/companies/<int:company_id>")
@login_required
def company_details(company_id: int):
    """Página de detalhes e gerenciamento completo da empresa com abas"""
    company_data = db.get_company(company_id)
    if not company_data:
        abort(404)
    return render_template("company_details.html", company=company_data)


@app.route("/companies/<int:company_id>/edit")
@login_required
def companies_edit(company_id: int):
    """Formulário de editar empresa (mantido para compatibilidade)"""
    company_data = db.get_company(company_id)
    if not company_data:
        abort(404)
    return render_template(
        "company_form.html", form_mode="edit", company_data=company_data
    )


@app.route("/companies/<int:company_id>/logos")
@login_required
def company_logos_manager(company_id: int):
    """Página de gerenciamento de logos da empresa"""
    from utils.logo_processor import get_all_logo_configs

    company_data = db.get_company(company_id)
    if not company_data:
        abort(404)

    logo_configs = get_all_logo_configs()

    return render_template(
        "company_logos_manager.html", company=company_data, logo_configs=logo_configs
    )


@app.route("/api/companies/<int:company_id>/logos", methods=["POST"])
@login_required
def api_upload_company_logo(company_id: int):
    """Upload de logo da empresa"""
    from utils.logo_processor import resize_and_save_logo, init_logo_folders

    try:
        # Verificar se empresa existe
        company = db.get_company(company_id)
        if not company:
            return jsonify({"success": False, "error": "Empresa não encontrada"}), 404

        # Verificar se arquivo foi enviado
        if "logo" not in request.files:
            return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

        file = request.files["logo"]
        if file.filename == "":
            return (
                jsonify({"success": False, "error": "Nenhum arquivo selecionado"}),
                400,
            )

        # Verificar tipo de logo
        logo_type = request.form.get("logo_type")
        if not logo_type or logo_type not in [
            "square",
            "vertical",
            "horizontal",
            "banner",
        ]:
            return jsonify({"success": False, "error": "Tipo de logo inválido"}), 400

        # Processar e salvar logo
        init_logo_folders()
        logo_path = resize_and_save_logo(file, company_id, logo_type)

        # Atualizar banco de dados
        field_name = f"logo_{logo_type}"
        conn = pg_connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE companies SET " + field_name + " = %s WHERE id = %s",
            (logo_path, company_id),
        )
        conn.commit()
        conn.close()

        return jsonify(
            {
                "success": True,
                "message": "Logo enviada com sucesso",
                "logo_path": logo_path,
                "logo_url": f"/{logo_path}",
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.info(f"Erro ao fazer upload de logo: {e}")
        return jsonify({"success": False, "error": "Erro ao processar logo"}), 500


@app.route("/api/companies/<int:company_id>/logos/<logo_type>", methods=["DELETE"])
@login_required
def api_delete_company_logo(company_id: int, logo_type: str):
    """Deletar logo da empresa"""
    from utils.logo_processor import delete_logo

    try:
        # Verificar tipo de logo
        if logo_type not in ["square", "vertical", "horizontal", "banner"]:
            return jsonify({"success": False, "error": "Tipo de logo inválido"}), 400

        # Buscar empresa
        company = db.get_company(company_id)
        if not company:
            return jsonify({"success": False, "error": "Empresa não encontrada"}), 404

        # Obter caminho da logo
        field_name = f"logo_{logo_type}"
        logo_path = company.get(field_name)

        # Deletar arquivo
        if logo_path:
            delete_logo(logo_path)

        # Atualizar banco de dados
        conn = pg_connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE companies SET " + field_name + " = NULL WHERE id = %s",
            (company_id,),
        )
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Logo removida com sucesso"})

    except Exception as e:
        logger.info(f"Erro ao deletar logo: {e}")
        return jsonify({"success": False, "error": "Erro ao deletar logo"}), 500


@app.route("/dashboard")
@login_required
def dashboard():
    # Preserve legacy route: redirect to PEV module dashboard
    return redirect("/pev/dashboard")


@app.route("/api/plans/<int:plan_id>/company-data", methods=["GET"])
@login_required
def api_get_company_data(plan_id: int):
    """Return minimal company data (mission, vision, values) for a plan"""
    try:
        company_data_row = db.get_company_data(int(plan_id)) or {}
        return jsonify(
            {
                "success": True,
                "data": {
                    "mission": company_data_row.get("mission") or "",
                    "vision": company_data_row.get("vision") or "",
                    "values": company_data_row.get("company_values") or "",
                    "grv_mvv_in_use": bool(company_data_row.get("grv_mvv_in_use")),
                },
            }
        )
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/plans/<int:plan_id>/company-data", methods=["POST"])
@login_required
def api_update_company_data(plan_id: int):
    """Update company data fields (mission, vision, values)"""
    try:
        payload = request.get_json(silent=True) or {}
        data = {
            "mission": payload.get("mission", ""),
            "vision": payload.get("vision", ""),
            "company_values": payload.get("values", ""),
            "grv_mvv_in_use": 1 if payload.get("grv_mvv_in_use") else 0,
        }
        if db.update_company_data(int(plan_id), data):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "update_failed"}), 400
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/mvv", methods=["GET"])
@login_required
def api_get_company_mvv(company_id: int):
    try:
        company = db.get_company(company_id)
        if not company:
            return jsonify({"success": False, "error": "not_found"}), 404
        return jsonify(
            {
                "success": True,
                "data": {
                    "mission": company.get("mvv_mission") or "",
                    "vision": company.get("mvv_vision") or "",
                    "values": company.get("mvv_values") or "",
                },
            }
        )
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/mvv", methods=["POST"])
@login_required
def api_update_company_mvv(company_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        ok = db.update_company_mvv(
            company_id,
            payload.get("mission", ""),
            payload.get("vision", ""),
            payload.get("values", ""),
        )
        if ok:
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "update_failed"}), 400
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/economic", methods=["POST"])
@login_required
def api_update_company_economic(company_id: int):
    """Update company economic data"""
    conn = None
    try:
        payload = request.get_json(silent=True) or {}

        def _clean(value):
            if value is None:
                return None
            if isinstance(value, str):
                value = value.strip()
                return value or None
            return value

        conn = pg_connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE companies SET
                cnpj = %s,
                city = %s,
                state = %s,
                cnaes = %s,
                coverage_physical = %s,
                coverage_online = %s,
                experience_total = %s,
                experience_segment = %s
            WHERE id = %s
        """,
            (
                _clean(payload.get("cnpj")),
                _clean(payload.get("city")),
                _clean(payload.get("state")),
                _clean(payload.get("cnaes")),
                _clean(payload.get("coverage_physical")),
                _clean(payload.get("coverage_online")),
                _clean(payload.get("experience_total")),
                _clean(payload.get("experience_segment")),
                company_id,
            ),
        )

        conn.commit()

        return jsonify({"success": True})
    except Exception as _err:
        if conn:
            conn.rollback()
        logger.info(f"Error updating economic data: {_err}")
        return jsonify({"success": False, "error": str(_err)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/companies", methods=["POST"])
@login_required
def api_create_company():
    """Create new company"""
    try:
        payload = request.get_json(silent=True) or {}

        name = (payload.get("name") or "").strip()
        if not name:
            return (
                jsonify({"success": False, "error": "Nome da empresa é obrigatório"}),
                400,
            )

        raw_client_code = payload.get("client_code")
        if raw_client_code is None:
            return (
                jsonify({"success": False, "error": "Código do cliente é obrigatório"}),
                400,
            )

        client_code = raw_client_code.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{1,3}", client_code):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Código do cliente deve ter de 1 a 3 caracteres (letras ou números)",
                    }
                ),
                400,
            )

        company_data = {
            "name": name,
            "client_code": client_code,
            "legal_name": (payload.get("legal_name") or "").strip() or None,
            "industry": (payload.get("industry") or "").strip() or None,
            "size": payload.get("size") or None,
            "description": (payload.get("description") or "").strip() or None,
        }

        new_id = db.create_company(company_data)
        if new_id:
            return jsonify({"success": True, "id": new_id}), 201
        return jsonify({"success": False, "error": "Erro ao criar empresa"}), 500
    except Exception as _err:
        logger.info(f"Error creating company: {_err}")
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/plans", methods=["POST"])
@api_login_required
def api_create_plan():
    """Create new strategic plan"""
    try:
        payload = request.get_json(silent=True) or {}

        # Validate required fields
        name = (payload.get("name") or "").strip()
        if not name:
            return (
                jsonify(
                    {"success": False, "error": "Nome do planejamento é obrigatório"}
                ),
                400,
            )

        company_id = payload.get("company_id")
        if not company_id:
            return jsonify({"success": False, "error": "Empresa é obrigatória"}), 400

        try:
            company_id = int(company_id)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "ID da empresa inválido"}), 400

        start_date_str = payload.get("start_date")
        if not start_date_str:
            return (
                jsonify({"success": False, "error": "Data de início é obrigatória"}),
                400,
            )

        end_date_str = payload.get("end_date")
        if not end_date_str:
            return (
                jsonify({"success": False, "error": "Data de fim é obrigatória"}),
                400,
            )

        # Verify company exists
        company = models_db.session.execute(
            models_db.text("SELECT id FROM companies WHERE id = :id"),
            {"id": company_id},
        ).fetchone()

        if not company:
            return jsonify({"success": False, "error": "Empresa não encontrada"}), 404

        # Parse dates
        try:
            if isinstance(start_date_str, str):
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            else:
                start_date = start_date_str

            if isinstance(end_date_str, str):
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                end_date = end_date_str
        except ValueError as e:
            return (
                jsonify(
                    {"success": False, "error": f"Formato de data inválido: {str(e)}"}
                ),
                400,
            )

        # Validate date range
        if end_date < start_date:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Data de fim deve ser posterior à data de início",
                    }
                ),
                400,
            )

        # Get optional description
        description = (payload.get("description") or "").strip() or None

        # Get plan mode (type of planning)
        plan_mode = (payload.get("plan_mode") or "").strip() or "evolucao"
        # Validate plan_mode
        if plan_mode not in ["evolucao", "implantacao"]:
            plan_mode = "evolucao"

        # Get year from start_date
        year = start_date.year

        # Use database abstraction layer to create plan
        plan_data = {
            "company_id": company_id,
            "name": name,
            "description": description,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "year": year,
            "status": "draft",
            "plan_mode": plan_mode,
        }

        new_plan_id = db.create_plan(plan_data)

        if not new_plan_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Erro ao criar planejamento no banco de dados",
                    }
                ),
                500,
            )

        # Criar projeto vinculado no GRV automaticamente
        project_created = False
        project_id = None

        logger.info(
            f"?? DEBUG: Iniciando criação de projeto GRV para plan_id={new_plan_id}"
        )
        logger.info(f"?? DEBUG: company_id={company_id}, plan_mode={plan_mode}")

        try:
            project_data = {
                "title": f"{name} (Projeto)",
                "description": description
                or f"Projeto vinculado ao planejamento {name}",
                "status": "planned",
                "priority": "medium",
                "owner": None,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "notes": f"Projeto criado automaticamente ao criar o planejamento em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            }

            logger.info(f"?? DEBUG: project_data preparado: {project_data}")

            # Criar projeto usando o método do database
            logger.info(f"?? DEBUG: Chamando db.create_company_project...")
            project_id = db.create_company_project(company_id, project_data)
            logger.info(f"?? DEBUG: create_company_project retornou: {project_id}")

            if project_id:
                # Vincular projeto ao plan
                logger.info(
                    f"?? DEBUG: Vinculando projeto {project_id} ao plan {new_plan_id}..."
                )
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE company_projects SET plan_id = %s, plan_type = %s WHERE id = %s",
                    (new_plan_id, "PEV", project_id),
                )
                conn.commit()
                conn.close()
                project_created = True
                logger.info(
                    f"[OK] Projeto GRV criado automaticamente: ID {project_id} para plan {new_plan_id}"
                )
            else:
                logger.info(f"[ERRO] create_company_project retornou None!")
        except Exception as project_err:
            logger.info(f"[ERRO] ERRO ao criar projeto GRV: {project_err}")
            import traceback

            traceback.print_exc()
            # Não falhar a criação do plano por causa disso

        return (
            jsonify(
                {
                    "success": True,
                    "id": new_plan_id,
                    "project_id": project_id if project_created else None,
                    "data": {
                        "id": new_plan_id,
                        "name": name,
                        "company_id": company_id,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "year": year,
                        "status": "draft",
                        "project_created": project_created,
                    },
                }
            ),
            201,
        )

    except Exception as _err:
        logger.info(f"Error creating plan: {_err}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/plans/<int:plan_id>", methods=["GET"])
@login_required
def api_get_plan(plan_id: int):
    """Get plan basic information including company_id"""
    try:
        # Get plan data from database using db layer
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, company_id, name, description, start_date, end_date, 
                   year, status, plan_mode, created_at
            FROM plans 
            WHERE id = %s
        """,
            (plan_id,),
        )

        plan_row = cursor.fetchone()
        conn.close()

        if not plan_row:
            return (
                jsonify({"success": False, "error": "Planejamento não encontrado"}),
                404,
            )

        # Convert row to dict
        plan_dict = dict(plan_row)

        # Convert dates to ISO format (if they are date/datetime objects)
        from datetime import date, datetime

        if plan_dict.get("start_date") and isinstance(
            plan_dict["start_date"], (date, datetime)
        ):
            plan_dict["start_date"] = plan_dict["start_date"].isoformat()
        if plan_dict.get("end_date") and isinstance(
            plan_dict["end_date"], (date, datetime)
        ):
            plan_dict["end_date"] = plan_dict["end_date"].isoformat()
        if plan_dict.get("created_at") and isinstance(
            plan_dict["created_at"], (date, datetime)
        ):
            plan_dict["created_at"] = plan_dict["created_at"].isoformat()

        return jsonify({"success": True, "data": plan_dict}), 200

    except Exception as err:
        logger.info(f"? Error getting plan {plan_id}: {err}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(err)}), 500


@app.route("/api/companies/<int:company_id>", methods=["GET"])
@login_required
def api_get_company_profile(company_id: int):
    try:
        profile = db.get_company_profile(company_id)
        if not profile:
            return jsonify({"success": False, "error": "not_found"}), 404
        return jsonify({"success": True, "data": profile})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>", methods=["POST"])
@login_required
def api_update_company_profile(company_id: int):
    """Update company basic information"""
    conn = None
    try:
        payload = request.get_json(silent=True) or {}

        def _clean(value):
            if value is None:
                return None
            if isinstance(value, str):
                value = value.strip()
                return value or None
            return value

        name = _clean(payload.get("name"))
        if not name:
            return (
                jsonify({"success": False, "error": "Nome da empresa é obrigatório"}),
                400,
            )

        raw_client_code = payload.get("client_code")
        if raw_client_code is not None:
            client_code = raw_client_code.strip().upper()
            if client_code and not re.fullmatch(r"[A-Z0-9]{1,3}", client_code):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Código do cliente deve ter de 1 a 3 caracteres (letras ou números)",
                        }
                    ),
                    400,
                )
            if not client_code:
                client_code = None
        else:
            client_code = None

        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE companies SET
                name = %s,
                client_code = %s,
                legal_name = %s,
                industry = %s,
                size = %s,
                description = %s
            WHERE id = %s
        """,
            (
                name,
                client_code,
                _clean(payload.get("legal_name")),
                _clean(payload.get("industry")),
                _clean(payload.get("size")),
                _clean(payload.get("description")),
                company_id,
            ),
        )
        conn.commit()

        return jsonify({"success": True})
    except Exception as _err:
        if conn:
            conn.rollback()
        logger.info(f"Error updating company: {_err}")
        return jsonify({"success": False, "error": str(_err)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/companies/<int:company_id>", methods=["DELETE"])
@login_required
def api_delete_company(company_id: int):
    """Delete company"""
    try:
        # Verificar se a empresa existe
        company = db.get_company(company_id)
        if not company:
            return jsonify({"success": False, "error": "Empresa não encontrada"}), 404

        # Deletar a empresa
        success = db.delete_company(company_id)
        if success:
            return jsonify({"success": True, "message": "Empresa excluída com sucesso"})
        else:
            return jsonify({"success": False, "error": "Erro ao excluir empresa"}), 500

    except Exception as e:
        logger.info(f"Error deleting company: {e}")
        return jsonify({"success": False, "error": "Erro interno do servidor"}), 500


# ===================================================================
# ROTAS DE RELATÓRIOS PROFISSIONAIS
# ===================================================================


def _gerar_relatorio_profissional(company_id: int):
    """
    Tenta gerar o relatório profissional usando WeasyPrint e aplica fallback,
    garantindo compatibilidade com ambientes que ainda dependem do ReportLab.
    """
    company = db.get_company(company_id)
    if not company:
        raise ValueError("Empresa não encontrada.")

    erros = []
    try:
        from modules.gerador_relatorios import (
            GeradorRelatoriosProfissionais as WeasyGenerator,
        )

        gerador = WeasyGenerator(db)
        pdf_path = gerador.gerar_relatorio_projetos(company_id)
        return pdf_path, "weasyprint"
    except ValueError:
        raise
    except Exception as exc:
        erros.append(("WeasyPrint", exc))
        logger.info(f"[relatorios] Falha ao gerar via WeasyPrint: {exc}")

    if getattr(db_config, "db_type", "sqlite") == "sqlite":
        try:
            from modules.gerador_relatorios_reportlab import (
                GeradorRelatoriosProfissionais as ReportLabGenerator,
            )

            sqlite_path = db_config.config.get("db_path", "pevapp22.db")
            gerador = ReportLabGenerator(db_path=sqlite_path)
            pdf_path = gerador.gerar_relatorio_projetos(company_id)
            return pdf_path, "reportlab"
        except ValueError:
            raise
        except Exception as exc:
            erros.append(("ReportLab", exc))
            logger.info(f"[relatorios] Falha ao gerar via ReportLab: {exc}")

    detalhes = (
        "; ".join(f"{origem}: {err}" for origem, err in erros)
        or "Verifique as depend?ncias instaladas."
    )
    raise RuntimeError(f"N?o foi poss?vel gerar o relat?rio profissional. {detalhes}")


@app.route("/relatorios/projetos/<int:company_id>")
def gerar_relatorio_projetos(company_id: int):
    """
    Gera relatório de projetos da empresa em PDF
    """
    try:
        pdf_path, _engine = _gerar_relatorio_profissional(company_id)

        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"relatorio_projetos_{company_id}.pdf",
        )

    except ValueError as ve:
        flash(f"Erro: {str(ve)}", "error")
        return redirect(url_for("companies"))
    except Exception as e:
        flash(f"Erro ao gerar relatório: {str(e)}", "error")
        return redirect(url_for("companies"))


@app.route("/api/relatorios/projetos/<int:company_id>")
def api_gerar_relatorio_projetos(company_id: int):
    """
    API para gerar relat?rio de projetos (retorna JSON com status)
    """
    try:
        pdf_path, engine = _gerar_relatorio_profissional(company_id)

        # Retorna informa??es do relat?rio gerado
        return jsonify(
            {
                "success": True,
                "message": "Relat?rio gerado com sucesso",
                "pdf_path": pdf_path,
                "engine": engine,
                "download_url": url_for(
                    "gerar_relatorio_projetos", company_id=company_id, _external=True
                ),
            }
        )

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/companies/<int:company_id>/employees", methods=["GET", "POST"])
@login_required
def api_company_employees(company_id: int):
    """List or create employees for a company"""
    company = db.get_company(company_id)
    if not company:
        return jsonify({"success": False, "error": "Empresa não encontrada."}), 404

    if request.method == "GET":
        try:
            employees = db.list_employees(company_id)
            return jsonify({"success": True, "employees": employees})
        except Exception as exc:
            logger.info(f"Erro ao listar colaboradores: {exc}")
            return (
                jsonify({"success": False, "message": "Erro ao listar colaboradores."}),
                500,
            )

    # POST
    payload = request.get_json(silent=True) or {}
    try:
        employee_id = db.create_employee(company_id, payload)
        if employee_id:
            employee = db.get_employee(company_id, employee_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "employee": employee,
                        "message": "Colaborador criado com sucesso.",
                    }
                ),
                201,
            )
        return jsonify({"success": False, "message": "Erro ao criar colaborador."}), 500
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.info(f"Erro ao criar colaborador: {exc}")
        return jsonify({"success": False, "message": "Erro ao criar colaborador."}), 500


@app.route(
    "/api/companies/<int:company_id>/employees/<int:employee_id>",
    methods=["GET", "PUT", "DELETE"],
)
@login_required
def api_company_employee(company_id: int, employee_id: int):
    """Update or delete an employee"""
    company = db.get_company(company_id)
    if not company:
        return jsonify({"success": False, "error": "Empresa não encontrada."}), 404

    if request.method == "GET":
        try:
            employee = db.get_employee(company_id, employee_id)
            if employee:
                return jsonify({"success": True, "employee": employee})
            return (
                jsonify({"success": False, "message": "Colaborador não encontrado."}),
                404,
            )
        except Exception as exc:
            logger.info(f"Erro ao buscar colaborador: {exc}")
            return (
                jsonify({"success": False, "message": "Erro ao buscar colaborador."}),
                500,
            )

    if request.method == "DELETE":
        try:
            success = db.delete_employee(company_id, employee_id)
            if success:
                return jsonify(
                    {"success": True, "message": "Colaborador excluído com sucesso."}
                )
            else:
                return (
                    jsonify(
                        {"success": False, "message": "Colaborador não encontrado."}
                    ),
                    404,
                )
        except Exception as exc:
            logger.info(f"Erro ao excluir colaborador: {exc}")
            return (
                jsonify({"success": False, "message": "Erro ao excluir colaborador."}),
                500,
            )

    # PUT
    payload = request.get_json(silent=True) or {}
    try:
        success = db.update_employee(company_id, employee_id, payload)
        if success:
            employee = db.get_employee(company_id, employee_id)
            return jsonify(
                {
                    "success": True,
                    "employee": employee,
                    "message": "Colaborador atualizado com sucesso.",
                }
            )
        return (
            jsonify({"success": False, "message": "Colaborador não encontrado."}),
            404,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.info(f"Erro ao atualizar colaborador: {exc}")
        return (
            jsonify({"success": False, "message": "Erro ao atualizar colaborador."}),
            500,
        )


@app.route("/api/companies/<int:company_id>/workforce-analysis", methods=["GET"])
@login_required
def api_workforce_analysis(company_id: int):
    """Get workforce analysis - hours used and capacity for all employees"""
    try:
        from database.postgres_helper import connect as pg_connect
        import json

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        # Get all active employees for this company
        cursor.execute(
            """
            SELECT id, name, email, department, role_id, weekly_hours
            FROM employees
            WHERE company_id = %s AND status = 'active'
            ORDER BY name
        """,
            (company_id,),
        )

        employees_data = []

        for emp_row in cursor.fetchall():
            employee_id = emp_row["id"]
            employee_name = emp_row["name"]
            department = emp_row["department"] or ""
            weekly_capacity = float(emp_row["weekly_hours"] or 40.0)

            # Get role title if exists
            role_title = ""
            if emp_row["role_id"]:
                cursor.execute(
                    "SELECT title FROM roles WHERE id = %s", (emp_row["role_id"],)
                )
                role_row = cursor.fetchone()
                if role_row:
                    role_title = role_row["title"]

            # Get all routines associated with this employee
            cursor.execute(
                """
                SELECT 
                    r.id, r.name, r.schedule_type, r.schedule_value, r.process_id,
                    rc.hours_used,
                    p.name as process_name
                FROM routine_collaborators rc
                JOIN routines r ON rc.routine_id = r.id
                LEFT JOIN processes p ON r.process_id = p.id
                WHERE rc.employee_id = %s AND r.company_id = %s AND r.is_active = 1
            """,
                (employee_id, company_id),
            )

            routines = []
            total_weekly_hours = 0.0

            for routine_row in cursor.fetchall():
                hours_used = float(routine_row["hours_used"] or 0)
                schedule_type = (routine_row["schedule_type"] or "weekly").lower()
                schedule_value = routine_row["schedule_value"] or ""

                # Convert hours to weekly basis based on schedule type
                weekly_hours = 0.0

                if schedule_type == "daily":
                    # Daily routines: 5 workdays per week
                    weekly_hours = hours_used * 5
                elif schedule_type == "weekly":
                    # Weekly routines: parse how many days per week
                    try:
                        if schedule_value:
                            days_data = (
                                json.loads(schedule_value)
                                if isinstance(schedule_value, str)
                                else schedule_value
                            )
                            if isinstance(days_data, list):
                                weekly_hours = hours_used * len(days_data)
                            else:
                                weekly_hours = hours_used  # Default to once per week
                        else:
                            weekly_hours = hours_used  # Default to once per week
                    except Exception as exc:
                        weekly_hours = hours_used  # Default to once per week
                elif schedule_type == "monthly":
                    # Monthly routines: ~4.33 weeks per month
                    weekly_hours = hours_used / 4.33
                elif schedule_type == "quarterly":
                    # Quarterly routines: 4 times per year
                    weekly_hours = (hours_used * 4) / 52
                elif schedule_type == "yearly" or schedule_type == "annual":
                    # Annual routines: once per year
                    weekly_hours = hours_used / 52
                elif schedule_type == "specific":
                    # Specific date routines don't count as recurring
                    weekly_hours = 0.0
                else:
                    # Default to weekly
                    weekly_hours = hours_used

                total_weekly_hours += weekly_hours

                routines.append(
                    {
                        "id": routine_row["id"],
                        "name": routine_row["name"],
                        "process_name": routine_row["process_name"] or "",
                        "schedule_type": schedule_type,
                        "hours_used": hours_used,
                        "weekly_hours": round(weekly_hours, 2),
                    }
                )

            # Calculate metrics
            hours_daily = round(total_weekly_hours / 5, 2)
            hours_weekly = round(total_weekly_hours, 2)
            hours_monthly = round(total_weekly_hours * 4.33, 2)
            hours_yearly = round(total_weekly_hours * 52, 2)
            hours_monthly_avg = round(hours_yearly / 12, 2)
            hours_available = round(weekly_capacity - total_weekly_hours, 2)

            utilization = round(
                (total_weekly_hours / weekly_capacity * 100)
                if weekly_capacity > 0
                else 0,
                1,
            )

            employees_data.append(
                {
                    "id": employee_id,
                    "name": employee_name,
                    "email": emp_row["email"] or "",
                    "department": department,
                    "role_title": role_title,
                    "weekly_capacity": weekly_capacity,
                    "hours_daily": hours_daily,
                    "hours_weekly": hours_weekly,
                    "hours_monthly": hours_monthly,
                    "hours_yearly": hours_yearly,
                    "hours_monthly_avg": hours_monthly_avg,
                    "hours_available": hours_available,
                    "utilization": utilization,
                    "routines": routines,
                }
            )

        conn.close()

        return jsonify({"success": True, "employees": employees_data})

    except Exception as exc:
        logger.info(f"Erro ao analisar mão de obra: {exc}")
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Erro ao analisar mão de obra: {str(exc)}",
                }
            ),
            500,
        )


@app.route("/api/companies/<int:company_id>/client-code", methods=["POST"])
def api_update_client_code(company_id: int):
    """Update only the client code for a company"""
    try:
        payload = request.get_json(silent=True) or {}
        raw_client_code = payload.get("client_code")

        if raw_client_code is not None:
            client_code = raw_client_code.strip().upper()
            if client_code and not re.fullmatch(r"[A-Z0-9]{1,3}", client_code):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Código do cliente deve ter de 1 a 3 caracteres (letras ou números)",
                        }
                    ),
                    400,
                )
            if not client_code:
                client_code = None
        else:
            client_code = None

        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE companies SET client_code = %s WHERE id = %s",
            (client_code, company_id),
        )
        conn.commit()
        conn.close()

        return jsonify({"success": True})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


# Roles (Funções) CRUD
@app.route("/api/companies/<int:company_id>/roles", methods=["GET"])
def api_list_roles(company_id: int):
    try:
        roles = db.list_roles(company_id)
        return jsonify({"success": True, "roles": roles})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/roles/tree", methods=["GET"])
def api_roles_tree(company_id: int):
    try:
        tree = db.get_roles_tree(company_id)
        return jsonify({"success": True, "data": tree})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/roles", methods=["POST"])
def api_create_role(company_id: int):
    payload = request.get_json(silent=True) or {}
    new_id = db.create_role(company_id, payload)
    if new_id:
        return jsonify({"success": True, "id": new_id}), 201
    return jsonify({"success": False, "error": "create_failed"}), 400


@app.route("/api/companies/<int:company_id>/roles/<int:role_id>", methods=["PUT"])
def api_update_role(company_id: int, role_id: int):
    payload = request.get_json(silent=True) or {}
    ok = db.update_role(role_id, payload)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "update_failed"}), 400


@app.route("/api/companies/<int:company_id>/roles/<int:role_id>", methods=["DELETE"])
def api_delete_role(company_id: int, role_id: int):
    ok = db.delete_role(role_id)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "delete_failed"}), 400


# Process Map APIs
@app.route("/api/companies/<int:company_id>/process-map", methods=["GET"])
def api_get_process_map(company_id: int):
    try:
        data = db.get_process_map(company_id)
        return jsonify({"success": True, "data": data})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


# Process Areas
@app.route("/api/companies/<int:company_id>/process-areas", methods=["GET"])
def api_list_process_areas(company_id: int):
    try:
        areas = db.list_process_areas(company_id)
        return jsonify({"success": True, "data": areas})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/process-areas", methods=["POST"])
def api_create_process_area(company_id: int):
    payload = request.get_json(silent=True) or {}
    new_id = db.create_process_area(company_id, payload)
    if new_id:
        return jsonify({"success": True, "id": new_id}), 201
    return jsonify({"success": False, "error": "create_failed"}), 400


@app.route(
    "/api/companies/<int:company_id>/process-areas/<int:area_id>", methods=["PUT"]
)
def api_update_process_area(company_id: int, area_id: int):
    payload = request.get_json(silent=True) or {}
    ok = db.update_process_area(area_id, payload)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "update_failed"}), 400


@app.route(
    "/api/companies/<int:company_id>/process-areas/<int:area_id>", methods=["DELETE"]
)
def api_delete_process_area(company_id: int, area_id: int):
    ok = db.delete_process_area(area_id)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "delete_failed"}), 400


# Macro Processes
@app.route("/api/companies/<int:company_id>/macro-processes", methods=["GET"])
def api_list_macro_processes(company_id: int):
    try:
        macros = db.list_macro_processes(company_id)
        return jsonify({"success": True, "data": macros})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/macro-processes", methods=["POST"])
def api_create_macro_process(company_id: int):
    payload = request.get_json(silent=True) or {}
    new_id = db.create_macro_process(company_id, payload)
    if new_id:
        return jsonify({"success": True, "id": new_id}), 201
    return jsonify({"success": False, "error": "create_failed"}), 400


@app.route(
    "/api/companies/<int:company_id>/macro-processes/<int:macro_id>", methods=["PUT"]
)
def api_update_macro_process(company_id: int, macro_id: int):
    payload = request.get_json(silent=True) or {}
    ok = db.update_macro_process(macro_id, payload)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "update_failed"}), 400


@app.route(
    "/api/companies/<int:company_id>/macro-processes/<int:macro_id>", methods=["DELETE"]
)
def api_delete_macro_process(company_id: int, macro_id: int):
    ok = db.delete_macro_process(macro_id)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "delete_failed"}), 400


# Processes
@app.route("/api/companies/<int:company_id>/processes", methods=["GET"])
def api_list_processes(company_id: int):
    try:
        processes = db.list_processes(company_id)
        return jsonify({"success": True, "data": processes})
    except Exception as _err:
        return jsonify({"success": False, "error": str(_err)}), 500


@app.route("/api/companies/<int:company_id>/processes", methods=["POST"])
def api_create_process(company_id: int):
    payload = request.get_json(silent=True) or {}
    new_id = db.create_process(company_id, payload)
    if new_id:
        return jsonify({"success": True, "id": new_id}), 201
    return jsonify({"success": False, "error": "create_failed"}), 400


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>", methods=["PUT"]
)
def api_update_process(company_id: int, process_id: int):
    payload = request.get_json(silent=True) or {}
    ok = db.update_process(process_id, payload)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "update_failed"}), 400


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/stage",
    methods=["PATCH"],
)
def api_update_process_stage(company_id: int, process_id: int):
    payload = request.get_json(silent=True) or {}
    stage = payload.get("stage") or payload.get("kanban_stage")
    if not stage:
        return jsonify({"success": False, "error": "missing_stage"}), 400
    normalized_stage = db.update_process_stage(process_id, stage)
    if normalized_stage is None:
        return jsonify({"success": False, "error": "update_failed"}), 400
    return jsonify({"success": True, "stage": normalized_stage})


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/notes",
    methods=["GET", "PUT"],
)
def api_process_notes(company_id: int, process_id: int):
    """Get or update process notes"""
    process = db.get_process(process_id)
    if not process or process.get("company_id") != company_id:
        return jsonify({"success": False, "error": "not_found"}), 404

    if request.method == "GET":
        return jsonify({"success": True, "notes": process.get("notes", "")})

    # PUT - Update notes
    payload = request.get_json(silent=True) or {}
    notes = payload.get("notes", "")
    ok = db.update_process_notes(process_id, notes)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "update_failed"}), 400


def _allowed_flow_extension(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in PROCESS_FLOW_ALLOWED_EXTENSIONS
    )


def _delete_flow_file(relative_path: str):
    if not relative_path:
        return
    try:
        file_path = os.path.join(upload_folder, relative_path.replace("/", os.sep))
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as _exc:
        logger.info(f"Warning: failed to remove flow file {relative_path}: {_exc}")


def _allowed_activity_image_extension(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in PROCESS_ACTIVITY_ALLOWED_EXTENSIONS
    )


def _delete_activity_image(relative_path: str):
    if not relative_path:
        return
    try:
        file_path = os.path.join(upload_folder, relative_path.replace("/", os.sep))
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as _exc:
        logger.info(f"Warning: failed to remove activity image {relative_path}: {_exc}")


def _save_activity_image(activity_id: int, storage) -> Optional[str]:
    if not storage or storage.filename == "":
        return None
    if not _allowed_activity_image_extension(storage.filename):
        return None
    safe_name = secure_filename(storage.filename)
    _, ext = os.path.splitext(safe_name)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    final_name = f"activity-{activity_id}-{timestamp}{ext.lower()}"
    relative_path = f"process_activities/{final_name}"
    storage_path = os.path.join(process_activity_folder, final_name)
    storage.save(storage_path)
    return relative_path


def _normalize_activity_suffix(suffix: Optional[str]) -> Optional[str]:
    if suffix is None:
        return None
    cleaned = "".join(ch for ch in str(suffix).strip() if ch.isdigit())
    if not cleaned:
        return None
    if len(cleaned) > 2:
        cleaned = cleaned[-2:]
    return cleaned.zfill(2)


def _build_activity_code(
    process_code: Optional[str], process_id: int, suffix: str
) -> str:
    base = (process_code or f"PROC-{process_id}").strip().rstrip(".")
    return f"{base}.{suffix}"


def _extract_activity_suffix(activity_code: Optional[str]) -> str:
    if not activity_code:
        return ""
    parts = str(activity_code).split(".")
    return parts[-1] if parts else ""


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/flow",
    methods=["POST", "DELETE"],
)
def api_process_flow_document(company_id: int, process_id: int):
    process = db.get_process(process_id)
    if not process or process.get("company_id") != company_id:
        return jsonify({"success": False, "error": "process_not_found"}), 404

    if request.method == "DELETE":
        existing_path = process.get("flow_document")
        if existing_path:
            _delete_flow_file(existing_path)
            db.set_process_flow_document(process_id, None)
        return jsonify({"success": True, "flow_document": None})

    upload = request.files.get("file")
    if not upload or upload.filename == "":
        return jsonify({"success": False, "error": "missing_file"}), 400

    if not _allowed_flow_extension(upload.filename):
        return jsonify({"success": False, "error": "unsupported_type"}), 400

    safe_name = secure_filename(upload.filename)
    _, ext = os.path.splitext(safe_name)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    final_name = f"process-{process_id}-{timestamp}{ext.lower()}"
    relative_path = f"process_flows/{final_name}"
    storage_path = os.path.join(process_flow_folder, final_name)

    # Remove previous document if any
    existing_path = process.get("flow_document")
    if existing_path and existing_path != relative_path:
        _delete_flow_file(existing_path)

    try:
        upload.save(storage_path)
        db.set_process_flow_document(process_id, relative_path)
    except Exception as exc:
        logger.info(f"Error saving process flow document: {exc}")
        return jsonify({"success": False, "error": "save_failed"}), 500

    preview_type = "pdf" if ext.lower() == ".pdf" else "image"
    file_url = url_for("serve_uploaded_file", filename=relative_path)
    return jsonify(
        {
            "success": True,
            "flow_document": relative_path,
            "url": file_url,
            "preview_type": preview_type,
        }
    )


def _serialize_activity_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    image_path = entry.get("image_path")
    return {
        "id": entry.get("id"),
        "order_index": entry.get("order_index"),
        "text_content": entry.get("text_content") or "",
        "image_path": image_path,
        "image_url": url_for("serve_uploaded_file", filename=image_path)
        if image_path
        else None,
        "image_width": entry.get("image_width") or 280,
        "layout": entry.get("layout") or "dual",  # Adicionado campo layout
        "created_at": entry.get("created_at"),
        "updated_at": entry.get("updated_at"),
    }


def _serialize_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    code = activity.get("code") or ""
    suffix = activity.get("code_suffix") or _extract_activity_suffix(code)
    base_code = code
    if suffix and code.endswith(f".{suffix}"):
        base_code = code[: -(len(suffix) + 1)]
    serialized = {
        "id": activity.get("id"),
        "process_id": activity.get("process_id"),
        "code": activity.get("code"),
        "base_code": base_code,
        "suffix": suffix,
        "name": activity.get("name"),
        "layout": activity.get("layout") or "single",
        "order_index": activity.get("order_index"),
        "created_at": activity.get("created_at"),
        "updated_at": activity.get("updated_at"),
        "entries": [],
    }
    entries = activity.get("entries") or []
    serialized["entries"] = [_serialize_activity_entry(entry) for entry in entries]
    return serialized


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/activities",
    methods=["GET", "POST"],
)
def api_process_activities(company_id: int, process_id: int):
    process = db.get_process(process_id)
    if not process or process.get("company_id") != company_id:
        return jsonify({"success": False, "error": "process_not_found"}), 404

    if request.method == "GET":
        activities = db.list_process_activities(process_id)
        data = [_serialize_activity(activity) for activity in activities]
        return jsonify({"success": True, "data": data})

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    layout = payload.get("layout") or "single"
    suffix = _normalize_activity_suffix(payload.get("suffix"))
    if not name:
        return jsonify({"success": False, "error": "missing_name"}), 400
    if not suffix:
        return jsonify({"success": False, "error": "invalid_suffix"}), 400

    existing = db.list_process_activities(process_id)
    if any((_extract_activity_suffix(act.get("code")) == suffix) for act in existing):
        return jsonify({"success": False, "error": "duplicate_suffix"}), 400

    new_id = db.create_process_activity(
        process_id,
        {
            "code_suffix": suffix,
            "name": name,
            "layout": layout if layout in ("single", "dual") else "single",
        },
    )
    if not new_id:
        return jsonify({"success": False, "error": "create_failed"}), 400

    activity = db.get_process_activity(new_id) or {}
    activity["entries"] = []
    return jsonify({"success": True, "data": _serialize_activity(activity)}), 201


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>",
    methods=["PUT", "DELETE"],
)
def api_process_activity_detail(company_id: int, process_id: int, activity_id: int):
    process = db.get_process(process_id)
    if not process or process.get("company_id") != company_id:
        return jsonify({"success": False, "error": "process_not_found"}), 404

    activity = db.get_process_activity(activity_id)
    if not activity or activity.get("process_id") != process_id:
        return jsonify({"success": False, "error": "activity_not_found"}), 404

    if request.method == "DELETE":
        entries = db.list_process_activity_entries(activity_id)
        for entry in entries:
            if entry.get("image_path"):
                _delete_activity_image(entry["image_path"])
        db.delete_process_activity(activity_id)
        return jsonify({"success": True})

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or activity.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "missing_name"}), 400
    layout = payload.get("layout") or activity.get("layout") or "single"
    order_index = payload.get("order_index", activity.get("order_index") or 0)
    suffix_value = payload.get("suffix")
    if suffix_value is None:
        normalized_suffix = activity.get("code_suffix") or _extract_activity_suffix(
            activity.get("code")
        )
    else:
        normalized_suffix = _normalize_activity_suffix(suffix_value)
        if not normalized_suffix:
            return jsonify({"success": False, "error": "invalid_suffix"}), 400
        existing = db.list_process_activities(process_id)
        for act in existing:
            if act.get("id") == activity_id:
                continue
            if _extract_activity_suffix(act.get("code")) == normalized_suffix:
                return jsonify({"success": False, "error": "duplicate_suffix"}), 400
    ok = db.update_process_activity(
        activity_id,
        {
            "name": name,
            "layout": layout if layout in ("single", "dual") else "single",
            "order_index": order_index,
            "code_suffix": normalized_suffix,
        },
    )
    if not ok:
        return jsonify({"success": False, "error": "update_failed"}), 400
    updated = db.get_process_activity(activity_id) or {}
    updated["entries"] = db.list_process_activity_entries(activity_id)
    return jsonify({"success": True, "data": _serialize_activity(updated)})


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries",
    methods=["POST"],
)
def api_create_process_activity_entry(
    company_id: int, process_id: int, activity_id: int
):
    process = db.get_process(process_id)
    if not process or process.get("company_id") != company_id:
        return jsonify({"success": False, "error": "process_not_found"}), 404

    activity = db.get_process_activity(activity_id)
    if not activity or activity.get("process_id") != process_id:
        return jsonify({"success": False, "error": "activity_not_found"}), 404

    text_content = (request.form.get("text_content") or "").strip()
    image_file = request.files.get("image")
    image_width = request.form.get("image_width")
    layout = request.form.get("layout", "dual")  # ADICIONADO

    logger.info(f"\n{'='*60}")
    logger.info(f"DEBUG - CREATE ENTRY para activity_id={activity_id}")
    logger.info(f"  text_content: '{text_content[:50]}...' ({len(text_content)} chars)")
    logger.info(f"  image_file: {image_file.filename if image_file else 'None'}")
    logger.info(f"  image_width: {image_width}")
    logger.info(f"  layout: {layout}")  # ADICIONADO
    logger.info(f"{'='*60}\n")

    if not text_content and not image_file:
        logger.info("ERROR - Sem texto e sem imagem")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "missing_content",
                    "message": "Adicione texto ou imagem",
                }
            ),
            400,
        )

    image_path = None
    if image_file and image_file.filename:
        logger.info(f"Tentando salvar imagem: {image_file.filename}")
        try:
            image_path = _save_activity_image(activity_id, image_file)
            if not image_path:
                logger.info("ERROR - _save_activity_image retornou None")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "invalid_image",
                            "message": "Falha ao salvar imagem",
                        }
                    ),
                    400,
                )
            logger.info(f">> Imagem salva: {image_path}")
        except Exception as img_err:
            logger.info(f"ERROR - Exceção ao salvar imagem: {img_err}")
            import traceback

            traceback.print_exc()
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "image_save_failed",
                        "message": str(img_err),
                    }
                ),
                400,
            )

    try:
        if image_width and str(image_width).strip():
            width_val = int(image_width)
            width_val = max(180, min(600, width_val))
        else:
            width_val = 280
    except (ValueError, TypeError) as e:
        logger.info(
            f"WARN - Erro ao converter image_width '{image_width}': {e}, usando 280"
        )
        width_val = 280

    logger.info(
        f"Criando entry no banco: text_len={len(text_content)}, image_path={image_path}, width={width_val}, layout={layout}"
    )

    try:
        new_id = db.create_process_activity_entry(
            activity_id,
            {
                "text_content": text_content,
                "image_path": image_path,
                "image_width": width_val,
                "layout": layout,  # ADICIONADO
            },
        )
    except Exception as db_err:
        logger.info(f"ERROR - Exceção no create_process_activity_entry: {db_err}")
        import traceback

        traceback.print_exc()
        if image_path:
            _delete_activity_image(image_path)
        return (
            jsonify(
                {"success": False, "error": "database_error", "message": str(db_err)}
            ),
            500,
        )

    if not new_id:
        logger.info("ERROR - create_process_activity_entry retornou None/False")
        if image_path:
            _delete_activity_image(image_path)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "create_failed",
                    "message": "Falha ao criar no banco",
                }
            ),
            400,
        )

    logger.info(f">> Entry criada com sucesso! ID={new_id}")
    entry = db.get_process_activity_entry(new_id) or {}
    return jsonify({"success": True, "data": _serialize_activity_entry(entry)}), 201


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>",
    methods=["PUT", "DELETE"],
)
def api_process_activity_entry_detail(
    company_id: int, process_id: int, activity_id: int, entry_id: int
):
    process = db.get_process(process_id)
    if not process or process.get("company_id") != company_id:
        return jsonify({"success": False, "error": "process_not_found"}), 404

    activity = db.get_process_activity(activity_id)
    if not activity or activity.get("process_id") != process_id:
        return jsonify({"success": False, "error": "activity_not_found"}), 404

    entry = db.get_process_activity_entry(entry_id)
    if not entry or entry.get("activity_id") != activity_id:
        return jsonify({"success": False, "error": "entry_not_found"}), 404

    if request.method == "DELETE":
        if entry.get("image_path"):
            _delete_activity_image(entry["image_path"])
        db.delete_process_activity_entry(entry_id)
        return jsonify({"success": True})

    text_content = (
        request.form.get("text_content") or entry.get("text_content") or ""
    ).strip()
    image_file = request.files.get("image")
    remove_image = request.form.get("remove_image")
    order_index = request.form.get("order_index")
    image_width = request.form.get("image_width")

    remove_flag = bool(remove_image)
    old_image_path = entry.get("image_path")
    image_path = old_image_path
    new_image_path = None

    if image_file and image_file.filename:
        new_path = _save_activity_image(activity_id, image_file)
        if not new_path:
            return jsonify({"success": False, "error": "invalid_image"}), 400
        new_image_path = new_path
        image_path = new_path
    elif remove_flag:
        image_path = None

    if not text_content and not image_path:
        return jsonify({"success": False, "error": "missing_content"}), 400

    try:
        order_val = (
            int(order_index)
            if order_index is not None
            else entry.get("order_index") or 0
        )
    except ValueError:
        order_val = entry.get("order_index") or 0

    try:
        width_val = (
            int(image_width)
            if image_width is not None
            else entry.get("image_width") or 280
        )
        # Limita entre 180px e 600px
        width_val = max(180, min(600, width_val))
    except ValueError:
        width_val = entry.get("image_width") or 280

    ok = db.update_process_activity_entry(
        entry_id,
        {
            "text_content": text_content,
            "image_path": image_path,
            "order_index": order_val,
            "image_width": width_val,
        },
    )
    if not ok:
        if new_image_path:
            _delete_activity_image(new_image_path)
        return jsonify({"success": False, "error": "update_failed"}), 400
    if new_image_path and old_image_path and old_image_path != new_image_path:
        _delete_activity_image(old_image_path)
    elif remove_flag and old_image_path:
        _delete_activity_image(old_image_path)
    updated = db.get_process_activity_entry(entry_id) or {}
    return jsonify({"success": True, "data": _serialize_activity_entry(updated)})


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>", methods=["DELETE"]
)
def api_delete_process(company_id: int, process_id: int):
    ok = db.delete_process(process_id)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "delete_failed"}), 400


# Process Instances APIs
@app.route("/api/companies/<int:company_id>/process-instances", methods=["GET"])
def api_list_process_instances(company_id: int):
    """List all process instances for a company"""
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM process_instances 
            WHERE company_id = %s
            ORDER BY created_at DESC
            """,
            (company_id,),
        )

        instances = []
        for row in cursor.fetchall():
            instances.append(dict(row))

        conn.close()
        return jsonify(instances)
    except Exception as e:
        logger.info(f"Erro ao listar instâncias: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/companies/<int:company_id>/process-instances", methods=["POST"])
def api_create_process_instance(company_id: int):
    """Create a new process instance (manual trigger)"""
    try:
        from database.postgres_helper import connect as pg_connect
        import json
        from datetime import datetime

        payload = request.get_json(silent=True) or {}

        process_id = payload.get("process_id")
        title = payload.get("title", "").strip()
        due_date = payload.get("due_date")
        priority = payload.get("priority", "normal")
        description = payload.get("description", "").strip()
        trigger_type = payload.get("trigger_type", "manual")

        if not process_id or not title:
            return jsonify({"error": "Missing required fields"}), 400

        # Get process details
        process = db.get_process(process_id)
        if not process or process.get("company_id") != company_id:
            return jsonify({"error": "Process not found"}), 404

        # Generate instance code
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        # Get company code
        company = db.get_company(company_id)
        company_code = company.get("client_code", "XX")

        # Get max sequence for this process
        cursor.execute(
            """
            SELECT COUNT(*) as count 
            FROM process_instances 
            WHERE company_id = %s AND process_id = %s
            """,
            (company_id, process_id),
        )
        result = cursor.fetchone()
        sequence = (result["count"] if result else 0) + 1

        instance_code = f"{company_code}.P{process_id}.{sequence:03d}"

        # Get routine collaborators if exists
        assigned_collaborators = []
        estimated_hours = 0.0
        routine_id = None

        try:
            cursor.execute(
                """
                SELECT id, assigned_roles 
                FROM routines 
                WHERE company_id = %s AND process_id = %s
                LIMIT 1
                """,
                (company_id, process_id),
            )
            routine_row = cursor.fetchone()

            if routine_row:
                routine_id = routine_row["id"]
                assigned_roles_json = routine_row["assigned_roles"]

                if assigned_roles_json:
                    assigned_roles = (
                        json.loads(assigned_roles_json)
                        if isinstance(assigned_roles_json, str)
                        else assigned_roles_json
                    )

                    for role_data in assigned_roles:
                        employee_id = role_data.get("employee_id")
                        hours = float(role_data.get("hours", 0))

                        if employee_id:
                            cursor.execute(
                                "SELECT name FROM employees WHERE id = %s",
                                (employee_id,),
                            )
                            emp_row = cursor.fetchone()
                            if emp_row:
                                assigned_collaborators.append(
                                    {
                                        "id": employee_id,
                                        "name": emp_row["name"],
                                        "hours": hours,
                                    }
                                )
                                estimated_hours += hours
        except Exception as e:
            logger.info(f"Warning: Could not fetch routine collaborators: {e}")

        # Insert instance
        cursor.execute(
            """
            INSERT INTO process_instances (
                company_id, process_id, routine_id, instance_code,
                title, description, status, priority, due_date,
                assigned_collaborators, estimated_hours, trigger_type,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                company_id,
                process_id,
                routine_id,
                instance_code,
                title,
                description,
                "pending",
                priority,
                due_date,
                json.dumps(assigned_collaborators),
                estimated_hours,
                trigger_type,
                datetime.now().isoformat(),
            ),
        )

        instance_id = cursor.fetchone()[0]
        conn.commit()

        # Get created instance
        cursor.execute("SELECT * FROM process_instances WHERE id = %s", (instance_id,))
        instance_row = cursor.fetchone()
        conn.close()

        instance = dict(instance_row) if instance_row else {}
        return jsonify(instance), 201

    except Exception as e:
        logger.info(f"Erro ao criar instância: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/routine-collaborators",
    methods=["GET"],
)
def api_get_process_routine_collaborators(company_id: int, process_id: int):
    """Get collaborators assigned to a process via routine"""
    try:
        from database.postgres_helper import connect as pg_connect
        import json

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        # Find routine for this process
        cursor.execute(
            """
            SELECT id, assigned_roles 
            FROM routines 
            WHERE company_id = %s AND process_id = %s
            LIMIT 1
            """,
            (company_id, process_id),
        )

        routine_row = cursor.fetchone()

        if not routine_row or not routine_row["assigned_roles"]:
            conn.close()
            return jsonify({"collaborators": []})

        assigned_roles_json = routine_row["assigned_roles"]
        assigned_roles = (
            json.loads(assigned_roles_json)
            if isinstance(assigned_roles_json, str)
            else assigned_roles_json
        )

        collaborators = []
        for role_data in assigned_roles:
            employee_id = role_data.get("employee_id")
            hours = float(role_data.get("hours", 0))

            if employee_id:
                cursor.execute(
                    "SELECT name FROM employees WHERE id = %s", (employee_id,)
                )
                emp_row = cursor.fetchone()
                if emp_row:
                    collaborators.append(
                        {"id": employee_id, "name": emp_row["name"], "hours": hours}
                    )

        conn.close()
        return jsonify({"collaborators": collaborators})

    except Exception as e:
        logger.info(f"Erro ao buscar colaboradores: {e}")
        return jsonify({"error": str(e)}), 500


@app.route(
    "/api/companies/<int:company_id>/process-instances/<int:instance_id>",
    methods=["PATCH"],
)
def api_update_process_instance(company_id: int, instance_id: int):
    """Update process instance"""
    try:
        from database.postgres_helper import connect as pg_connect
        from datetime import datetime

        payload = request.get_json(silent=True) or {}

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        # Verify instance exists and belongs to company
        cursor.execute(
            "SELECT * FROM process_instances WHERE id = %s AND company_id = %s",
            (instance_id, company_id),
        )
        instance = cursor.fetchone()
        if not instance:
            conn.close()
            return jsonify({"error": "Instance not found"}), 404

        # Build update query dynamically
        updates = []
        params = []

        if "status" in payload:
            updates.append("status = ?")
            params.append(payload["status"])

        if "priority" in payload:
            updates.append("priority = ?")
            params.append(payload["priority"])

        if "assigned_collaborators" in payload:
            updates.append("assigned_collaborators = ?")
            params.append(payload["assigned_collaborators"])

        if "actual_hours" in payload:
            updates.append("actual_hours = ?")
            params.append(payload["actual_hours"])

        if "notes" in payload:
            updates.append("notes = ?")
            params.append(payload["notes"])

        if "completed_at" in payload:
            updates.append("completed_at = ?")
            params.append(payload["completed_at"])

        if "started_at" in payload:
            updates.append("started_at = ?")
            params.append(payload["started_at"])

        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(instance_id)

            sql = f"UPDATE process_instances SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            conn.commit()

        # Get updated instance
        cursor.execute("SELECT * FROM process_instances WHERE id = %s", (instance_id,))
        updated_instance = cursor.fetchone()
        conn.close()

        return jsonify(dict(updated_instance) if updated_instance else {})

    except Exception as e:
        logger.info(f"Erro ao atualizar instância: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/companies/<int:company_id>/unified-activities", methods=["GET"])
def api_get_unified_activities(company_id: int):
    """Get unified list of project activities and process instances"""
    try:
        from database.postgres_helper import connect as pg_connect
        import json

        unified_activities = []

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        # Get project activities
        cursor.execute(
            """
            SELECT 
                cp.id as project_id,
                cp.code as project_code,
                cp.title as project_name,
                cp.activities,
                cp.responsible_id,
                e.name as responsible_name
            FROM company_projects cp
            LEFT JOIN employees e ON e.id = cp.responsible_id
            WHERE cp.company_id = %s
            """,
            (company_id,),
        )

        project_rows = cursor.fetchall()

        for project_row in project_rows:
            activities_json = project_row["activities"]
            if activities_json:
                try:
                    activities = (
                        json.loads(activities_json)
                        if isinstance(activities_json, str)
                        else activities_json
                    )
                    if isinstance(activities, list):
                        for activity in activities:
                            # Parse who field for executors
                            who = activity.get("who", "")
                            executors = []
                            if who:
                                # Simple text executor
                                executors = [who] if who else []

                            unified_activities.append(
                                {
                                    "id": f"project-{project_row['project_id']}-{activity.get('id')}",
                                    "type": "project_activity",
                                    "project_id": project_row["project_id"],
                                    "activity_id": activity.get("id"),
                                    "code": activity.get("code", ""),
                                    "title": activity.get("what", "Sem título"),
                                    "description": activity.get("observations", ""),
                                    "status": activity.get("status", "pending"),
                                    "stage": activity.get("stage", "inbox"),
                                    "due_date": activity.get("when", ""),
                                    "project_name": project_row["project_name"],
                                    "project_code": project_row["project_code"],
                                    "responsible": project_row["responsible_name"],
                                    "responsible_id": project_row["responsible_id"],
                                    "executors": executors,
                                    "amount": activity.get("amount", ""),
                                    "how": activity.get("how", ""),
                                }
                            )
                except Exception as e:
                    logger.info(f"Error parsing project activities: {e}")

        # Get process instances
        cursor.execute(
            """
            SELECT 
                pi.*,
                p.code as process_code,
                p.name as process_name
            FROM process_instances pi
            LEFT JOIN processes p ON p.id = pi.process_id
            WHERE pi.company_id = %s
            """,
            (company_id,),
        )

        inst_rows = cursor.fetchall()

        for inst_row in inst_rows:
            # Parse assigned collaborators
            collab_json = inst_row["assigned_collaborators"]
            executors = []
            if collab_json:
                try:
                    collabs = (
                        json.loads(collab_json)
                        if isinstance(collab_json, str)
                        else collab_json
                    )
                    if isinstance(collabs, list):
                        executors = [
                            c.get("name", "") for c in collabs if c.get("name")
                        ]
                except Exception as exc:
                    pass

            unified_activities.append(
                {
                    "id": f"process-{inst_row['id']}",
                    "type": "process_instance",
                    "instance_id": inst_row["id"],
                    "process_id": inst_row["process_id"],
                    "code": inst_row["instance_code"] or "",
                    "title": inst_row["title"],
                    "description": inst_row["description"] or "",
                    "status": inst_row["status"],
                    "stage": None,
                    "due_date": inst_row["due_date"] or "",
                    "process_name": inst_row["process_name"],
                    "process_code": inst_row["process_code"],
                    "responsible": None,
                    "responsible_id": None,
                    "executors": executors,
                    "priority": inst_row["priority"],
                    "estimated_hours": inst_row["estimated_hours"],
                    "actual_hours": inst_row["actual_hours"],
                }
            )

        conn.close()

        return jsonify(unified_activities)

    except Exception as e:
        logger.info(f"Erro ao buscar atividades unificadas: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ====================================
# OCCURRENCES API
# ====================================


@app.route("/api/companies/<int:company_id>/occurrences", methods=["GET", "POST"])
def api_company_occurrences(company_id: int):
    """List or create occurrences"""
    if request.method == "GET":
        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    o.id,
                    o.employee_id,
                    o.process_id,
                    o.project_id,
                    o.title,
                    o.description,
                    o.type,
                    o.score,
                    o.created_at,
                    o.updated_at,
                    e.name as employee_name,
                    p.name as process_name,
                    p.code as process_code,
                    cp.title as project_name,
                    cp.code as project_code
                FROM occurrences o
                LEFT JOIN employees e ON o.employee_id = e.id
                LEFT JOIN processes p ON o.process_id = p.id
                LEFT JOIN company_projects cp ON o.project_id = cp.id
                WHERE o.company_id = %s
                ORDER BY o.created_at DESC
            """,
                (company_id,),
            )

            occurrences = []
            for row in cursor.fetchall():
                occurrences.append(
                    {
                        "id": row["id"],
                        "employee_id": row["employee_id"],
                        "employee_name": row["employee_name"],
                        "process_id": row["process_id"],
                        "process_name": row["process_name"],
                        "process_code": row["process_code"],
                        "project_id": row["project_id"],
                        "project_name": row["project_name"],
                        "project_code": row["project_code"],
                        "title": row["title"],
                        "description": row["description"],
                        "type": row["type"],
                        "score": row["score"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

            conn.close()
            return jsonify(occurrences)
        except Exception as e:
            logger.info(f"Erro ao listar ocorrências: {e}")
            import traceback

            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    # POST - Create occurrence
    payload = request.get_json(silent=True) or {}

    employee_id = payload.get("employee_id")
    process_id = payload.get("process_id")
    project_id = payload.get("project_id")
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    occ_type = (payload.get("type") or "").strip()
    score = payload.get("score", 0)

    if not employee_id:
        return jsonify({"success": False, "message": "Colaborador é obrigatório."}), 400

    if not title:
        return jsonify({"success": False, "message": "Título é obrigatório."}), 400

    if occ_type not in ["positive", "negative"]:
        return (
            jsonify(
                {"success": False, "message": 'Tipo deve ser "positive" ou "negative".'}
            ),
            400,
        )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO occurrences 
            (company_id, employee_id, process_id, project_id, title, description, type, score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                company_id,
                employee_id,
                process_id,
                project_id,
                title,
                description,
                occ_type,
                score,
            ),
        )

        occurrence_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Ocorrência criada com sucesso!",
                    "id": occurrence_id,
                }
            ),
            201,
        )
    except Exception as e:
        logger.info(f"Erro ao criar ocorrência: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route(
    "/api/companies/<int:company_id>/occurrences/<int:occurrence_id>",
    methods=["PUT", "DELETE"],
)
def api_company_occurrence(company_id: int, occurrence_id: int):
    """Update or delete an occurrence"""
    if request.method == "PUT":
        payload = request.get_json(silent=True) or {}

        employee_id = payload.get("employee_id")
        process_id = payload.get("process_id")
        project_id = payload.get("project_id")
        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        occ_type = (payload.get("type") or "").strip()
        score = payload.get("score", 0)

        if not employee_id:
            return (
                jsonify({"success": False, "message": "Colaborador é obrigatório."}),
                400,
            )

        if not title:
            return jsonify({"success": False, "message": "Título é obrigatório."}), 400

        if occ_type not in ["positive", "negative"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": 'Tipo deve ser "positive" ou "negative".',
                    }
                ),
                400,
            )

        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE occurrences
                SET employee_id = %s, process_id = %s, project_id = %s, title = ?, 
                    description = ?, type = ?, score = ?
                WHERE id = %s AND company_id = %s
            """,
                (
                    employee_id,
                    process_id,
                    project_id,
                    title,
                    description,
                    occ_type,
                    score,
                    occurrence_id,
                    company_id,
                ),
            )

            conn.commit()
            conn.close()

            return jsonify(
                {"success": True, "message": "Ocorrência atualizada com sucesso!"}
            )
        except Exception as e:
            logger.info(f"Erro ao atualizar ocorrência: {e}")
            import traceback

            traceback.print_exc()
            return jsonify({"success": False, "message": str(e)}), 500

    # DELETE
    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM occurrences WHERE id = %s AND company_id = %s",
            (occurrence_id, company_id),
        )

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Ocorrência excluída com sucesso!"})
    except Exception as e:
        logger.info(f"Erro ao excluir ocorrência: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


# ====================================
# EFFICIENCY API
# ====================================


@app.route("/api/companies/<int:company_id>/efficiency/collaborators", methods=["GET"])
def api_company_efficiency_collaborators(company_id: int):
    """Get efficiency data aggregated by collaborator"""
    try:
        from database.postgres_helper import connect as pg_connect
        import json
        from datetime import datetime, date

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        # Get all employees
        cursor.execute(
            "SELECT id, name FROM employees WHERE company_id = %s ORDER BY name",
            (company_id,),
        )
        employees = [dict(row) for row in cursor.fetchall()]

        today = date.today()
        efficiency_data = []

        for employee in employees:
            employee_id = employee["id"]
            employee_name = employee["name"]

            # Initialize counters
            data = {
                "employee_id": employee_id,
                "employee_name": employee_name,
                "in_progress": {"total": 0, "on_time": 0, "late": 0},
                "completed": {"total": 0, "on_time": 0, "late": 0},
                "positive_occurrences": {"count": 0, "score": 0},
                "negative_occurrences": {"count": 0, "score": 0},
            }

            # 1. Get project activities (where employee is responsible)
            cursor.execute(
                """
                SELECT cp.id as project_id, cp.activities
                FROM company_projects cp
                WHERE cp.company_id = %s AND cp.responsible_id = %s
                """,
                (company_id, employee_id),
            )

            for project_row in cursor.fetchall():
                activities_json = project_row["activities"]
                if activities_json:
                    try:
                        activities = (
                            json.loads(activities_json)
                            if isinstance(activities_json, str)
                            else activities_json
                        )
                        if isinstance(activities, list):
                            for activity in activities:
                                stage = activity.get("stage", "inbox")
                                due_date_str = activity.get("when", "")

                                # Check if late
                                is_late = False
                                if due_date_str:
                                    try:
                                        due_date = datetime.fromisoformat(
                                            due_date_str.replace("Z", "+00:00")
                                        ).date()
                                        is_late = due_date < today
                                    except Exception as exc:
                                        try:
                                            due_date = datetime.strptime(
                                                due_date_str, "%Y-%m-%d"
                                            ).date()
                                            is_late = due_date < today
                                        except Exception as exc:
                                            pass

                                # Count by status
                                if stage == "completed":
                                    data["completed"]["total"] += 1
                                    if is_late:
                                        data["completed"]["late"] += 1
                                    else:
                                        data["completed"]["on_time"] += 1
                                elif stage in ["executing", "waiting"]:
                                    data["in_progress"]["total"] += 1
                                    if is_late:
                                        data["in_progress"]["late"] += 1
                                    else:
                                        data["in_progress"]["on_time"] += 1
                    except Exception as e:
                        logger.info(f"Error parsing activities: {e}")

            # 2. Get process instances (where employee is assigned)
            cursor.execute(
                """
                SELECT pi.id, pi.status, pi.due_date, pi.assigned_collaborators, pi.completed_at
                FROM process_instances pi
                WHERE pi.company_id = %s
                """,
                (company_id,),
            )

            for inst_row in cursor.fetchall():
                # Check if employee is assigned
                collab_json = inst_row["assigned_collaborators"]
                is_assigned = False

                if collab_json:
                    try:
                        collabs = (
                            json.loads(collab_json)
                            if isinstance(collab_json, str)
                            else collab_json
                        )
                        if isinstance(collabs, list):
                            is_assigned = any(
                                c.get("id") == employee_id
                                or c.get("name") == employee_name
                                for c in collabs
                            )
                    except Exception as exc:
                        pass

                if not is_assigned:
                    continue

                status = inst_row["status"]
                due_date_str = inst_row["due_date"]
                completed_at_str = inst_row["completed_at"]

                # Check if late
                is_late = False
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(
                            due_date_str.replace("Z", "+00:00")
                        ).date()

                        if status == "completed" and completed_at_str:
                            try:
                                completed_at = datetime.fromisoformat(
                                    completed_at_str.replace("Z", "+00:00")
                                ).date()
                                is_late = completed_at > due_date
                            except Exception as exc:
                                is_late = False
                        else:
                            is_late = due_date < today
                    except Exception as exc:
                        pass

                # Count by status
                if status == "completed":
                    data["completed"]["total"] += 1
                    if is_late:
                        data["completed"]["late"] += 1
                    else:
                        data["completed"]["on_time"] += 1
                elif status in ["in_progress", "executing"]:
                    data["in_progress"]["total"] += 1
                    if is_late:
                        data["in_progress"]["late"] += 1
                    else:
                        data["in_progress"]["on_time"] += 1

            # 3. Get occurrences
            cursor.execute(
                """
                SELECT type, score
                FROM occurrences
                WHERE company_id = %s AND employee_id = %s
                """,
                (company_id, employee_id),
            )

            for occ_row in cursor.fetchall():
                occ_type = occ_row["type"]
                score = occ_row["score"] or 0

                if occ_type == "positive":
                    data["positive_occurrences"]["count"] += 1
                    data["positive_occurrences"]["score"] += score
                elif occ_type == "negative":
                    data["negative_occurrences"]["count"] += 1
                    data["negative_occurrences"]["score"] += score

            efficiency_data.append(data)

        conn.close()
        return jsonify(efficiency_data)

    except Exception as e:
        logger.info(f"Erro ao buscar dados de eficiência: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route(
    "/api/companies/<int:company_id>/processes/<int:process_id>/report", methods=["GET"]
)
def api_generate_process_report(company_id: int, process_id: int):
    """Generate HTML report for process documentation"""
    from datetime import datetime

    process = db.get_process(process_id)
    if not process or process.get("company_id") != company_id:
        return jsonify({"success": False, "error": "process_not_found"}), 404

    # Capturar parâmetros da URL (seções selecionadas)
    sections = request.args.getlist("sections")

    # ========================================
    # GERADOR DE RELATÓRIOS COM TEMPLATE ESPECÍFICO
    # ========================================
    try:
        # Forçar reload do módulo para garantir que está usando código atualizado
        import sys
        import importlib

        if "relatorios.generators.process_pop" in sys.modules:
            importlib.reload(sys.modules["relatorios.generators.process_pop"])
        from relatorios.generators.process_pop import ProcessPOPReport

        logger.info(
            f">> Gerando relatório de processo - Empresa: {company_id}, Processo: {process_id}"
        )
        logger.info(
            f">> Seções selecionadas: {', '.join(sections) if sections else 'Todas'}"
        )

        # Determinar modelo de página (se não especificado, usa configuração padrão)
        model_id = request.args.get("model", type=int)

        # Criar gerador aplicando o modelo desejado
        report = ProcessPOPReport(report_model_id=model_id)

        # Configurar seções baseado na seleção do usuário
        report.configure(
            flow="flow" in sections,
            activities="pop" in sections,
            routines="routine" in sections,
            indicators="indicators" in sections,
        )

        logger.info(
            f">> [DEBUG] Configuração: flow={report.include_flow}, routines={report.include_routines}, indicators={report.include_indicators}, activities={report.include_activities}"
        )

        # Gerar HTML usando o template específico
        html_content = report.generate_html(
            company_id=company_id, process_id=process_id
        )

        logger.info(f">> Relatório gerado com sucesso!")

        # Retornar HTML
        response = app.make_response(html_content)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    except Exception as e:
        logger.info(f">> ERRO ao gerar relatório: {e}")
        import traceback

        traceback.print_exc()
        error_trace = traceback.format_exc()

        # Retornar HTML formatado para exibir o erro de forma amigável
        error_html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erro ao Gerar Relatório</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 15px 10px;
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
        }}
        .error-container {{
            max-width: 700px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        .error-header {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .error-header h1 {{
            margin: 0 0 8px 0;
            font-size: 22px;
            font-weight: 700;
        }}
        .error-header p {{
            margin: 0;
            opacity: 0.9;
            font-size: 13px;
        }}
        .error-body {{
            padding: 20px;
        }}
        .error-message {{
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .error-message h2 {{
            margin: 0 0 8px 0;
            color: #991b1b;
            font-size: 15px;
        }}
        .error-message code {{
            background: #fee2e2;
            padding: 2px 4px;
            border-radius: 3px;
            color: #7f1d1d;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }}
        .error-details {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .error-details h3 {{
            margin: 0 0 10px 0;
            color: #374151;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .error-details pre {{
            background: #1f2937;
            color: #f3f4f6;
            padding: 12px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 11px;
            line-height: 1.4;
            margin: 0;
            max-height: 300px;
            overflow-y: auto;
        }}
        .actions {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .button {{
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
            font-size: 13px;
        }}
        .button-primary {{
            background: #3b82f6;
            color: white;
        }}
        .button-primary:hover {{
            background: #2563eb;
            transform: translateY(-1px);
            box-shadow: 0 3px 10px rgba(59, 130, 246, 0.4);
        }}
        .button-secondary {{
            background: #f3f4f6;
            color: #374151;
        }}
        .button-secondary:hover {{
            background: #e5e7eb;
        }}
        .icon {{
            font-size: 36px;
            margin-bottom: 8px;
        }}
        .toggle-trace {{
            cursor: pointer;
            color: #3b82f6;
            text-decoration: underline;
            background: none;
            border: none;
            padding: 0;
            font-size: 12px;
        }}
        .toggle-trace:hover {{
            color: #2563eb;
        }}
        #traceDetails {{
            display: none;
            margin-top: 10px;
        }}
        #traceDetails.show {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-header">
            <div class="icon">??</div>
            <h1>Erro ao Gerar Relatório</h1>
            <p>Ocorreu um problema durante a geração do relatório do processo</p>
        </div>
        
        <div class="error-body">
            <div class="error-message">
                <h2>Mensagem do Erro:</h2>
                <code>{str(e)}</code>
            </div>
            
            <div class="error-details">
                <h3>
                    <span>??</span>
                    <span>Detalhes Técnicos</span>
                </h3>
                <p style="margin-bottom: 10px; color: #6b7280;">
                    <button class="toggle-trace" onclick="toggleTrace()">? Mostrar stack trace completo</button>
                </p>
                <div id="traceDetails">
                    <pre>{error_trace}</pre>
                </div>
            </div>
            
            <div class="actions">
                <button class="button button-primary" onclick="window.history.back()">
                    ? Voltar para o Processo
                </button>
                <button class="button button-secondary" onclick="window.location.reload()">
                    ?? Tentar Novamente
                </button>
            </div>
        </div>
    </div>
    
    <script>
        function toggleTrace() {{
            const details = document.getElementById('traceDetails');
            const button = document.querySelector('.toggle-trace');
            if (details.classList.contains('show')) {{
                details.classList.remove('show');
                button.textContent = '? Mostrar stack trace completo';
            }} else {{
                details.classList.add('show');
                button.textContent = '? Ocultar stack trace';
            }}
        }}
    </script>
</body>
</html>
        """

        response = app.make_response(error_html)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response, 500


@app.route("/__routes")
def __routes():
    # Utilitário de diagnóstico para listar rotas ativas
    routes = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        routes.append(
            {
                "rule": rule.rule,
                "endpoint": rule.endpoint,
                "methods": sorted(
                    m for m in rule.methods if m not in ("HEAD", "OPTIONS")
                ),
            }
        )
    return jsonify({"count": len(routes), "routes": routes})


# ===== ROTINAS API =====


# Rotas para Rotinas
@app.route("/api/companies/<int:company_id>/routines", methods=["GET"])
def api_get_routines(company_id: int):
    """Get all routines for a company"""
    try:
        routines = db.get_routines(company_id)
        return jsonify({"success": True, "routines": routines})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/companies/<int:company_id>/routines", methods=["POST"])
def api_create_routine(company_id: int):
    """Create a new routine"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        description = data.get("description", "")

        if not name:
            return jsonify({"success": False, "error": "Nome é obrigatório"}), 400

        routine_id = db.create_routine(company_id, name, description)

        if routine_id:
            return jsonify({"success": True, "routine_id": routine_id})
        else:
            return jsonify({"success": False, "error": "Erro ao criar rotina"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/routines/<int:routine_id>", methods=["GET"])
def api_get_routine(routine_id: int):
    """Get a specific routine"""
    try:
        routine = db.get_routine(routine_id)
        if routine:
            return jsonify({"success": True, "routine": routine})
        else:
            return jsonify({"success": False, "error": "Rotina não encontrada"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/routines/<int:routine_id>", methods=["PUT"])
def api_update_routine(routine_id: int):
    """Update a routine"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        description = data.get("description", "")

        if not name:
            return jsonify({"success": False, "error": "Nome é obrigatório"}), 400

        success = db.update_routine(routine_id, name, description)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Erro ao atualizar rotina"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/routines/<int:routine_id>", methods=["DELETE"])
def api_delete_routine(routine_id: int):
    """Delete a routine"""
    try:
        success = db.delete_routine(routine_id)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Erro ao excluir rotina"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Rotas para Triggers (Gatilhos)
@app.route("/api/routines/<int:routine_id>/triggers", methods=["GET"])
def api_get_routine_triggers(routine_id: int):
    """Get all triggers for a routine"""
    try:
        triggers = db.get_routine_triggers(routine_id)
        return jsonify({"success": True, "triggers": triggers})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/routines/<int:routine_id>/triggers", methods=["POST"])
def api_create_routine_trigger(routine_id: int):
    """Create a new trigger for a routine"""
    try:
        data = request.get_json(silent=True) or {}

        trigger_type = data.get("trigger_type")
        trigger_value = data.get("trigger_value")
        deadline_value = data.get("deadline_value")
        deadline_unit = data.get("deadline_unit")

        if not all([trigger_type, trigger_value, deadline_value, deadline_unit]):
            return (
                jsonify(
                    {"success": False, "error": "Todos os campos são obrigatórios"}
                ),
                400,
            )

        # Validar trigger_type
        if trigger_type not in ["daily", "weekly", "monthly", "yearly"]:
            return jsonify({"success": False, "error": "Tipo de gatilho inválido"}), 400

        # Validar deadline_unit
        if deadline_unit not in ["hours", "days"]:
            return (
                jsonify({"success": False, "error": "Unidade de prazo inválida"}),
                400,
            )

        trigger_id = db.create_routine_trigger(
            routine_id, trigger_type, trigger_value, int(deadline_value), deadline_unit
        )

        if trigger_id:
            return jsonify({"success": True, "trigger_id": trigger_id})
        else:
            return jsonify({"success": False, "error": "Erro ao criar gatilho"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/triggers/<int:trigger_id>", methods=["PUT"])
def api_update_routine_trigger(trigger_id: int):
    """Update a routine trigger"""
    try:
        data = request.get_json(silent=True) or {}

        trigger_type = data.get("trigger_type")
        trigger_value = data.get("trigger_value")
        deadline_value = data.get("deadline_value")
        deadline_unit = data.get("deadline_unit")

        if not all([trigger_type, trigger_value, deadline_value, deadline_unit]):
            return (
                jsonify(
                    {"success": False, "error": "Todos os campos são obrigatórios"}
                ),
                400,
            )

        success = db.update_routine_trigger(
            trigger_id, trigger_type, trigger_value, int(deadline_value), deadline_unit
        )

        if success:
            return jsonify({"success": True})
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar gatilho"}),
                500,
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/triggers/<int:trigger_id>", methods=["DELETE"])
def api_delete_routine_trigger(trigger_id: int):
    """Delete a routine trigger"""
    try:
        success = db.delete_routine_trigger(trigger_id)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Erro ao excluir gatilho"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Rotas para Tasks (Tarefas)
@app.route("/api/companies/<int:company_id>/routine-tasks", methods=["GET"])
def api_get_routine_tasks(company_id: int):
    """Get routine tasks for a company"""
    try:
        status = request.args.get("status")
        tasks = db.get_routine_tasks(company_id, status)
        return jsonify({"success": True, "tasks": tasks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/companies/<int:company_id>/routine-tasks/overdue", methods=["GET"])
def api_get_overdue_tasks(company_id: int):
    """Get overdue tasks for a company"""
    try:
        tasks = db.get_overdue_tasks(company_id)
        return jsonify({"success": True, "tasks": tasks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/companies/<int:company_id>/routine-tasks/upcoming", methods=["GET"])
def api_get_upcoming_tasks(company_id: int):
    """Get upcoming tasks for a company"""
    try:
        days = request.args.get("days", 7, type=int)
        tasks = db.get_upcoming_tasks(company_id, days)
        return jsonify({"success": True, "tasks": tasks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/routine-tasks/<int:task_id>/status", methods=["PUT"])
def api_update_task_status(task_id: int):
    """Update the status of a routine task"""
    try:
        data = request.get_json(silent=True) or {}
        status = data.get("status")
        completed_by = data.get("completed_by")
        notes = data.get("notes")

        if not status:
            return jsonify({"success": False, "error": "Status é obrigatório"}), 400

        if status not in ["pending", "in_progress", "completed", "overdue"]:
            return jsonify({"success": False, "error": "Status inválido"}), 400

        success = db.update_routine_task_status(task_id, status, completed_by, notes)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Erro ao atualizar status"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Rota para página de gerenciamento de rotinas DOS PROCESSOS
@app.route("/companies/<int:company_id>/routines")
def routines_management(company_id: int):
    """Routine management page - Nova versão com processos"""
    from modules.grv import grv_navigation

    company = db.get_company(company_id)
    if not company:
        abort(404)

    # Buscar processos da empresa para o select
    from database.postgres_helper import connect as pg_connect

    conn = pg_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, code, name FROM processes WHERE company_id = %s ORDER BY code",
        (company_id,),
    )
    processes = [
        {"id": row[0], "code": row[1], "name": row[2]} for row in cursor.fetchall()
    ]
    conn.close()

    return render_template(
        "process_routines.html",
        company=company,
        processes=processes,
        navigation=grv_navigation(),
        active_id="process-routines",
    )


@app.route("/companies/<int:company_id>/routines/<routine_id>")
def routine_details(company_id: int, routine_id):
    """Routine details/creation page with tabs (Routine Data + Collaborators)"""
    from modules.grv import grv_navigation

    company = db.get_company(company_id)
    if not company:
        abort(404)

    from database.postgres_helper import connect as pg_connect

    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()

    # Buscar todos os processos para o select
    cursor.execute(
        "SELECT id, code, name FROM processes WHERE company_id = %s ORDER BY code",
        (company_id,),
    )
    processes = [
        {"id": row[0], "code": row[1], "name": row[2]} for row in cursor.fetchall()
    ]

    # Se routine_id = 'new', criar nova rotina
    if routine_id == "new":
        routine = {
            "id": None,
            "name": "",
            "description": "",
            "process_id": None,
            "schedule_type": "weekly",
            "schedule_value": "",
            "deadline_days": 0,
            "deadline_hours": 0,
        }
        conn.close()
        return render_template(
            "routine_details.html",
            company=company,
            routine=routine,
            processes=processes,
            is_new=True,
            navigation=grv_navigation(),
            active_id="process-routines",
        )

    # Caso contrário, buscar rotina existente
    cursor.execute(
        """
        SELECT r.*, p.code as process_code, p.name as process_name
        FROM routines r
        LEFT JOIN processes p ON r.process_id = p.id
        WHERE r.id = %s AND r.company_id = %s
    """,
        (int(routine_id), company_id),
    )

    routine_row = cursor.fetchone()
    if not routine_row:
        conn.close()
        abort(404)

    routine = dict(routine_row)
    conn.close()

    return render_template(
        "routine_details.html",
        company=company,
        routine=routine,
        processes=processes,
        is_new=False,
        navigation=grv_navigation(),
        active_id="process-routines",
    )


# API - Listar rotinas de processos
@app.route("/api/companies/<int:company_id>/process-routines", methods=["GET"])
def api_get_process_routines(company_id: int):
    """Get all process routines for a company"""
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT r.id, r.name, r.description, r.process_id, r.schedule_type, 
                   r.schedule_value, r.deadline_days, r.deadline_hours, r.deadline_date,
                   p.code as process_code, p.name as process_name
            FROM routines r
            LEFT JOIN processes p ON r.process_id = p.id
            WHERE r.company_id = %s
            ORDER BY r.created_at DESC
        """,
            (company_id,),
        )

        routines = []
        for row in cursor.fetchall():
            routines.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "process_id": row[3],
                    "schedule_type": row[4],
                    "schedule_value": row[5],
                    "deadline_days": row[6],
                    "deadline_hours": row[7],
                    "deadline_date": row[8],
                    "process_code": row[9],
                    "process_name": f"{row[9]} - {row[10]}"
                    if row[9] and row[10]
                    else row[10] or "Não vinculado",
                }
            )

        conn.close()
        return jsonify({"success": True, "routines": routines})

    except Exception as e:
        logger.info(f"Erro ao buscar rotinas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# API - Criar rotina de processo
@app.route("/api/companies/<int:company_id>/process-routines", methods=["POST"])
def api_create_process_routine(company_id: int):
    """Create a new process routine"""
    try:
        data = request.get_json(silent=True) or {}

        name = data.get("name", "").strip()
        if not name:
            return jsonify({"success": False, "message": "Nome é obrigatório"}), 400

        process_id = data.get("process_id")
        if not process_id:
            return jsonify({"success": False, "message": "Processo é obrigatório"}), 400

        schedule_type = data.get("schedule_type")
        if not schedule_type:
            return (
                jsonify(
                    {"success": False, "message": "Tipo de agendamento é obrigatório"}
                ),
                400,
            )

        from database.postgres_helper import connect as pg_connect
        from datetime import datetime as dt

        conn = pg_connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO routines (
                company_id, name, description, process_id,
                schedule_type, schedule_value, deadline_days, deadline_hours, deadline_date,
                is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                company_id,
                name,
                data.get("description", ""),
                process_id,
                schedule_type,
                data.get("schedule_value"),
                data.get("deadline_days", 0),
                data.get("deadline_hours", 0),
                data.get("deadline_date"),
                1,  # is_active (INTEGER: 1=ativo, 0=inativo)
                dt.utcnow(),  # created_at
                dt.utcnow(),  # updated_at
            ),
        )

        routine_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return (
            jsonify(
                {
                    "success": True,
                    "routine_id": routine_id,
                    "message": "Rotina cadastrada com sucesso",
                }
            ),
            201,
        )

    except Exception as e:
        logger.info(f"Erro ao criar rotina: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


# API - Deletar rotina de processo
@app.route(
    "/api/companies/<int:company_id>/process-routines/<int:routine_id>",
    methods=["DELETE"],
)
def api_delete_process_routine(company_id: int, routine_id: int):
    """Delete a process routine"""
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        cursor = conn.cursor()

        # Verificar se pertence à empresa
        cursor.execute(
            "SELECT id FROM routines WHERE id = %s AND company_id = %s",
            (routine_id, company_id),
        )
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Rotina não encontrada"}), 404

        # Deletar
        cursor.execute("DELETE FROM routines WHERE id = %s", (routine_id,))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Rotina excluída com sucesso"}), 200

    except Exception as e:
        logger.info(f"Erro ao deletar rotina: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route(
    "/api/companies/<int:company_id>/process-routines/<int:routine_id>", methods=["PUT"]
)
def api_update_process_routine(company_id: int, routine_id: int):
    """Update a process routine"""
    try:
        data = request.get_json(silent=True) or {}

        from database.postgres_helper import connect as pg_connect
        from datetime import datetime as dt

        conn = pg_connect()
        cursor = conn.cursor()

        # Verificar se pertence à empresa
        cursor.execute(
            "SELECT id FROM routines WHERE id = %s AND company_id = %s",
            (routine_id, company_id),
        )
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Rotina não encontrada"}), 404

        cursor.execute(
            """
            UPDATE routines SET
                name = %s,
                description = %s,
                process_id = %s,
                schedule_type = %s,
                schedule_value = %s,
                deadline_days = %s,
                deadline_hours = %s,
                updated_at = %s
            WHERE id = %s AND company_id = %s
        """,
            (
                data.get("name"),
                data.get("description", ""),
                data.get("process_id"),
                data.get("schedule_type"),
                data.get("schedule_value"),
                data.get("deadline_days", 0),
                data.get("deadline_hours", 0),
                dt.utcnow(),  # updated_at
                routine_id,
                company_id,
            ),
        )

        conn.commit()
        conn.close()

        return (
            jsonify({"success": True, "message": "Rotina atualizada com sucesso"}),
            200,
        )

    except Exception as e:
        logger.info(f"Erro ao atualizar rotina: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route(
    "/api/processes/<int:process_id>/routines-with-collaborators", methods=["GET"]
)
def api_get_process_routines_with_collaborators(process_id: int):
    """Get all routines for a process with their collaborators"""
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        # Buscar rotinas do processo
        cursor.execute(
            """
            SELECT r.id, r.name, r.description, r.schedule_type, r.schedule_value,
                   r.deadline_days, r.deadline_hours, r.deadline_date
            FROM routines r
            WHERE r.process_id = %s
            ORDER BY r.created_at DESC
        """,
            (process_id,),
        )

        routines = []
        for row in cursor.fetchall():
            routine_dict = dict(row)
            routine_id = routine_dict["id"]

            # Buscar colaboradores desta rotina
            cursor.execute(
                """
                SELECT rc.*, e.name as employee_name, e.email as employee_email
                FROM routine_collaborators rc
                JOIN employees e ON rc.employee_id = e.id
                WHERE rc.routine_id = %s
                ORDER BY e.name
            """,
                (routine_id,),
            )

            collaborators = [dict(c) for c in cursor.fetchall()]
            routine_dict["collaborators"] = collaborators

            # Calcular total de horas
            total_hours = sum(c["hours_used"] for c in collaborators)
            routine_dict["total_hours"] = total_hours

            routines.append(routine_dict)

        conn.close()
        return jsonify({"success": True, "routines": routines}), 200

    except Exception as e:
        logger.info(f"Erro ao buscar rotinas com colaboradores: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ===== APIs para Colaboradores das Rotinas =====


@app.route("/api/routines/<int:routine_id>/collaborators", methods=["GET"])
def api_get_routine_collaborators(routine_id: int):
    """Get all collaborators for a routine"""
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT rc.*, e.name as employee_name, e.email as employee_email
            FROM routine_collaborators rc
            JOIN employees e ON rc.employee_id = e.id
            WHERE rc.routine_id = %s
            ORDER BY e.name
        """,
            (routine_id,),
        )

        collaborators = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({"success": True, "collaborators": collaborators}), 200

    except Exception as e:
        logger.info(f"Erro ao buscar colaboradores: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/routines/<int:routine_id>/collaborators", methods=["POST"])
def api_add_routine_collaborator(routine_id: int):
    """Add a collaborator to a routine"""
    try:
        from database.postgres_helper import connect as pg_connect

        data = request.get_json()

        conn = pg_connect()
        cursor = conn.cursor()

        ensure_routine_collaborators_sequence(cursor)

        cursor.execute("SELECT nextval('routine_collaborators_id_seq')")
        seq_row = cursor.fetchone()
        if not seq_row or seq_row[0] is None:
            conn.rollback()
            conn.close()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Falha ao gerar identificador da rotina",
                    }
                ),
                500,
            )
        generated_id = seq_row[0]

        cursor.execute(
            """
            INSERT INTO routine_collaborators (id, routine_id, employee_id, hours_used, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                generated_id,
                routine_id,
                data.get("employee_id"),
                data.get("hours_used"),
                data.get("notes", ""),
            ),
        )

        collaborator_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return (
            jsonify(
                {
                    "success": True,
                    "id": collaborator_id,
                    "message": "Colaborador adicionado com sucesso",
                }
            ),
            201,
        )

    except Exception as e:
        logger.info(f"Erro ao adicionar colaborador: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route(
    "/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>",
    methods=["PUT"],
)
def api_update_routine_collaborator(routine_id: int, collaborator_id: int):
    """Update a routine collaborator"""
    try:
        from database.postgres_helper import connect as pg_connect

        data = request.get_json()

        conn = pg_connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE routine_collaborators
            SET employee_id = %s,
                hours_used = %s,
                notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND routine_id = %s
        """,
            (
                data.get("employee_id"),
                data.get("hours_used"),
                data.get("notes", ""),
                collaborator_id,
                routine_id,
            ),
        )

        conn.commit()
        conn.close()

        return (
            jsonify({"success": True, "message": "Colaborador atualizado com sucesso"}),
            200,
        )

    except Exception as e:
        logger.info(f"Erro ao atualizar colaborador: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route(
    "/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>",
    methods=["DELETE"],
)
def api_delete_routine_collaborator(routine_id: int, collaborator_id: int):
    """Delete a routine collaborator"""
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM routine_collaborators WHERE id = %s AND routine_id = %s",
            (collaborator_id, routine_id),
        )

        conn.commit()
        conn.close()

        return (
            jsonify({"success": True, "message": "Colaborador removido com sucesso"}),
            200,
        )

    except Exception as e:
        logger.info(f"Erro ao deletar colaborador: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# Rota para página de tarefas da rotina
@app.route("/companies/<int:company_id>/routine-tasks")
def routine_tasks_page(company_id: int):
    """Routine tasks management page"""
    company = db.get_company(company_id)
    if not company:
        abort(404)

    return render_template("routine_tasks.html", company=company)


# Rota de teste para debug
@app.route("/test-routines-modal")
def test_routines_modal():
    """Test page for routines modal"""
    return render_template("test_routines_modal.html")


@app.route("/plans/<plan_id>")
def plan_dashboard(plan_id: str):
    """Plan dashboard - main dashboard for a specific plan"""
    plan, company = _plan_for(plan_id)

    # Verificar se é planejamento de implantação e redirecionar
    plan_mode = (plan.get("plan_mode") or "evolucao").lower()
    if plan_mode == "implantacao":
        return redirect(url_for("pev.pev_implantacao_overview", plan_id=plan_id))

    navigation = _navigation(plan_id, "dashboard")

    # Core datasets used across the dashboard
    participants = db.get_participants(int(plan_id))
    drivers = db.get_drivers(int(plan_id))
    okrs_global = db.get_global_okr_records(int(plan_id), "approval")
    okrs_area = []
    final_area_status = db.get_section_status(int(plan_id), "final-area-okr")
    if final_area_status and final_area_status.get("notes"):
        try:
            area_data = json.loads(final_area_status["notes"])
            if isinstance(area_data, dict) and "okrs" in area_data:
                okrs_area = area_data["okrs"]
        except Exception:
            okrs_area = []
    if not isinstance(okrs_area, list):
        okrs_area = []
    projects = db.get_projects(int(plan_id))

    # Company information for progress calculations
    company_data_row = db.get_company_data(int(plan_id)) or {}
    try:
        company_financials = json.loads(company_data_row.get("financials") or "[]")
    except (json.JSONDecodeError, TypeError, AttributeError):
        company_financials = []
    if not isinstance(company_financials, list):
        company_financials = []
    process_map_file = company_data_row.get("process_map_file")
    org_chart_file = company_data_row.get("org_chart_file")

    def is_filled(value, treat_zero=False):
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (int, float)):
            if treat_zero:
                return True
            return value > 0
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) > 0
        return True

    def filled_ratio(values, treat_zero_as_filled=False):
        values = list(values)
        if not values:
            return 0
        filled = sum(1 for value in values if is_filled(value, treat_zero_as_filled))
        return int(round((filled / len(values)) * 100))

    company_identity_progress = filled_ratio(
        [
            company_data_row.get("trade_name"),
            company_data_row.get("legal_name"),
            company_data_row.get("cnpj"),
        ]
    )
    company_coverage_progress = filled_ratio(
        [
            company_data_row.get("coverage_physical"),
            company_data_row.get("coverage_online"),
            company_data_row.get("experience_total"),
            company_data_row.get("experience_segment"),
        ]
    )
    company_culture_progress = filled_ratio(
        [
            company_data_row.get("mission"),
            company_data_row.get("vision"),
            company_data_row.get("company_values"),
        ]
    )
    company_structure_progress = filled_ratio(
        [
            company_data_row.get("headcount_strategic"),
            company_data_row.get("headcount_tactical"),
            company_data_row.get("headcount_operational"),
        ]
    )
    company_finance_progress = 100 if company_financials else 0

    # Section status map for consolidated progress tree
    section_keys = [
        "participants",
        "interviews",
        "vision",
        "market",
        "company",
        "alignment",
        "directionals",
        "alignments-found",
        "misalignments-critical",
        "preliminary-analysis",
        "workshop-final-analysis",
        "directionals-ai",
        "directionals-consultant",
        "directionals-approvals",
        "preliminary-analysis-okr",
        "workshop-final-okr",
        "okr-approvals",
        "preliminary-analysis-area-okr",
        "area-okr-workshop",
        "final-area-okr",
        "projects",
        "projects-analysis",
    ]
    section_statuses = {
        key: db.get_section_status(int(plan_id), key) for key in section_keys
    }

    STATUS_LABELS = {
        "pending": "Não iniciado",
        "in_progress": "Em andamento",
        "completed": "Concluído",
    }

    def section_value(name):
        status = section_statuses.get(name)
        if not status:
            return 0
        return 100 if status.get("status") == "closed" else 0

    def section_has_record(name):
        return section_statuses.get(name) is not None

    def status_from_value(value, has_record=False):
        if value >= 100:
            return "completed"
        if value <= 0:
            return "in_progress" if has_record else "pending"
        return "in_progress"

    def make_leaf(node_id, label, value, has_record=False, meta=None):
        status_key = status_from_value(value, has_record)
        node = {
            "id": node_id,
            "label": label,
            "value": int(value),
            "status": status_key,
            "status_label": STATUS_LABELS[status_key],
            "children": [],
        }
        if meta:
            node["meta"] = meta
        return node

    def make_section_leaf(node_id, label, section_name, meta=None):
        value = section_value(section_name)
        return make_leaf(
            node_id,
            label,
            value,
            has_record=section_has_record(section_name),
            meta=meta,
        )

    def make_branch(node_id, label, children):
        children = children or []
        if children:
            avg_value = int(
                round(sum(child["value"] for child in children) / len(children))
            )
            any_progress = any(child["status"] != "pending" for child in children)
        else:
            avg_value = 0
            any_progress = False
        status_key = status_from_value(avg_value, any_progress)
        return {
            "id": node_id,
            "label": label,
            "value": avg_value,
            "status": status_key,
            "status_label": STATUS_LABELS[status_key],
            "children": children,
        }

    # Build hierarchical progress structure
    organization_branch = make_branch(
        "organization",
        "Dados da Organização",
        [
            make_branch(
                "organization.cadastro",
                "Cadastro da empresa",
                [
                    make_leaf(
                        "organization.cadastro.identidade",
                        "Identidade e registro",
                        company_identity_progress,
                        has_record=company_identity_progress > 0,
                    ),
                    make_leaf(
                        "organization.cadastro.cobertura",
                        "Cobertura e experiência",
                        company_coverage_progress,
                        has_record=company_coverage_progress > 0,
                    ),
                    make_leaf(
                        "organization.cadastro.cultura",
                        "Cultura e propósito",
                        company_culture_progress,
                        has_record=company_culture_progress > 0,
                    ),
                    make_leaf(
                        "organization.cadastro.estrutura",
                        "Estrutura de pessoas",
                        company_structure_progress,
                        has_record=company_structure_progress > 0,
                    ),
                    make_leaf(
                        "organization.cadastro.financas",
                        "Indicadores financeiros",
                        company_finance_progress,
                        has_record=bool(company_financials),
                        meta=f"{len(company_financials)} linhas"
                        if company_financials
                        else None,
                    ),
                ],
            ),
            make_branch(
                "organization.documentos",
                "Documentos de apoio",
                [
                    make_leaf(
                        "organization.documentos.mapa-processos",
                        "Mapa de processos",
                        100 if process_map_file else 0,
                        has_record=bool(process_map_file),
                    ),
                    make_leaf(
                        "organization.documentos.organograma",
                        "Organograma",
                        100 if org_chart_file else 0,
                        has_record=bool(org_chart_file),
                    ),
                ],
            ),
        ],
    )

    participants_branch = make_branch(
        "participants",
        "Participantes",
        [
            make_branch(
                "participants.gestao",
                "Gestão de participantes",
                [
                    make_section_leaf(
                        "participants.gestao.cadastro",
                        "Cadastro e engajamento",
                        "participants",
                        meta=f"{len(participants)} cadastrados"
                        if participants
                        else None,
                    )
                ],
            )
        ],
    )

    drivers_branch = make_branch(
        "drivers",
        "Direcionadores",
        [
            make_branch(
                "drivers.diagnostico",
                "Diagnóstico inicial",
                [
                    make_section_leaf(
                        "drivers.diagnostico.entrevistas",
                        "Entrevistas com stakeholders",
                        "interviews",
                    ),
                    make_section_leaf(
                        "drivers.diagnostico.visao", "Visão dos sócios", "vision"
                    ),
                    make_section_leaf(
                        "drivers.diagnostico.mercado",
                        "Possibilidades do mercado",
                        "market",
                    ),
                    make_section_leaf(
                        "drivers.diagnostico.empresa",
                        "Possibilidades da empresa",
                        "company",
                    ),
                ],
            ),
            make_branch(
                "drivers.analise",
                "Análises e alinhamentos",
                [
                    make_section_leaf(
                        "drivers.analise.alinhamentos",
                        "Alinhamentos encontrados",
                        "alignment",
                    ),
                    make_section_leaf(
                        "drivers.analise.catalogo",
                        "Catálogo de alinhamentos",
                        "alignments-found",
                    ),
                    make_section_leaf(
                        "drivers.analise.desalinhamentos",
                        "Desalinhamentos críticos",
                        "misalignments-critical",
                    ),
                    make_section_leaf(
                        "drivers.analise.preliminar",
                        "Análise preliminar",
                        "preliminary-analysis",
                    ),
                    make_section_leaf(
                        "drivers.analise.workshop",
                        "Workshop final de análise",
                        "workshop-final-analysis",
                    ),
                ],
            ),
            make_branch(
                "drivers.formulacao",
                "Formulação e aprovações",
                [
                    make_section_leaf(
                        "drivers.formulacao.direcionadores",
                        "Direcionadores consolidados",
                        "directionals",
                        meta=f"{len(drivers)} direcionadores" if drivers else None,
                    ),
                    make_section_leaf(
                        "drivers.formulacao.ia",
                        "Recomendações da IA",
                        "directionals-ai",
                    ),
                    make_section_leaf(
                        "drivers.formulacao.consultor",
                        "Parecer do consultor",
                        "directionals-consultant",
                    ),
                    make_section_leaf(
                        "drivers.formulacao.aprovacoes",
                        "Aprovações e comunicação",
                        "directionals-approvals",
                    ),
                ],
            ),
        ],
    )

    okr_global_branch = make_branch(
        "okrs_global",
        "OKRs Globais",
        [
            make_branch(
                "okrs_global.ciclo",
                "Ciclo de construção",
                [
                    make_section_leaf(
                        "okrs_global.ciclo.preliminar",
                        "Diagnóstico preliminar",
                        "preliminary-analysis-okr",
                    ),
                    make_section_leaf(
                        "okrs_global.ciclo.workshop",
                        "Workshop de construção",
                        "workshop-final-okr",
                    ),
                    make_section_leaf(
                        "okrs_global.ciclo.aprovacao",
                        "Aprovação e publicação",
                        "okr-approvals",
                        meta=f"{len(okrs_global)} aprovados" if okrs_global else None,
                    ),
                ],
            )
        ],
    )

    okr_area_branch = make_branch(
        "okrs_area",
        "OKRs de Área",
        [
            make_branch(
                "okrs_area.ciclo",
                "Ciclo de construção",
                [
                    make_section_leaf(
                        "okrs_area.ciclo.preliminar",
                        "Diagnóstico preliminar",
                        "preliminary-analysis-area-okr",
                    ),
                    make_section_leaf(
                        "okrs_area.ciclo.workshop",
                        "Workshops por área",
                        "area-okr-workshop",
                    ),
                    make_section_leaf(
                        "okrs_area.ciclo.finalizacao",
                        "Encerramento e aprovação",
                        "final-area-okr",
                        meta=f"{len(okrs_area)} aprovados" if okrs_area else None,
                    ),
                ],
            )
        ],
    )

    projects_branch = make_branch(
        "projects_progress",
        "Projetos",
        [
            make_branch(
                "projects_progress.portfolio",
                "Portfólio estratégico",
                [
                    make_section_leaf(
                        "projects_progress.portfolio.identificacao",
                        "Identificação de iniciativas",
                        "projects",
                        meta=f"{len(projects)} projetos" if projects else None,
                    ),
                    make_section_leaf(
                        "projects_progress.portfolio.analise",
                        "Análises e priorização",
                        "projects-analysis",
                    ),
                ],
            )
        ],
    )

    progress_tree = make_branch(
        "plan",
        "Planejamento",
        [
            organization_branch,
            participants_branch,
            drivers_branch,
            okr_global_branch,
            okr_area_branch,
            projects_branch,
        ],
    )
    progress_overall = progress_tree["value"]

    # Plan data for dashboard header cards
    plan_data = {
        "id": plan["id"],
        "name": plan["name"],
        "company": plan["company"],
        "progress_overall": progress_overall,
        "owner": "Marcos Fenecio",
        "sponsor": "Fabiano Ferreira",
        "participants": len(participants),
        "directionals_count": len(drivers),
        "okr_global_count": len(okrs_global),
        "okr_area_count": len(okrs_area),
        "projects_count": len(projects),
        "locked": False,
        "start": "01/01/2025",
        "end": "31/12/2025",
        "company_industry": "Alimentício",
        "company_location": "São Paulo",
    }

    directionals_progress = section_value("directionals")
    directionals = []
    for driver in drivers[:3]:
        description = driver.get("description", "") if isinstance(driver, dict) else ""
        summary = (
            description[:100] + "..."
            if description and len(description) > 100
            else description
        )
        status_raw = driver.get("status") if isinstance(driver, dict) else None
        directionals.append(
            {
                "name": driver.get("title") if isinstance(driver, dict) else driver,
                "owner": driver.get("owner") if isinstance(driver, dict) else None,
                "summary": summary,
                "progress": directionals_progress,
                "status": status_raw.title()
                if isinstance(status_raw, str)
                else "Em andamento",
            }
        )

    return render_template(
        "plan_dashboard.html",
        plan=plan_data,
        company=company,
        navigation=navigation,
        active_section="dashboard",
        progress_tree=progress_tree,
        directionals=directionals,
        sections_progress=progress_tree,
    )


@app.route("/plans/<plan_id>/company")
def plan_company(plan_id: str):
    """Company data page"""
    plan, company = _plan_for(plan_id)
    navigation = _navigation(plan_id, "company")

    company_data_row = db.get_company_data(int(plan_id))
    company_section_status = db.get_section_status(int(plan_id), "company")
    company_section_open = (
        company_section_status is None
        or company_section_status.get("status", "open") == "open"
    )

    # Section status for analyses and summary
    analyses_section_status = db.get_section_status(int(plan_id), "analyses")
    analyses_section_open = (
        analyses_section_status is None
        or analyses_section_status.get("status", "open") == "open"
    )

    summary_section_status = db.get_section_status(int(plan_id), "summary")
    summary_section_open = (
        summary_section_status is None
        or summary_section_status.get("status", "open") == "open"
    )

    if company_data_row:
        try:
            cnaes = json.loads(company_data_row.get("cnaes") or "[]")
            if not isinstance(cnaes, list):
                cnaes = []
        except (TypeError, json.JSONDecodeError):
            cnaes = []

        financials_raw = company_data_row.get("financials")
        if isinstance(financials_raw, str):
            try:
                financials_list = json.loads(financials_raw or "[]")
            except (TypeError, json.JSONDecodeError):
                financials_list = []
        elif isinstance(financials_raw, list):
            financials_list = financials_raw
        else:
            financials_list = []

        normalized_financials = []
        for entry in financials_list:
            if not isinstance(entry, dict):
                continue
            revenue_decimal = _to_decimal(entry.get("revenue"))
            margin_decimal = _to_decimal(entry.get("margin"))
            normalized_financials.append(
                {
                    "line": entry.get("line", ""),
                    "revenue": float(revenue_decimal)
                    if revenue_decimal is not None
                    else 0,
                    "margin": float(margin_decimal)
                    if margin_decimal is not None
                    else 0,
                    "market": entry.get("market", ""),
                }
            )
        computed_revenue, computed_margin = _calculate_financial_totals(
            normalized_financials
        )
        stored_revenue = _to_decimal(company_data_row.get("financial_total_revenue"))
        stored_margin = _to_decimal(company_data_row.get("financial_total_margin"))

        total_revenue_value = (
            computed_revenue if computed_revenue is not None else stored_revenue
        )
        total_margin_value = (
            computed_margin if computed_margin is not None else stored_margin
        )
        if total_revenue_value is not None:
            total_revenue_value = total_revenue_value.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        if total_margin_value is not None:
            total_margin_value = total_margin_value.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        company_data = {
            "trade_name": company_data_row.get("trade_name") or "",
            "legal_name": company_data_row.get("legal_name") or "",
            "cnpj": company_data_row.get("cnpj") or "",
            "coverage_physical": company_data_row.get("coverage_physical")
            or "regional",
            "coverage_online": company_data_row.get("coverage_online")
            or "internet-nacional",
            "experience_total": company_data_row.get("experience_total"),
            "experience_segment": company_data_row.get("experience_segment"),
            "cnaes": cnaes,
            "mission": company_data_row.get("mission") or "",
            "vision": company_data_row.get("vision") or "",
            "company_values": company_data_row.get("company_values") or "",
            "headcount_strategic": company_data_row.get("headcount_strategic") or 0,
            "headcount_tactical": company_data_row.get("headcount_tactical") or 0,
            "headcount_operational": company_data_row.get("headcount_operational") or 0,
            "financials": normalized_financials,
            "financial_total_revenue": total_revenue_value,
            "financial_total_margin": total_margin_value,
            "process_map": company_data_row.get("process_map_file"),
            "org_chart": company_data_row.get("org_chart_file"),
            "other_information": company_data_row.get("other_information") or "",
            "ai_insights": company_data_row.get("ai_insights") or "",
            "consultant_analysis": company_data_row.get("consultant_analysis") or "",
        }
    else:
        company_data = {
            "trade_name": plan["company"],
            "legal_name": "",
            "cnpj": "",
            "coverage_physical": "regional",
            "coverage_online": "internet-nacional",
            "experience_total": "",
            "experience_segment": "",
            "cnaes": [],
            "mission": "",
            "vision": "",
            "company_values": "",
            "headcount_strategic": 0,
            "headcount_tactical": 0,
            "headcount_operational": 0,
            "financials": [],
            "financial_total_revenue": None,
            "financial_total_margin": None,
            "process_map": "",
            "org_chart": "",
            "other_information": "",
            "ai_insights": "",
            "consultant_analysis": "",
        }

    coverage_options = [
        {"id": "local", "label": "Local"},
        {"id": "regional", "label": "Regional"},
        {"id": "nacional", "label": "Nacional"},
        {"id": "internacional", "label": "Internacional"},
    ]

    online_options = [
        {"id": "sem-presenca-online", "label": "Sem presenca online"},
        {"id": "site-basico", "label": "Site basico"},
        {"id": "internet-nacional", "label": "Internet nacional"},
        {"id": "internet-global", "label": "Internet global"},
    ]

    coverage_physical_label = next(
        (
            opt["label"]
            for opt in coverage_options
            if opt["id"] == company_data.get("coverage_physical")
        ),
        "Nacional",
    )
    coverage_online_label = next(
        (
            opt["label"]
            for opt in online_options
            if opt["id"] == company_data.get("coverage_online")
        ),
        "Internet nacional",
    )

    filled_fields = sum(
        1
        for value in [
            company_data.get("trade_name"),
            company_data.get("legal_name"),
            company_data.get("cnpj"),
            company_data.get("mission"),
            company_data.get("vision"),
            company_data.get("company_values"),
        ]
        if value and str(value).strip()
    )
    progress = int((filled_fields / 6) * 100)
    plan["progress"] = progress

    return render_template(
        "plan_company.html",
        plan=plan,
        company=company,
        navigation=navigation,
        active_section="company",
        company_data=company_data,
        coverage_options=coverage_options,
        online_options=online_options,
        coverage_physical_label=coverage_physical_label,
        coverage_online_label=coverage_online_label,
        progress=progress,
        company_section_open=company_section_open,
        company_section_status=company_section_status,
        analyses_section_open=analyses_section_open,
        analyses_section_status=analyses_section_status,
        summary_section_open=summary_section_open,
        summary_section_status=summary_section_status,
    )


@app.route("/plans/<plan_id>/participants")
def plan_participants(plan_id: str):
    """Participants page"""
    plan, company = _plan_for(plan_id)
    navigation = _navigation(plan_id, "participants")

    # Get all employees from the company
    employees = db.list_employees(company["id"])

    # Get current participants of the plan
    participants = db.get_participants(int(plan_id))

    # Create a set of employee_ids that are already participants
    participant_employee_ids = {
        p.get("employee_id") for p in participants if p.get("employee_id")
    }

    # Mark which employees are participants
    for emp in employees:
        emp["is_participant"] = emp["id"] in participant_employee_ids

    # Get participants section status
    participants_section_status = db.get_section_status(int(plan_id), "participants")
    participants_section_open = (
        participants_section_status is None
        or participants_section_status.get("status", "open") == "open"
    )

    # Statistics
    total_employees = len(employees)
    total_participants = len(participant_employee_ids)

    return render_template(
        "plan_participants.html",
        plan=plan,
        company=company,
        navigation=navigation,
        active_section="participants",
        employees=employees,
        total_employees=total_employees,
        total_participants=total_participants,
        participants_section_open=participants_section_open,
        participants_section_status=participants_section_status,
    )


@app.route("/plans/<plan_id>/participants/toggle/<int:employee_id>", methods=["POST"])
def toggle_participant(plan_id: str, employee_id: int):
    """Toggle employee participation in the plan"""
    try:
        plan, company = _plan_for(plan_id)

        # Get the employee
        employee = db.get_employee(company["id"], employee_id)
        if not employee:
            return (
                jsonify({"success": False, "error": "Colaborador não encontrado"}),
                404,
            )

        # Check if employee is already a participant
        participants = db.get_participants(int(plan_id))
        existing_participant = next(
            (p for p in participants if p.get("employee_id") == employee_id), None
        )

        if existing_participant:
            # Remove participation
            db.delete_participant(existing_participant["id"])
            return jsonify(
                {
                    "success": True,
                    "action": "removed",
                    "message": "Participação removida com sucesso",
                }
            )
        else:
            # Add participation
            participant_data = {
                "employee_id": employee_id,
                "name": employee["name"],
                "role": employee.get("role_name") or employee.get("department") or "",
                "relation": employee.get("department") or "",
                "email": employee.get("email") or "",
                "phone": employee.get("phone") or "",
                "cpf": "",
                "status": "active",
            }
            participant_id = db.add_participant(int(plan_id), participant_data)
            if participant_id:
                return jsonify(
                    {
                        "success": True,
                        "action": "added",
                        "message": "Participante adicionado com sucesso",
                    }
                )
            else:
                return (
                    jsonify(
                        {"success": False, "error": "Erro ao adicionar participante"}
                    ),
                    500,
                )
    except Exception as e:
        logger.info(f"Error toggling participant: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/plans/<plan_id>/drivers")
def plan_drivers(plan_id: str):
    """Drivers page"""
    plan, company = _plan_for(plan_id)
    navigation = _navigation(plan_id, "drivers")

    # Get drivers
    drivers = db.get_drivers(int(plan_id))

    # Get participants for selection
    participants = db.get_participants(int(plan_id))

    # Get interviews from database
    interviews = db.get_interviews(int(plan_id))

    # Get interview section status
    interview_section_status = db.get_section_status(int(plan_id), "interviews")
    interview_section_open = (
        interview_section_status is None
        or interview_section_status.get("status", "open") == "open"
    )

    # Get vision records from database
    vision_records = db.get_vision_records(int(plan_id))

    # Get vision section status
    vision_section_status = db.get_section_status(int(plan_id), "vision")
    vision_section_open = (
        vision_section_status is None
        or vision_section_status.get("status", "open") == "open"
    )

    # Get market records from database
    market_records = db.get_market_records(int(plan_id))

    # Get market section status
    market_section_status = db.get_section_status(int(plan_id), "market")
    market_section_open = (
        market_section_status is None
        or market_section_status.get("status", "open") == "open"
    )

    # Get company records from database
    company_records = db.get_company_records(int(plan_id))

    # Get company section status
    company_section_status = db.get_section_status(int(plan_id), "company")
    company_section_open = (
        company_section_status is None
        or company_section_status.get("status", "open") == "open"
    )

    # Get new alignment subsections status
    alignments_found_section_status = db.get_section_status(
        int(plan_id), "alignments-found"
    )
    alignments_found_section_open = (
        alignments_found_section_status is None
        or alignments_found_section_status.get("status", "open") == "open"
    )

    misalignments_critical_section_status = db.get_section_status(
        int(plan_id), "misalignments-critical"
    )
    misalignments_critical_section_open = (
        misalignments_critical_section_status is None
        or misalignments_critical_section_status.get("status", "open") == "open"
    )

    preliminary_analysis_section_status = db.get_section_status(
        int(plan_id), "preliminary-analysis"
    )
    preliminary_analysis_section_open = (
        preliminary_analysis_section_status is None
        or preliminary_analysis_section_status.get("status", "open") == "open"
    )

    workshop_final_analysis_section_status = db.get_section_status(
        int(plan_id), "workshop-final-analysis"
    )
    workshop_final_analysis_section_open = (
        workshop_final_analysis_section_status is None
        or workshop_final_analysis_section_status.get("status", "open") == "open"
    )

    # Get alignment and misalignment records from database
    alignment_records = db.get_alignment_records(int(plan_id))
    misalignment_records = db.get_misalignment_records(int(plan_id))

    # Get directional records from database
    directional_records = db.get_directional_records(int(plan_id))

    # Get directionals section status
    directionals_section_status = db.get_section_status(int(plan_id), "directionals")
    directionals_section_open = (
        directionals_section_status is None
        or directionals_section_status.get("status", "open") == "open"
    )

    # Get new directionals sections status
    directionals_ai_section_status = db.get_section_status(
        int(plan_id), "directionals-ai"
    )
    directionals_ai_section_open = (
        directionals_ai_section_status is None
        or directionals_ai_section_status.get("status", "open") == "open"
    )

    directionals_consultant_section_status = db.get_section_status(
        int(plan_id), "directionals-consultant"
    )
    directionals_consultant_section_open = (
        directionals_consultant_section_status is None
        or directionals_consultant_section_status.get("status", "open") == "open"
    )

    directionals_approvals_section_status = db.get_section_status(
        int(plan_id), "directionals-approvals"
    )
    directionals_approvals_section_open = (
        directionals_approvals_section_status is None
        or directionals_approvals_section_status.get("status", "open") == "open"
    )

    # Get directionals data
    directionals_ai_analysis = ""
    directionals_ai_suggestions = ""
    directionals_consultant_ai_analysis = ""
    directionals_consultant_diagnosis = ""
    directionals_consultant_directionals = ""
    directionals_approvals = []

    if directionals_ai_section_status:
        directionals_ai_analysis = directionals_ai_section_status.get("notes", "")
        directionals_ai_suggestions = directionals_ai_section_status.get(
            "suggestions", ""
        )

    if directionals_consultant_section_status:
        directionals_consultant_ai_analysis = (
            directionals_consultant_section_status.get("ai_analysis", "")
        )
        directionals_consultant_diagnosis = directionals_consultant_section_status.get(
            "diagnosis", ""
        )
        directionals_consultant_directionals = (
            directionals_consultant_section_status.get("directionals", "")
        )

    # TODO: Implement database methods for approvals
    # directionals_approvals = db.get_directionals_approvals(plan_id)

    # Get consultant notes for alignment and misalignment sections
    alignment_consultant_notes = ""
    misalignment_consultant_notes = ""
    workshop_consultant_notes = ""
    directionals_consultant_notes = ""

    if alignments_found_section_status:
        alignment_consultant_notes = alignments_found_section_status.get("notes", "")

    if misalignments_critical_section_status:
        misalignment_consultant_notes = misalignments_critical_section_status.get(
            "notes", ""
        )

    if workshop_final_analysis_section_status:
        workshop_consultant_notes = workshop_final_analysis_section_status.get(
            "notes", ""
        )
        # Try to get workshop adjustments from the adjustments field (JSON format)
        try:
            adjustments_data = workshop_final_analysis_section_status.get(
                "adjustments", ""
            )
            workshop_adjustments = (
                json.loads(adjustments_data) if adjustments_data else []
            )
        except (json.JSONDecodeError, TypeError):
            workshop_adjustments = []
    else:
        workshop_adjustments = []

    # Get consultant notes and approvals from the directionals-approvals section (Finalização)
    if directionals_approvals_section_status:
        directionals_approvals_notes = directionals_approvals_section_status.get(
            "notes", ""
        )

        # The notes field can be:
        # 1. Plain text (consultant notes)
        # 2. JSON with approvals and consultant notes
        # We need to handle both cases
        try:
            if directionals_approvals_notes:
                # Try to parse as JSON first
                try:
                    combined_data = json.loads(directionals_approvals_notes)
                    directionals_approvals = combined_data.get("approvals", [])
                    directionals_consultant_notes = combined_data.get(
                        "consultant_notes", ""
                    )
                except (json.JSONDecodeError, TypeError):
                    # If it's not JSON, it's plain text consultant notes
                    directionals_consultant_notes = directionals_approvals_notes
                    directionals_approvals = []
            else:
                directionals_consultant_notes = ""
                directionals_approvals = []
        except Exception as e:
            logger.info(f"Error parsing directionals-approvals notes: {e}")
            directionals_consultant_notes = ""
            directionals_approvals = []
    else:
        directionals_consultant_notes = ""
        directionals_approvals = []

    # Use the directional records from the database table, not from plan_sections
    directionals_records = directional_records

    # Sample data for drivers page
    average_maturity = 3.2
    interview_records = [
        {
            "id": interview["id"],
            "participant": interview["participant_name"],
            "consultant": interview["consultant_name"],
            "date": interview["interview_date"],
            "format": interview["format"],
            "notes": interview["notes"],
        }
        for interview in interviews
    ]

    # Process vision records
    vision_records_processed = []
    for vision_record in vision_records:
        # Os dados já são texto livre, não precisamos converter
        vision_records_processed.append(
            {
                "id": vision_record["id"],
                "participants": vision_record["participants"] or "",
                "consultants": vision_record["consultants"] or "",
                "date": vision_record["vision_date"],
                "format": vision_record["format"],
                "notes": vision_record["notes"],
                "created_at": vision_record["created_at"],
            }
        )

    # Process market records
    market_records_processed = []
    for market_record in market_records:
        # Os dados já são texto livre, não precisamos converter
        market_records_processed.append(
            {
                "id": market_record["id"],
                "participants": market_record["participants"] or "",
                "consultants": market_record["consultants"] or "",
                "date": market_record["market_date"],
                "format": market_record["format"],
                "global_context": market_record["global_context"] or "",
                "sector_context": market_record["sector_context"] or "",
                "market_size": market_record["market_size"] or "",
                "growth_space": market_record["growth_space"] or "",
                "threats": market_record["threats"] or "",
                "consumer_behavior": market_record["consumer_behavior"] or "",
                "competition": market_record["competition"] or "",
                "notes": market_record["notes"] or "",
                "created_at": market_record["created_at"],
            }
        )

    # Process company records
    company_records_processed = []
    for company_record in company_records:
        company_records_processed.append(
            {
                "id": company_record["id"],
                "participants": company_record["participants"] or "",
                "consultants": company_record["consultants"] or "",
                "date": company_record["company_date"],
                "bsc_financial": company_record["bsc_financial"] or "",
                "bsc_commercial": company_record["bsc_commercial"] or "",
                "bsc_process": company_record["bsc_process"] or "",
                "bsc_learning": company_record["bsc_learning"] or "",
                "tri_commercial": company_record["tri_commercial"] or "",
                "tri_adm_fin": company_record["tri_adm_fin"] or "",
                "tri_operational": company_record["tri_operational"] or "",
                "notes": company_record["notes"] or "",
                "created_at": company_record["created_at"],
            }
        )

    # Process alignment records
    alignment_records_processed = []
    for alignment_record in alignment_records:
        alignment_records_processed.append(
            {
                "id": alignment_record["id"],
                "topic": alignment_record["topic"] or "",
                "description": alignment_record["description"] or "",
                "consensus": alignment_record["consensus"] or "",
                "priority": alignment_record["priority"] or "",
                "notes": alignment_record["notes"] or "",
                "created_at": alignment_record["created_at"],
            }
        )

    # Process misalignment records
    misalignment_records_processed = []
    for misalignment_record in misalignment_records:
        misalignment_records_processed.append(
            {
                "id": misalignment_record["id"],
                "issue": misalignment_record["issue"] or "",
                "description": misalignment_record["description"] or "",
                "severity": misalignment_record["severity"] or "",
                "impact": misalignment_record["impact"] or "",
                "notes": misalignment_record["notes"] or "",
                "created_at": misalignment_record["created_at"],
            }
        )

    # Process directional records
    directional_records_processed = []
    for directional_record in directional_records:
        directional_records_processed.append(
            {
                "id": directional_record["id"],
                "title": directional_record["title"] or "",
                "description": directional_record["description"] or "",
                "status": directional_record["status"] or "",
                "owner": directional_record["owner"] or "",
                "notes": directional_record["notes"] or "",
                "created_at": directional_record["created_at"],
            }
        )

    alignments_found = {
        "title": "Alinhamentos encontrados",
        "ai_briefing": "Análise de IA: Forte consenso sobre necessidade de digitalização, mas divergências sobre prioridades de investimento.",
    }

    # Remove static data - use only database records
    alignments_records = []

    misalignments_critical = {
        "title": "Desalinhamentos críticos",
        "ai_briefing": "Análise de IA: Identificados pontos de resistência à mudança e divergências sobre investimentos em tecnologia.",
        "consultant_notes": "Necessário trabalho de convencimento sobre benefícios da digitalização e treinamento da equipe.",
    }

    # Remove static data - use only database records
    misalignments_records = []

    directionals_preliminary = {
        "title": "Direcionadores preliminares",
        "ai_suggestion": "Análise de IA: Sugestão de foco em digitalização, capacitação da equipe e otimização de processos como direcionadores estratégicos principais.",
        "consultant_diagnosis": "Diagnóstico: Necessidade de transformação digital urgente, com foco em treinamento e mudança de cultura organizacional.",
        "notes": "Baseado nas entrevistas realizadas e análise do ambiente interno.",
    }

    directionals_changes = {
        "title": "Ajustes realizados",
        "notes": "Ajustes realizados após revisão com a equipe de liderança.",
    }

    directionals_approvals_data = {
        "title": "Aprovações e comunicações",
        "selected_partners": ["Carlos Pina", "Marcos Fenecio"],
        "approval_text": "Conforme aprovado em reunião de diretoria, os direcionadores estratégicos foram validados para implementação.",
        "send_email": True,
        "send_whatsapp": False,
    }

    partners_options = [
        "Carlos Pina",
        "Marcos Fenecio",
        "Ana Souza",
        "Fabiano Ferreira",
    ]

    # Use first company record if available
    company_record = company_records_processed[0] if company_records_processed else None

    return render_template(
        "plan_drivers.html",
        plan=plan,
        company=company,
        navigation=navigation,
        active_section="drivers",
        drivers=drivers,
        participants=participants,
        interview_section_open=interview_section_open,
        interview_section_status=interview_section_status,
        vision_section_open=vision_section_open,
        vision_section_status=vision_section_status,
        market_section_open=market_section_open,
        market_section_status=market_section_status,
        company_section_open=company_section_open,
        company_section_status=company_section_status,
        alignments_found_section_open=alignments_found_section_open,
        alignments_found_section_status=alignments_found_section_status,
        misalignments_critical_section_open=misalignments_critical_section_open,
        misalignments_critical_section_status=misalignments_critical_section_status,
        preliminary_analysis_section_open=preliminary_analysis_section_open,
        preliminary_analysis_section_status=preliminary_analysis_section_status,
        workshop_final_analysis_section_open=workshop_final_analysis_section_open,
        workshop_final_analysis_section_status=workshop_final_analysis_section_status,
        directionals_section_open=directionals_section_open,
        directionals_section_status=directionals_section_status,
        directionals_ai_section_open=directionals_ai_section_open,
        directionals_ai_section_status=directionals_ai_section_status,
        directionals_consultant_section_open=directionals_consultant_section_open,
        directionals_consultant_section_status=directionals_consultant_section_status,
        directionals_approvals_section_open=directionals_approvals_section_open,
        directionals_approvals_section_status=directionals_approvals_section_status,
        directionals_ai_analysis=directionals_ai_analysis,
        directionals_ai_suggestions=directionals_ai_suggestions,
        directionals_consultant_ai_analysis=directionals_consultant_ai_analysis,
        directionals_consultant_diagnosis=directionals_consultant_diagnosis,
        directionals_consultant_directionals=directionals_consultant_directionals,
        directionals_approvals=directionals_approvals,
        alignment_consultant_notes=alignment_consultant_notes,
        misalignment_consultant_notes=misalignment_consultant_notes,
        workshop_consultant_notes=workshop_consultant_notes,
        workshop_adjustments=workshop_adjustments,
        directionals_consultant_notes=directionals_consultant_notes,
        directionals_records=directionals_records,
        average_maturity=average_maturity,
        interview_records=interview_records,
        vision_records=vision_records_processed,
        market_records=market_records_processed,
        company_records=company_records_processed,
        alignment_records=alignment_records_processed,
        misalignment_records=misalignment_records_processed,
        directionals_catalog=directional_records_processed,
        alignments_found=alignments_found,
        alignments_records=alignments_records,
        misalignments_critical=misalignments_critical,
        misalignments_records=misalignments_records,
        directionals_preliminary=directionals_preliminary,
        directionals_changes=directionals_changes,
        directionals_approvals_data=directionals_approvals_data,
        partners_options=partners_options,
        company_record=company_record,
    )


@app.route("/plans/<plan_id>/okr-global")
def plan_okr_global(plan_id: str):
    """OKR Global page"""
    plan, company = _plan_for(plan_id)
    navigation = _navigation(plan_id, "okr-global")
    indicator_sidebar_nav = _indicator_navigation(company.get("id"))

    participants_options, participant_lookup = _build_participant_context(int(plan_id))

    indicator_lookup_map = _build_indicator_lookup(company["id"])
    indicators = list(indicator_lookup_map.values())
    indicator_lookup = {
        key: value.get("label") or value.get("name") or ""
        for key, value in indicator_lookup_map.items()
    }

    preliminary_analysis_section_status = db.get_section_status(
        int(plan_id), "preliminary-analysis-okr"
    )
    preliminary_analysis_section_open = (
        preliminary_analysis_section_status is None
        or preliminary_analysis_section_status.get("status", "open") == "open"
    )

    workshop_final_section_status = db.get_section_status(
        int(plan_id), "workshop-final-okr"
    )
    workshop_final_section_open = (
        workshop_final_section_status is None
        or workshop_final_section_status.get("status", "open") == "open"
    )

    okr_approvals_section_status = db.get_section_status(int(plan_id), "okr-approvals")
    okr_approvals_section_open = (
        okr_approvals_section_status is None
        or okr_approvals_section_status.get("status", "open") == "open"
    )

    preliminary_raw = db.get_okr_preliminary_records(int(plan_id))
    workshop_raw = db.get_global_okr_records(int(plan_id), "workshop")
    approvals_raw = db.get_global_okr_records(int(plan_id), "approval")

    # Migrate legacy OKRs stored in plan_sections if new tables are empty
    workshop_status = db.get_section_status(int(plan_id), "workshop-final-okr")
    if not workshop_raw and workshop_status and workshop_status.get("notes"):
        try:
            legacy_workshop = json.loads(workshop_status["notes"])
            legacy_okrs = (
                legacy_workshop.get("okrs")
                if isinstance(legacy_workshop, dict)
                else None
            )
            if isinstance(legacy_okrs, list) and legacy_okrs:
                for legacy in legacy_okrs:
                    okr_type = legacy.get("okr_type") or legacy.get("type") or ""
                    okr_data = {
                        "objective": legacy.get("objective", ""),
                        "okr_type": okr_type,
                        "type_display": legacy.get("type_display")
                        or _okr_type_display(okr_type),
                        "owner_id": legacy.get("owner_id"),
                        "owner": legacy.get("owner"),
                        "deadline": legacy.get("deadline"),
                        "observations": legacy.get("observations"),
                        "directional": str(legacy.get("directional") or ""),
                    }
                    legacy_key_results = []
                    for legacy_kr in legacy.get("key_results", []):
                        if not isinstance(legacy_kr, dict):
                            continue
                        legacy_key_results.append(
                            {
                                "label": legacy_kr.get("label", ""),
                                "target": legacy_kr.get("target"),
                                "deadline": legacy_kr.get("deadline"),
                                "owner_id": legacy_kr.get("owner_id"),
                                "owner": legacy_kr.get("owner"),
                                "indicator_id": legacy_kr.get("indicator_id"),
                                "indicator_label": legacy_kr.get("indicator_label"),
                                "position": len(legacy_key_results),
                            }
                        )
                    db.add_global_okr_record(
                        int(plan_id), "workshop", okr_data, legacy_key_results
                    )
                legacy_workshop.pop("okrs", None)
                db.update_section_consultant_notes(
                    int(plan_id), "workshop-final-okr", json.dumps(legacy_workshop)
                )
                workshop_raw = db.get_global_okr_records(int(plan_id), "workshop")
                workshop_status = db.get_section_status(
                    int(plan_id), "workshop-final-okr"
                )
        except Exception as exc:
            logger.info(f"Error migrating legacy workshop OKRs: {exc}")

    approvals_status = db.get_section_status(int(plan_id), "okr-approvals")
    if not approvals_raw and approvals_status and approvals_status.get("notes"):
        try:
            legacy_approvals = json.loads(approvals_status["notes"])
            legacy_okrs = (
                legacy_approvals.get("okrs")
                if isinstance(legacy_approvals, dict)
                else None
            )
            if isinstance(legacy_okrs, list) and legacy_okrs:
                for legacy in legacy_okrs:
                    okr_type = legacy.get("okr_type") or legacy.get("type") or ""
                    okr_data = {
                        "objective": legacy.get("objective", ""),
                        "okr_type": okr_type,
                        "type_display": legacy.get("type_display")
                        or _okr_type_display(okr_type),
                        "owner_id": legacy.get("owner_id"),
                        "owner": legacy.get("owner"),
                        "deadline": legacy.get("deadline"),
                        "observations": legacy.get("observations"),
                        "directional": str(legacy.get("directional") or ""),
                    }
                    legacy_key_results = []
                    for legacy_kr in legacy.get("key_results", []):
                        if not isinstance(legacy_kr, dict):
                            continue
                        legacy_key_results.append(
                            {
                                "label": legacy_kr.get("label", ""),
                                "target": legacy_kr.get("target"),
                                "deadline": legacy_kr.get("deadline"),
                                "owner_id": legacy_kr.get("owner_id"),
                                "owner": legacy_kr.get("owner"),
                                "indicator_id": legacy_kr.get("indicator_id"),
                                "indicator_label": legacy_kr.get("indicator_label"),
                                "position": len(legacy_key_results),
                            }
                        )
                    db.add_global_okr_record(
                        int(plan_id), "approval", okr_data, legacy_key_results
                    )
                legacy_approvals.pop("okrs", None)
                db.update_section_consultant_notes(
                    int(plan_id), "okr-approvals", json.dumps(legacy_approvals)
                )
                approvals_raw = db.get_global_okr_records(int(plan_id), "approval")
                approvals_status = db.get_section_status(int(plan_id), "okr-approvals")
        except Exception as exc:
            logger.info(f"Error migrating legacy approval OKRs: {exc}")

    preliminary_okr_records = []
    for record in preliminary_raw:
        item = dict(record)
        item["created_at"] = _parse_datetime(item.get("created_at"))
        item["updated_at"] = _parse_datetime(item.get("updated_at"))
        preliminary_okr_records.append(item)

    def _normalize_global_records(records):
        normalized = []
        for record in records:
            item = dict(record)
            item["id"] = str(item.get("id")) if item.get("id") is not None else None
            item["created_at"] = _parse_datetime(item.get("created_at"))
            item["updated_at"] = _parse_datetime(item.get("updated_at"))
            item["deadline"] = _parse_datetime(item.get("deadline"))
            item["type"] = item.get("okr_type")
            item["type_display"] = item.get("type_display") or _okr_type_display(
                item.get("okr_type", "")
            )
            item["directional"] = (
                str(item.get("directional"))
                if item.get("directional") is not None
                else ""
            )
            owner_id_value = item.get("owner_id")
            if owner_id_value is not None and owner_id_value != "":
                owner_id_str = str(owner_id_value)
                item["owner_id"] = owner_id_str
                owner_name = participant_lookup.get(owner_id_str)
                if owner_name:
                    item["owner"] = owner_name
            else:
                item["owner_id"] = ""
            key_results = []
            for kr in item.get("key_results", []):
                normalized_kr = dict(kr)
                normalized_kr["id"] = (
                    str(normalized_kr.get("id"))
                    if normalized_kr.get("id") is not None
                    else None
                )
                kr_owner_id = normalized_kr.get("owner_id")
                if kr_owner_id is not None and kr_owner_id != "":
                    kr_owner_str = str(kr_owner_id)
                    normalized_kr["owner_id"] = kr_owner_str
                    kr_owner_name = participant_lookup.get(kr_owner_str)
                    if kr_owner_name and not normalized_kr.get("owner"):
                        normalized_kr["owner"] = kr_owner_name
                else:
                    normalized_kr["owner_id"] = ""
                indicator_id_value = normalized_kr.get("indicator_id")
                if indicator_id_value is not None and indicator_id_value != "":
                    indicator_id_str = str(indicator_id_value)
                    normalized_kr["indicator_id"] = indicator_id_str
                    indicator_display = indicator_lookup.get(indicator_id_str)
                    if indicator_display:
                        normalized_kr["indicator_display"] = indicator_display
                else:
                    normalized_kr["indicator_id"] = ""
                    if normalized_kr.get("indicator_label"):
                        normalized_kr["indicator_display"] = normalized_kr[
                            "indicator_label"
                        ]
                key_results.append(normalized_kr)
            item["key_results"] = key_results
            normalized.append(item)
        return normalized

    workshop_okr_records = _normalize_global_records(workshop_raw)
    okr_approvals_records = _normalize_global_records(approvals_raw)

    # Get workshop discussions using new simplified method
    workshop_discussions_data = db.get_workshop_discussions(int(plan_id), "preliminary")
    workshop_discussions = (
        workshop_discussions_data.get("content", "")
        if workshop_discussions_data
        else ""
    )

    # Get approval discussions using new simplified method
    approval_discussions_data = db.get_workshop_discussions(int(plan_id), "final")
    approval_discussions = (
        approval_discussions_data.get("content", "")
        if approval_discussions_data
        else ""
    )

    directionals_records = _load_directionals(int(plan_id))
    directionals_lookup = {str(d.get("id")): d for d in directionals_records}

    return render_template(
        "plan_okr_global.html",
        plan=plan,
        company=company,
        navigation=navigation,
        indicator_sidebar_nav=indicator_sidebar_nav,
        active_section="okr-global",
        preliminary_analysis_section_open=preliminary_analysis_section_open,
        workshop_final_section_open=workshop_final_section_open,
        okr_approvals_section_open=okr_approvals_section_open,
        preliminary_okr_records=preliminary_okr_records,
        workshop_okr_records=workshop_okr_records,
        okr_approvals_records=okr_approvals_records,
        directionals_records=directionals_records,
        directionals_lookup=directionals_lookup,
        participants_options=participants_options,
        participant_lookup=participant_lookup,
        indicators=indicators,
        indicator_lookup=indicator_lookup,
        workshop_discussions=workshop_discussions,
        approval_discussions=approval_discussions,
    )


@app.route("/plans/<plan_id>/okr-area")
def plan_okr_area(plan_id: str):
    """OKR Area page"""
    plan, company = _plan_for(plan_id)
    navigation = _navigation(plan_id, "okr-area")
    indicator_sidebar_nav = _indicator_navigation(company.get("id"))

    participants_options, participant_name_lookup = _build_participant_context(
        int(plan_id)
    )
    indicator_lookup_map = _build_indicator_lookup(company["id"])
    indicators = list(indicator_lookup_map.values())
    indicator_lookup = {
        key: value.get("label") or value.get("name") or ""
        for key, value in indicator_lookup_map.items()
    }

    # Get section statuses for all area OKR sections
    preliminary_analysis_status = db.get_section_status(
        int(plan_id), "preliminary-analysis-area-okr"
    )
    preliminary_analysis_section_open = (
        preliminary_analysis_status is None
        or preliminary_analysis_status.get("status", "open") == "open"
    )

    workshop_area_status = db.get_section_status(int(plan_id), "area-okr-workshop")
    workshop_area_section_open = (
        workshop_area_status is None
        or workshop_area_status.get("status", "open") == "open"
    )

    final_area_status = db.get_section_status(int(plan_id), "final-area-okr")
    final_area_section_open = (
        final_area_status is None or final_area_status.get("status", "open") == "open"
    )

    # Get Global OKRs for dropdown (from approved OKRs)
    global_okrs = []
    approval_records = db.get_global_okr_records(int(plan_id), "approval")
    for record in approval_records:
        item = dict(record)
        item["id"] = str(item.get("id")) if item.get("id") is not None else None
        item["type"] = item.get("okr_type")
        item["type_display"] = item.get("type_display") or _okr_type_display(
            item.get("okr_type", "")
        )
        item["directional"] = (
            str(item.get("directional")) if item.get("directional") is not None else ""
        )
        item["created_at"] = _parse_datetime(item.get("created_at"))
        item["updated_at"] = _parse_datetime(item.get("updated_at"))
        item["deadline"] = _parse_datetime(item.get("deadline"))
        owner_id_val = item.get("owner_id")
        if owner_id_val is not None and owner_id_val != "":
            owner_id_str = str(owner_id_val)
            item["owner_id"] = owner_id_str
            owner_name = participant_name_lookup.get(owner_id_str)
            if owner_name:
                item["owner"] = owner_name
        else:
            item["owner_id"] = ""
        normalized_key_results = []
        for kr in item.get("key_results", []):
            normalized_kr = dict(kr)
            kr_owner_id = normalized_kr.get("owner_id")
            if kr_owner_id is not None and kr_owner_id != "":
                kr_owner_str = str(kr_owner_id)
                normalized_kr["owner_id"] = kr_owner_str
                owner_name = participant_name_lookup.get(kr_owner_str)
                if owner_name and not normalized_kr.get("owner"):
                    normalized_kr["owner"] = owner_name
            else:
                normalized_kr["owner_id"] = ""
            indicator_id_val = normalized_kr.get("indicator_id")
            if indicator_id_val is not None and indicator_id_val != "":
                indicator_id_str = str(indicator_id_val)
                normalized_kr["indicator_id"] = indicator_id_str
                indicator_display = indicator_lookup.get(indicator_id_str)
                if indicator_display:
                    normalized_kr["indicator_display"] = indicator_display
            else:
                normalized_kr["indicator_id"] = ""
                if normalized_kr.get("indicator_label"):
                    normalized_kr["indicator_display"] = normalized_kr[
                        "indicator_label"
                    ]
            normalized_key_results.append(normalized_kr)
        item["key_results"] = normalized_key_results
        global_okrs.append(item)
    # Get Preliminary Analysis Records using new simplified method
    preliminary_area_raw = db.get_okr_area_preliminary_records(int(plan_id))
    preliminary_area_okr_records = []
    for record in preliminary_area_raw:
        item = dict(record)
        item["created_at"] = _parse_datetime(item.get("created_at"))
        item["updated_at"] = _parse_datetime(item.get("updated_at"))
        preliminary_area_okr_records.append(item)

    # Get Workshop Area OKRs - buscar de ambas as fontes
    workshop_area_okr_records = []

    # 1. Buscar da tabela okr_area_records (novo sistema)
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM okr_area_records 
            WHERE plan_id = %s AND stage = 'workshop'
            ORDER BY created_at
        """,
            (plan_id,),
        )

        table_records = cursor.fetchall()
        for record in table_records:
            okr_data = dict(record)
            # Converter para formato esperado
            okr_data["area"] = okr_data.get("department", "")
            okr_data["type"] = okr_data.get("okr_type", "")
            okr_data["type_display"] = okr_data.get("type_display", "")
            okr_data["key_results"] = []  # TODO: buscar key results se necessário

            # Convert datetime strings to datetime objects
            if "created_at" in okr_data and okr_data["created_at"]:
                try:
                    from datetime import datetime

                    okr_data["created_at"] = datetime.fromisoformat(
                        okr_data["created_at"].replace("Z", "+00:00")
                    )
                except Exception as exc:
                    pass
            if "updated_at" in okr_data and okr_data["updated_at"]:
                try:
                    from datetime import datetime

                    okr_data["updated_at"] = datetime.fromisoformat(
                        okr_data["updated_at"].replace("Z", "+00:00")
                    )
                except Exception as exc:
                    pass
            if "deadline" in okr_data and okr_data["deadline"]:
                try:
                    from datetime import datetime

                    # Handle both ISO format and simple date strings
                    if isinstance(okr_data["deadline"], str):
                        if "T" in okr_data["deadline"] or "+" in okr_data["deadline"]:
                            okr_data["deadline"] = datetime.fromisoformat(
                                okr_data["deadline"].replace("Z", "+00:00")
                            )
                        else:
                            # Try to parse as date string (YYYY-MM-DD)
                            okr_data["deadline"] = datetime.strptime(
                                okr_data["deadline"], "%Y-%m-%d"
                            )
                except Exception as exc:
                    pass

            workshop_area_okr_records.append(okr_data)

        conn.close()
    except Exception as e:
        logger.info(f"Erro ao buscar OKRs da tabela: {e}")

    # 2. Buscar do sistema antigo (JSON nas notas) se não houver dados na tabela
    if (
        not workshop_area_okr_records
        and workshop_area_status
        and workshop_area_status.get("notes")
    ):
        try:
            import json
            from datetime import datetime

            workshop_data = json.loads(workshop_area_status["notes"])
            if isinstance(workshop_data, dict):
                if "okrs" in workshop_data:
                    for okr in workshop_data["okrs"]:
                        # Convert datetime strings to datetime objects
                        if "created_at" in okr:
                            try:
                                okr["created_at"] = datetime.fromisoformat(
                                    okr["created_at"].replace("Z", "+00:00")
                                )
                            except Exception as exc:
                                okr["created_at"] = datetime.now()
                        if "updated_at" in okr:
                            try:
                                okr["updated_at"] = datetime.fromisoformat(
                                    okr["updated_at"].replace("Z", "+00:00")
                                )
                            except Exception as exc:
                                okr["updated_at"] = okr.get(
                                    "created_at", datetime.now()
                                )
                        if "deadline" in okr and okr["deadline"]:
                            try:
                                okr["deadline"] = datetime.fromisoformat(
                                    okr["deadline"]
                                )
                            except Exception as exc:
                                pass
                        workshop_area_okr_records.append(okr)
        except Exception as exc:
            pass

    workshop_area_okr_records = _normalize_area_okr_payload(
        workshop_area_okr_records, participant_name_lookup, indicator_lookup
    )

    # Get area workshop discussions using new simplified method
    area_workshop_discussions_data = db.get_workshop_discussions(
        int(plan_id), "area-preliminary"
    )
    area_workshop_discussions = (
        area_workshop_discussions_data.get("content", "")
        if area_workshop_discussions_data
        else ""
    )

    # Get Final Area OKRs - buscar de ambas as fontes
    final_area_okr_records = []

    # 1. Buscar da tabela okr_area_records (novo sistema)
    try:
        from database.postgres_helper import connect as pg_connect

        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM okr_area_records 
            WHERE plan_id = %s AND stage = 'approval'
            ORDER BY created_at
        """,
            (plan_id,),
        )

        table_records = cursor.fetchall()
        for record in table_records:
            okr_data = dict(record)
            # Converter para formato esperado
            okr_data["area"] = okr_data.get("department", "")
            okr_data["type"] = okr_data.get("okr_type", "")
            okr_data["type_display"] = okr_data.get("type_display", "")
            okr_data["key_results"] = []  # TODO: buscar key results se necessário

            # Convert datetime strings to datetime objects
            if "created_at" in okr_data and okr_data["created_at"]:
                try:
                    from datetime import datetime

                    okr_data["created_at"] = datetime.fromisoformat(
                        okr_data["created_at"].replace("Z", "+00:00")
                    )
                except Exception as exc:
                    pass
            if "updated_at" in okr_data and okr_data["updated_at"]:
                try:
                    from datetime import datetime

                    okr_data["updated_at"] = datetime.fromisoformat(
                        okr_data["updated_at"].replace("Z", "+00:00")
                    )
                except Exception as exc:
                    pass
            if "deadline" in okr_data and okr_data["deadline"]:
                try:
                    from datetime import datetime

                    # Handle both ISO format and simple date strings
                    if isinstance(okr_data["deadline"], str):
                        if "T" in okr_data["deadline"] or "+" in okr_data["deadline"]:
                            okr_data["deadline"] = datetime.fromisoformat(
                                okr_data["deadline"].replace("Z", "+00:00")
                            )
                        else:
                            # Try to parse as date string (YYYY-MM-DD)
                            okr_data["deadline"] = datetime.strptime(
                                okr_data["deadline"], "%Y-%m-%d"
                            )
                except Exception as exc:
                    pass

            final_area_okr_records.append(okr_data)

        conn.close()
    except Exception as e:
        logger.info(f"Erro ao buscar OKRs finais da tabela: {e}")

    # 2. Buscar do sistema antigo (JSON nas notas) se não houver dados na tabela
    if (
        not final_area_okr_records
        and final_area_status
        and final_area_status.get("notes")
    ):
        try:
            import json
            from datetime import datetime

            final_data = json.loads(final_area_status["notes"])
            if isinstance(final_data, dict):
                if "okrs" in final_data:
                    for okr in final_data["okrs"]:
                        # Convert datetime strings to datetime objects
                        if "created_at" in okr:
                            try:
                                okr["created_at"] = datetime.fromisoformat(
                                    okr["created_at"].replace("Z", "+00:00")
                                )
                            except Exception as exc:
                                okr["created_at"] = datetime.now()
                        if "updated_at" in okr:
                            try:
                                okr["updated_at"] = datetime.fromisoformat(
                                    okr["updated_at"].replace("Z", "+00:00")
                                )
                            except Exception as exc:
                                okr["updated_at"] = okr.get(
                                    "created_at", datetime.now()
                                )
                        if "deadline" in okr and okr["deadline"]:
                            try:
                                okr["deadline"] = datetime.fromisoformat(
                                    okr["deadline"]
                                )
                            except Exception as exc:
                                pass
                        final_area_okr_records.append(okr)
        except Exception as exc:
            pass

    final_area_okr_records = _normalize_area_okr_payload(
        final_area_okr_records, participant_name_lookup, indicator_lookup
    )

    # Get final area discussions using new simplified method
    final_area_discussions_data = db.get_workshop_discussions(
        int(plan_id), "area-final"
    )
    final_area_discussions = (
        final_area_discussions_data.get("content", "")
        if final_area_discussions_data
        else ""
    )

    # Calculate summary for all OKRs
    all_area_okrs = workshop_area_okr_records + final_area_okr_records
    okr_summary = {
        "total": len(all_area_okrs),
        "comercial": len(
            [okr for okr in all_area_okrs if okr.get("area") == "comercial"]
        ),
        "operacional": len(
            [okr for okr in all_area_okrs if okr.get("area") == "operacional"]
        ),
        "administrativo": len(
            [okr for okr in all_area_okrs if okr.get("area") == "administrativo"]
        ),
        "estruturante": len(
            [okr for okr in all_area_okrs if okr.get("type") == "estruturante"]
        ),
        "aceleracao": len(
            [okr for okr in all_area_okrs if okr.get("type") == "aceleracao"]
        ),
    }

    return render_template(
        "plan_okr_area.html",
        plan=plan,
        company=company,
        navigation=navigation,
        indicator_sidebar_nav=indicator_sidebar_nav,
        active_section="okr-area",
        # Section statuses
        preliminary_analysis_section_open=preliminary_analysis_section_open,
        workshop_area_section_open=workshop_area_section_open,
        final_area_section_open=final_area_section_open,
        # Data
        global_okrs=global_okrs,
        preliminary_area_okr_records=preliminary_area_okr_records,
        workshop_area_okr_records=workshop_area_okr_records,
        final_area_okr_records=final_area_okr_records,
        okr_summary=okr_summary,
        # Discussions
        area_workshop_discussions=area_workshop_discussions,
        final_area_discussions=final_area_discussions,
        # Selection helpers
        participants_options=participants_options,
        participant_lookup=participant_name_lookup,
        indicators=indicators,
        indicator_lookup=indicator_lookup,
    )


@app.route("/plans/<plan_id>/projects", methods=["GET"])
def plan_projects(plan_id: str):
    """Projects page"""
    try:
        plan, company = _plan_for(plan_id)

        # Verificar se é planejamento de implantação e redirecionar
        plan_mode = (plan.get("plan_mode") or "evolucao").lower()
        if plan_mode == "implantacao":
            return redirect(url_for("pev.pev_implantacao_overview", plan_id=plan_id))

        navigation = _navigation(plan_id, "projects")
        indicator_sidebar_nav = _indicator_navigation(company.get("id"))

        # Get projects
        projects = db.get_projects(int(plan_id))

        # Get projects section status
        projects_section_status = db.get_section_status(int(plan_id), "projects")
        projects_section_open = (
            projects_section_status is None
            or projects_section_status.get("status", "open") == "open"
        )

        # Get projects analysis section status
        projects_analysis_section_status = db.get_section_status(
            int(plan_id), "projects-analysis"
        )
        projects_analysis_section_open = (
            projects_analysis_section_status is None
            or projects_analysis_section_status.get("status", "open") == "open"
        )

        # Get analysis data
        projects_ai_analysis = ""
        projects_consultant_analysis = ""

        if projects_analysis_section_status:
            try:
                analysis_data = json.loads(
                    projects_analysis_section_status.get("notes", "{}")
                )
                projects_ai_analysis = analysis_data.get("ai_analysis", "")
                projects_consultant_analysis = analysis_data.get(
                    "consultant_analysis", ""
                )
            except Exception as exc:
                pass

        # Get Area OKRs for dropdown
        import json

        area_okrs = []
        workshop_area_status = db.get_section_status(int(plan_id), "area-okr-workshop")
        if workshop_area_status and workshop_area_status.get("notes"):
            try:
                area_data = json.loads(workshop_area_status["notes"])
                if isinstance(area_data, dict) and "okrs" in area_data:
                    for okr in area_data["okrs"]:
                        area_okrs.append(
                            {
                                "id": okr.get("id", ""),
                                "title": okr.get("objective", ""),
                                "type": okr.get("type", ""),
                                "area": okr.get("area", ""),
                            }
                        )
            except Exception as exc:
                pass

        # Process projects data
        processed_projects = []
        for project in projects:
            processed_project = dict(project)

            # Format dates for display
            if processed_project.get("start_date"):
                try:
                    from datetime import datetime

                    start_date = datetime.fromisoformat(
                        processed_project["start_date"].replace("Z", "+00:00")
                    )
                    processed_project["start_date_display"] = start_date.strftime(
                        "%d/%m/%Y"
                    )
                except Exception as exc:
                    processed_project["start_date_display"] = processed_project[
                        "start_date"
                    ]

            if processed_project.get("end_date"):
                try:
                    from datetime import datetime

                    end_date = datetime.fromisoformat(
                        processed_project["end_date"].replace("Z", "+00:00")
                    )
                    processed_project["end_date_display"] = end_date.strftime(
                        "%d/%m/%Y"
                    )
                except Exception as exc:
                    processed_project["end_date_display"] = processed_project[
                        "end_date"
                    ]

            # Process activities
            if processed_project.get("activities"):
                try:
                    processed_project["activities_list"] = json.loads(
                        processed_project["activities"]
                    )
                except Exception as exc:
                    processed_project["activities_list"] = []
            else:
                processed_project["activities_list"] = []

            # Convert datetime strings to datetime objects and format for display
            if processed_project.get("created_at"):
                try:
                    from datetime import datetime

                    created_at = datetime.fromisoformat(
                        processed_project["created_at"].replace("Z", "+00:00")
                    )
                    processed_project["created_at"] = created_at
                    processed_project["created_at_display"] = created_at.strftime(
                        "%d/%m/%Y ?s %H:%M"
                    )
                except Exception as exc:
                    # Se n?o conseguir converter, manter como string e criar display
                    processed_project["created_at_display"] = processed_project[
                        "created_at"
                    ]

            if processed_project.get("updated_at"):
                try:
                    from datetime import datetime

                    updated_at = datetime.fromisoformat(
                        processed_project["updated_at"].replace("Z", "+00:00")
                    )
                    processed_project["updated_at"] = updated_at
                    processed_project["updated_at_display"] = updated_at.strftime(
                        "%d/%m/%Y ?s %H:%M"
                    )
                except Exception as exc:
                    # Se n?o conseguir converter, manter como string e criar display
                    processed_project["updated_at_display"] = processed_project[
                        "updated_at"
                    ]

            processed_projects.append(processed_project)

        # Get project summary
        project_summary = {
            "total": len(projects),
            "status": {
                "Em andamento": len(
                    [p for p in projects if p.get("status") == "in_progress"]
                ),
                "Concluídos": len(
                    [p for p in projects if p.get("status") == "completed"]
                ),
                "Planejados": len(
                    [p for p in projects if p.get("status") == "planned"]
                ),
            },
        }

        # Check if editing a specific project
        editing_project_id = request.args.get("edit")
        editing_project = None
        if editing_project_id:
            editing_project = db.get_project(int(editing_project_id))

        # Get company employees for dropdown
        employees = []
        try:
            employees = db.list_employees(company.get("id"))
        except Exception as e:
            logger.info(f"Erro ao buscar colaboradores: {e}")
            employees = []

        return render_template(
            "plan_projects.html",
            plan=plan,
            company=company,
            navigation=navigation,
            indicator_sidebar_nav=indicator_sidebar_nav,
            active_section="projects",
            projects=processed_projects,
            project_summary=project_summary,
            editing_project=editing_project,
            area_okrs=area_okrs,
            employees=employees,
            projects_section_status=projects_section_status,
            projects_section_open=projects_section_open,
            projects_analysis_section_status=projects_analysis_section_status,
            projects_analysis_section_open=projects_analysis_section_open,
            projects_ai_analysis=projects_ai_analysis,
            projects_consultant_analysis=projects_consultant_analysis,
        )

    except NotFound:
        raise
    except Exception as e:
        flash(f"Erro ao carregar projetos: {str(e)}", "error")
        return redirect(url_for("plan_dashboard", plan_id=plan_id))


@app.route("/plans/<plan_id>/projects", methods=["POST"])
def create_project(plan_id: str):
    """Create new project"""
    try:
        # Get form data
        title = request.form.get("title")
        description = request.form.get("description", "")
        status = request.form.get("status", "planned")
        priority = request.form.get("priority", "medium")
        owner = request.form.get("owner", "")
        start_date = request.form.get("start_date", "")
        end_date = request.form.get("end_date", "")
        okr_area_ref = request.form.get("okr_area_ref", "")
        notes = request.form.get("notes", "")

        # Collect activities
        activities = []
        activity_index = 0
        while True:
            activity_what = request.form.get(f"activity_what_{activity_index}")
            if not activity_what:
                break

            activity = {
                "what": activity_what,
                "who": request.form.get(f"activity_who_{activity_index}", ""),
                "when": request.form.get(f"activity_when_{activity_index}", ""),
                "amount": request.form.get(f"activity_amount_{activity_index}", ""),
                "how": request.form.get(f"activity_how_{activity_index}", ""),
                "observations": request.form.get(
                    f"activity_observations_{activity_index}", ""
                ),
            }
            activities.append(activity)
            activity_index += 1

        # Prepare project data
        project_data = {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "owner": owner,
            "start_date": start_date if start_date else None,
            "end_date": end_date if end_date else None,
            "okr_area_ref": okr_area_ref if okr_area_ref else None,
            "activities": json.dumps(activities) if activities else None,
            "notes": notes if notes else None,
        }

        # Add project to database
        project_id = db.add_project(int(plan_id), project_data)

        if project_id:
            flash("Projeto criado com sucesso!", "success")
        else:
            flash("Erro ao criar projeto", "error")

        return redirect(url_for("plan_projects", plan_id=plan_id))

    except Exception as e:
        flash(f"Erro ao criar projeto: {str(e)}", "error")
        return redirect(url_for("plan_projects", plan_id=plan_id))


@app.route("/plans/<plan_id>/projects/<int:project_id>", methods=["POST"])
def update_project_route(plan_id: str, project_id: int):
    """Update existing project"""
    try:
        # Get existing project to preserve status (controlled by kanban position)
        existing_project = db.get_project(project_id)

        # Get form data
        title = request.form.get("title")
        description = request.form.get("description", "")
        # Status is not in form anymore - preserve existing status (controlled by kanban)
        status = (
            existing_project.get("status", "planned") if existing_project else "planned"
        )
        priority = request.form.get("priority", "medium")
        owner = request.form.get("owner", "")
        start_date = request.form.get("start_date", "")
        end_date = request.form.get("end_date", "")
        okr_area_ref = request.form.get("okr_area_ref", "")
        notes = request.form.get("notes", "")

        # Collect activities
        activities = []
        activity_index = 0
        while True:
            activity_what = request.form.get(f"activity_what_{activity_index}")
            if not activity_what:
                break

            activity = {
                "what": activity_what,
                "who": request.form.get(f"activity_who_{activity_index}", ""),
                "when": request.form.get(f"activity_when_{activity_index}", ""),
                "amount": request.form.get(f"activity_amount_{activity_index}", ""),
                "how": request.form.get(f"activity_how_{activity_index}", ""),
                "observations": request.form.get(
                    f"activity_observations_{activity_index}", ""
                ),
            }
            activities.append(activity)
            activity_index += 1

        # Prepare project data
        project_data = {
            "title": title,
            "description": description,
            "status": status,  # Preserved from existing project
            "priority": priority,
            "owner": owner,
            "start_date": start_date if start_date else None,
            "end_date": end_date if end_date else None,
            "okr_area_ref": okr_area_ref if okr_area_ref else None,
            "activities": json.dumps(activities) if activities else None,
            "notes": notes if notes else None,
        }

        # Update project in database
        success = db.update_project(project_id, project_data)

        if success:
            flash("Projeto atualizado com sucesso!", "success")
        else:
            flash("Erro ao atualizar projeto", "error")

        return redirect(url_for("plan_projects", plan_id=plan_id))

    except Exception as e:
        flash(f"Erro ao atualizar projeto: {str(e)}", "error")
        return redirect(url_for("plan_projects", plan_id=plan_id))


@app.route("/plans/<plan_id>/projects/analysis", methods=["POST"])
def save_projects_analysis(plan_id: str):
    """Save projects analysis (AI and Consultant)"""
    try:
        # Get form data
        ai_analysis = request.form.get("ai_analysis", "")
        consultant_analysis = request.form.get("consultant_analysis", "")

        # Prepare analysis data
        analysis_data = {
            "ai_analysis": ai_analysis,
            "consultant_analysis": consultant_analysis,
        }

        # Save to plan_sections table using update_section_status
        db.update_section_status(
            int(plan_id),
            "projects-analysis",
            "open",  # Keep section open after saving
            closed_by=None,
            notes=json.dumps(analysis_data),
        )

        flash("Análise de projetos salva com sucesso!", "success")
        return redirect(url_for("plan_projects", plan_id=plan_id))

    except Exception as e:
        flash(f"Erro ao salvar análise: {str(e)}", "error")
        return redirect(url_for("plan_projects", plan_id=plan_id))


@app.route("/plans/<plan_id>/projects/<int:project_id>/edit")
def edit_project(plan_id: str, project_id: int):
    """Edit project - redirect to projects page with edit parameter"""
    return redirect(url_for("plan_projects", plan_id=plan_id, edit=project_id))


@app.route("/plans/<plan_id>/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(plan_id: str, project_id: int):
    """Delete a project"""
    try:
        # Delete the project
        if db.delete_project(project_id):
            flash("Projeto excluído com sucesso!", "success")
        else:
            flash("Erro ao excluir projeto.", "error")
    except Exception as e:
        flash(f"Erro ao excluir projeto: {str(e)}", "error")

    return redirect(url_for("plan_projects", plan_id=plan_id))


@app.route("/plans/<plan_id>/reports")
def plan_reports(plan_id: str):
    """Reports page"""
    plan, company = _plan_for(plan_id)
    navigation = _navigation(plan_id, "reports")

    # Get company data
    company_data_row = db.get_company_data(int(plan_id))

    # Get drivers
    drivers = db.get_drivers(int(plan_id))

    # Sample data for Reports page
    reports_summary = {"total": 3, "executivo": 1, "operacional": 2}

    # Convert to the format expected by the template
    if company_data_row:
        company_data_for_reports = {
            "trade_name": company_data_row["trade_name"],
            "legal_name": company_data_row["legal_name"],
            "cnpj": company_data_row["cnpj"],
            "coverage": {
                "physical": company_data_row["coverage_physical"],
                "online": company_data_row["coverage_online"],
            },
            "mission": company_data_row["mission"],
            "vision": company_data_row["vision"],
            "values": company_data_row["company_values"],
            "headcount": {
                "strategic": company_data_row["headcount_strategic"],
                "tactical": company_data_row["headcount_tactical"],
                "operational": company_data_row["headcount_operational"],
            },
        }
    else:
        company_data_for_reports = {
            "trade_name": plan["company"],
            "legal_name": "",
            "cnpj": "",
            "coverage": {"physical": "", "online": ""},
            "mission": "",
            "vision": "",
            "values": "",
            "headcount": {"strategic": 0, "tactical": 0, "operational": 0},
        }

    # Sample data for directionals session
    directionals_session = {
        "catalog": [
            {
                "title": driver["title"],
                "status": driver["status"].title(),
                "owner": driver["owner"],
                "updated_at": driver["updated_at"][:10]
                if driver["updated_at"]
                else driver["created_at"][:10],
            }
            for driver in drivers
        ],
        "approvals": {"selected_partners": ["Carlos Pina", "Marcos Fenecio"]},
    }

    # Get all sections data for reports
    sections_data = {}

    # Directionals data
    directionals_status = db.get_section_status(int(plan_id), "directionals-ai")
    directionals_consultant_status = db.get_section_status(
        int(plan_id), "directionals-consultant"
    )
    directionals_approvals_status = db.get_section_status(
        int(plan_id), "directionals-approvals"
    )

    sections_data["directionals"] = {
        "ai_analysis": directionals_status.get("notes", "")
        if directionals_status
        else "",
        "consultant_analysis": directionals_consultant_status.get("notes", "")
        if directionals_consultant_status
        else "",
        "approvals": directionals_approvals_status.get("notes", "")
        if directionals_approvals_status
        else "",
    }

    # OKR Global data
    global_okr_workshop = db.get_global_okr_records(int(plan_id), "workshop")
    global_okr_approvals = db.get_global_okr_records(int(plan_id), "approval")

    sections_data["okr_global"] = {
        "workshop": global_okr_workshop,
        "approvals": global_okr_approvals,
    }

    # OKR Area data
    area_workshop_status = db.get_section_status(int(plan_id), "area-okr-workshop")
    final_area_status = db.get_section_status(int(plan_id), "final-area-okr")

    sections_data["okr_area"] = {
        "workshop": area_workshop_status.get("notes", "")
        if area_workshop_status
        else "",
        "final": final_area_status.get("notes", "") if final_area_status else "",
    }

    # Projects data
    projects = db.get_projects(int(plan_id))
    projects_analysis_status = db.get_section_status(int(plan_id), "projects-analysis")

    sections_data["projects"] = {
        "projects": projects,
        "analysis": projects_analysis_status.get("notes", "")
        if projects_analysis_status
        else "",
    }

    return render_template(
        "plan_reports.html",
        plan=plan,
        company=company,
        navigation=navigation,
        active_section="reports",
        reports_summary=reports_summary,
        company_data=company_data_for_reports,
        directionals_session=directionals_session,
        sections_data=sections_data,
    )


@app.route("/plans/<plan_id>/reports/pdf/<variant>")
def plan_reports_pdf(plan_id: str, variant: str):
    """Generate PDF report - placeholder"""
    plan, company = _plan_for(plan_id)

    # For now, just redirect to the reports page
    # In a real implementation, this would generate and return a PDF
    flash(f"Gera??o de PDF {variant} ser? implementada em breve!", "info")
    return redirect(url_for("plan_reports", plan_id=plan_id))


@app.route("/plans/<plan_id>/reports/formal")
def generate_formal_report(plan_id: str):
    """Generate formal report PDF"""
    plan, company = _plan_for(plan_id)

    # For now, just show a message
    flash("Geração de Relatório Formal será implementada em breve!", "info")
    return redirect(url_for("plan_reports", plan_id=plan_id))


@app.route("/plans/<plan_id>/reports/slides")
def generate_presentation_slides(plan_id: str):
    """Generate presentation slides PDF"""
    plan, company = _plan_for(plan_id)

    # For now, just show a message
    flash("Geração de Slides de Apresentação será implementada em breve!", "info")
    return redirect(url_for("plan_reports", plan_id=plan_id))


@app.route("/uploads/<path:filename>")
def serve_uploaded_file(filename):
    """Serve uploaded files"""
    from flask import send_from_directory

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/plans/<plan_id>/company/delete-file", methods=["POST"])
def delete_company_file(plan_id: str):
    """Delete a company file"""
    import os

    file_type = request.json.get("file_type")  # 'process_map' or 'org_chart'
    filename = request.json.get("filename")

    if not file_type or not filename:
        return jsonify({"success": False, "error": "Parâmetros inválidos"}), 400

    try:
        # Remove file from filesystem
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        # Update database
        company_data_row = db.get_company_data(int(plan_id))
        if company_data_row:
            if file_type == "process_map":
                db.update_company_data(int(plan_id), {"process_map_file": None})
            elif file_type == "org_chart":
                db.update_company_data(int(plan_id), {"org_chart_file": None})

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# CRUD Operations for Company Data
@app.route("/plans/<plan_id>/company", methods=["POST"])
def update_company_data(plan_id: str):
    """Update company data"""
    import os
    import uuid
    from werkzeug.utils import secure_filename

    existing_company_data = db.get_company_data(int(plan_id))

    # Uploads de PDF removidos - não mais necessários
    # Mapa de processos: agora gerenciado pelo GRV
    # Organograma: agora gerenciado pelo GRV com funções/colaboradores

    financials = []
    i = 1
    while True:
        line = request.form.get(f"financial_line_{i}")
        revenue_raw = request.form.get(f"financial_revenue_{i}")
        margin_raw = request.form.get(f"financial_margin_{i}")
        market = request.form.get(f"financial_market_{i}")

        if not line and not revenue_raw and not margin_raw:
            break

        if line or revenue_raw or margin_raw or market:
            revenue_decimal = _to_decimal(revenue_raw)
            margin_decimal = _to_decimal(margin_raw)
            financials.append(
                {
                    "line": line or "",
                    "revenue": float(revenue_decimal)
                    if revenue_decimal is not None
                    else 0,
                    "margin": float(margin_decimal)
                    if margin_decimal is not None
                    else 0,
                    "market": market or "",
                }
            )
        i += 1

    total_revenue_decimal, total_margin_decimal = _calculate_financial_totals(
        financials
    )
    if total_revenue_decimal is not None:
        total_revenue_decimal = total_revenue_decimal.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    if total_margin_decimal is not None:
        total_margin_decimal = total_margin_decimal.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # CAMPOS REMOVIDOS (agora no cadastro centralizado em /companies/<id>):
    # Dados básicos: trade_name, legal_name (agora: companies.name, companies.legal_name)
    # Fiscal: cnpj, cnaes (agora em companies)
    # Cobertura: coverage_physical, coverage_online (agora em companies)
    # Experiência: experience_total, experience_segment (agora em companies)
    # MVV: mission, vision, company_values (agora em companies.mvv_*)
    # Headcount: headcount_* (agora em companies)
    # PDFs: process_map_file, org_chart_file (não mais usados)

    # APENAS dados específicos do plano PEV são mantidos aqui:
    # Preservar campos existentes que não estão sendo atualizados
    if existing_company_data:
        # Copiar todos os campos existentes
        data = dict(existing_company_data)
    else:
        # Criar dicionário com valores padrão para todos os campos necessários
        data = {
            "trade_name": "",
            "legal_name": "",
            "cnpj": "",
            "coverage_physical": "",
            "coverage_online": "",
            "experience_total": "",
            "experience_segment": "",
            "cnaes": [],
            "mission": "",
            "vision": "",
            "company_values": "",
            "headcount_strategic": 0,
            "headcount_tactical": 0,
            "headcount_operational": 0,
            "ai_insights": "",
            "consultant_analysis": "",
            "process_map_file": "",
            "org_chart_file": "",
            "grv_mvv_in_use": 0,
        }

    # Atualizar apenas os campos de faturamento
    data["financials"] = financials
    data["financial_total_revenue"] = (
        str(total_revenue_decimal) if total_revenue_decimal is not None else ""
    )
    data["financial_total_margin"] = (
        str(total_margin_decimal) if total_margin_decimal is not None else ""
    )
    data["other_information"] = (request.form.get("other_information") or "").strip()

    if db.update_company_data(int(plan_id), data):
        flash("Dados da empresa atualizados com sucesso!", "success")
    else:
        flash("Erro ao atualizar dados da empresa!", "error")

    return redirect(url_for("plan_company", plan_id=plan_id))


@app.route("/plans/<plan_id>/company/update-analyses", methods=["POST"])
def update_company_analyses(plan_id: str):
    """Update company analyses data via AJAX"""
    try:
        if request.is_json:
            data = request.get_json()
            update_data = {
                "ai_insights": data.get("ai_insights", ""),
                "consultant_analysis": data.get("consultant_analysis", ""),
            }
        else:
            update_data = {
                "ai_insights": request.form.get("ai_insights", ""),
                "consultant_analysis": request.form.get("consultant_analysis", ""),
            }

        if db.update_company_analyses(int(plan_id), update_data):
            return jsonify({"success": True, "message": "Análises salvas com sucesso!"})
        else:
            return jsonify({"success": False, "error": "Erro ao salvar análises"})

    except Exception as e:
        return jsonify({"success": False, "error": f"Erro ao processar: {str(e)}"})


@app.route("/plans/<plan_id>/company/generate-ai-insights", methods=["POST"])
def generate_company_ai_insights(plan_id: str):
    """Generate AI insights for company analysis"""
    try:
        from services.ai_service import ai_service

        # Get company data
        company_data = db.get_company_data(int(plan_id))
        if not company_data:
            return jsonify(
                {"success": False, "error": "Dados da empresa não encontrados"}
            )

        # Try to resolve an active agent for this page/section
        agent = None
        try:
            agents = db.get_ai_agents()
            for a in agents or []:
                # Normalize dict access regardless of row/object mapping
                page = a.get("page") if isinstance(a, dict) else None
                section = a.get("section") if isinstance(a, dict) else None
                status = a.get("status") if isinstance(a, dict) else None
                btn = a.get("button_text") if isinstance(a, dict) else None
                if status == "active" and page == "company" and section == "analyses":
                    # Prefer exact button match if available
                    if btn and btn.strip().lower() == "gerar buscas e análises de ia":
                        agent = a
                        break
                    # Fallback to the first active matching agent
                    if agent is None:
                        agent = a
        except Exception:
            agent = None

        if agent:
            # Execute configured agent, which handles integrations and prompt rendering
            result = ai_service.execute_custom_agent(agent, int(plan_id), db)
            if result.get("success"):
                output_field = (
                    agent.get("output_field", "ai_insights")
                    if isinstance(agent, dict)
                    else "ai_insights"
                )
                insights_text = result.get("result", "")
                # Persist into company data
                try:
                    existing_analyses = db.get_company_data(int(plan_id)) or {}
                    existing_ai = existing_analyses.get("ai_insights") or ""
                    existing_consultant = (
                        existing_analyses.get("consultant_analysis") or ""
                    )
                    if output_field == "consultant_analysis":
                        db.update_company_analyses(
                            int(plan_id),
                            {
                                "ai_insights": existing_ai,
                                "consultant_analysis": insights_text,
                            },
                        )
                    elif output_field == "ai_insights":
                        db.update_company_analyses(
                            int(plan_id),
                            {
                                "ai_insights": insights_text,
                                "consultant_analysis": existing_consultant,
                            },
                        )
                    else:
                        # Campo nao suportado para atualizacao direta; resultado disponivel apenas na resposta
                        pass
                except Exception:
                    # Ignore persistence failure, still return generated text
                    pass
                return jsonify(
                    {
                        "success": True,
                        "insights": insights_text,
                        "agent": result.get("agent_id"),
                    }
                )
            else:
                # If agent execution failed, fallback to generic insights
                insights = ai_service.generate_insights(
                    company_data, "Análise estratégica da empresa"
                )
                if insights:
                    return jsonify(
                        {"success": True, "insights": insights, "fallback": True}
                    )
                return jsonify(
                    {
                        "success": False,
                        "error": result.get("error") or "Erro ao gerar insights da IA",
                    }
                )

        # No agent configured: fallback to generic insights
        insights = ai_service.generate_insights(
            company_data, "Análise estratégica da empresa"
        )
        if insights:
            return jsonify({"success": True, "insights": insights, "fallback": True})
        else:
            return jsonify(
                {
                    "success": False,
                    "error": "Nenhum agente configurado e falha no gerador padrão",
                }
            )

    except Exception as e:
        return jsonify({"success": False, "error": f"Erro ao processar: {str(e)}"})


# Section status for Company page (Concluir/Reabrir todas)
@app.route("/plans/<plan_id>/sections/company/status", methods=["POST"])
def update_company_section_status(plan_id: str):
    try:
        payload = request.get_json() or {}
        status = (payload.get("status") or "").strip()
        closed_by = payload.get("closed_by")
        notes = payload.get("notes")
        if status not in ("open", "closed"):
            return jsonify({"success": False, "error": "Status inválido"}), 400
        ok = db.update_section_status(
            int(plan_id), "company", status, closed_by=closed_by, notes=notes
        )
        if ok:
            # Retornar o status atual para UI
            current = db.get_section_status(int(plan_id), "company") or {
                "status": status,
                "closed_by": closed_by,
                "notes": notes,
            }
            return jsonify({"success": True, "section": current})
        return (
            jsonify({"success": False, "error": "Falha ao atualizar status da seção"}),
            500,
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/plans/<plan_id>/participants", methods=["POST"])
def add_participant(plan_id: str):
    """Add new participant"""
    if request.is_json:
        # AJAX request
        data = request.get_json()
        participant_data = {
            "name": data.get("name"),
            "role": data.get("position", ""),
            "relation": data.get("department", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "cpf": "",  # Campo não usado no formulário atual
            "status": "active",
        }

        participant_id = db.add_participant(int(plan_id), participant_data)
        if participant_id:
            # Buscar o participante criado para retornar os dados
            participant = db.get_participant(participant_id)
            return jsonify({"success": True, "participant": participant})
        else:
            return (
                jsonify({"success": False, "error": "Erro ao adicionar participante"}),
                500,
            )
    else:
        # Form request
        participant_data = {
            "name": request.form.get("name"),
            "role": request.form.get("role"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
        }

        participant_id = db.add_participant(int(plan_id), participant_data)
        if participant_id:
            flash("Participante adicionado com sucesso!", "success")
        else:
            flash("Erro ao adicionar participante!", "error")

        return redirect(url_for("plan_participants", plan_id=plan_id))


@app.route("/plans/<plan_id>/participants/<participant_id>", methods=["GET"])
def get_participant(plan_id: str, participant_id: str):
    """Get participant data for editing"""
    participant = db.get_participant(participant_id)
    if participant:
        return jsonify({"success": True, "participant": participant})
    else:
        return jsonify({"success": False, "error": "Participante não encontrado"}), 404


@app.route("/plans/<plan_id>/participants/<participant_id>", methods=["PUT"])
def update_participant(plan_id: str, participant_id: str):
    """Update participant data"""
    data = request.get_json()

    participant_data = {
        "name": data.get("name"),
        "role": data.get("role"),
        "relation": data.get("relation"),
        "email": data.get("email"),
        "cpf": data.get("cpf"),
        "phone": data.get("phone"),
        "status": data.get("status"),
    }

    if db.update_participant(participant_id, participant_data):
        return jsonify({"success": True})
    else:
        return (
            jsonify({"success": False, "error": "Erro ao atualizar participante"}),
            500,
        )


@app.route("/plans/<plan_id>/participants/<participant_id>/status", methods=["POST"])
def update_participant_status(plan_id: str, participant_id: str):
    """Update participant status"""
    data = request.get_json()
    new_status = data.get("status")

    if not new_status or new_status not in ["active", "inactive"]:
        return jsonify({"success": False, "error": "Status inválido"}), 400

    if db.update_participant_status(participant_id, new_status):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Erro ao atualizar status"}), 500


# Message Templates Routes
@app.route("/plans/<plan_id>/messages", methods=["GET"])
def get_message_templates(plan_id: str):
    """Get message templates for a plan"""
    templates = db.get_message_templates(int(plan_id))
    return jsonify({"success": True, "templates": templates})


@app.route("/plans/<plan_id>/messages/<message_type>", methods=["GET"])
def get_message_template(plan_id: str, message_type: str):
    """Get specific message template"""
    template = db.get_message_template(int(plan_id), message_type)
    if template:
        return jsonify({"success": True, "template": template})
    else:
        return jsonify({"success": False, "error": "Template não encontrado"}), 404


@app.route("/plans/<plan_id>/messages/<message_type>", methods=["POST"])
def save_message_template(plan_id: str, message_type: str):
    """Save or update message template"""
    data = request.get_json()
    subject = data.get("subject", "")
    content = data.get("content", "")

    if db.save_message_template(int(plan_id), message_type, subject, content):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Erro ao salvar template"}), 500


@app.route(
    "/plans/<plan_id>/participants/<participant_id>/send-message", methods=["POST"]
)
def send_participant_message(plan_id: str, participant_id: str):
    """Send message to participant"""
    data = request.get_json()
    message_type = data.get("message_type")  # 'email' or 'whatsapp'

    # Get participant data
    participant = db.get_participant(int(participant_id))
    if not participant:
        return jsonify({"success": False, "error": "Participante não encontrado"}), 404

    # Get message template
    template = db.get_message_template(int(plan_id), message_type)
    if not template:
        return (
            jsonify({"success": False, "error": "Template de mensagem não encontrado"}),
            404,
        )

    # Get plan data for template variables
    plan = db.get_plan(int(plan_id))
    if not plan:
        return jsonify({"success": False, "error": "Plano não encontrado"}), 404

    # Process template with variables
    processed_content = template["content"].replace(
        "{{name}}", participant["name"] or ""
    )
    processed_content = processed_content.replace("{{role}}", participant["role"] or "")
    processed_content = processed_content.replace("{{plan_name}}", plan["name"] or "")

    processed_subject = template["subject"].replace(
        "{{name}}", participant["name"] or ""
    )
    processed_subject = processed_subject.replace("{{role}}", participant["role"] or "")
    processed_subject = processed_subject.replace("{{plan_name}}", plan["name"] or "")

    return jsonify(
        {
            "success": True,
            "message": {
                "subject": processed_subject,
                "content": processed_content,
                "participant": participant,
                "message_type": message_type,
            },
        }
    )


@app.route("/plans/<plan_id>/participants/<participant_id>", methods=["DELETE"])
def delete_participant(plan_id: str, participant_id: str):
    """Delete participant"""
    if db.delete_participant(participant_id):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Failed to delete participant"}), 500


# CRUD Operations for Drivers
@app.route("/plans/<plan_id>/drivers", methods=["POST"])
def add_driver(plan_id: str):
    """Add new driver"""
    driver_data = {
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "status": request.form.get("status", "draft"),
        "priority": request.form.get("priority"),
        "owner": request.form.get("owner"),
    }

    if db.add_driver(plan_id, driver_data):
        flash("Direcionador adicionado com sucesso!", "success")
    else:
        flash("Erro ao adicionar direcionador!", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


# CRUD Operations for Interviews
@app.route("/plans/<plan_id>/interviews", methods=["POST"])
def add_interview(plan_id: str):
    """Add new interview"""
    interview_data = {
        "participant_name": request.form.get("participant"),
        "consultant_name": request.form.get("consultant"),
        "interview_date": request.form.get("date"),
        "format": request.form.get("format"),
        "notes": request.form.get("notes"),
    }

    if db.add_interview(plan_id, interview_data):
        flash("Entrevista registrada com sucesso!", "success")
    else:
        flash("Erro ao registrar entrevista!", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/interviews/<interview_id>", methods=["PUT"])
def update_interview(plan_id: str, interview_id: str):
    """Update interview"""
    # Verificar se é uma requisição AJAX (JSON) ou formulário HTML
    if request.is_json:
        data = request.get_json()
        interview_data = {
            "participant_name": data.get("participant_name"),
            "consultant_name": data.get("consultant_name"),
            "interview_date": data.get("interview_date"),
            "format": data.get("format"),
            "notes": data.get("notes"),
        }
    else:
        # Dados do formulário HTML
        interview_data = {
            "participant_name": request.form.get("participant"),
            "consultant_name": request.form.get("consultant"),
            "interview_date": request.form.get("date"),
            "format": request.form.get("format"),
            "notes": request.form.get("notes"),
        }

    if db.update_interview(int(interview_id), interview_data):
        if request.is_json:
            return jsonify({"success": True})
        else:
            flash("Entrevista atualizada com sucesso!", "success")
            return redirect(url_for("plan_drivers", plan_id=plan_id))
    else:
        if request.is_json:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar entrevista"}),
                500,
            )
        else:
            flash("Erro ao atualizar entrevista!", "error")
            return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/interviews/<interview_id>", methods=["DELETE"])
def delete_interview(plan_id: str, interview_id: str):
    """Delete interview"""
    if db.delete_interview(int(interview_id)):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Erro ao excluir entrevista"}), 500


@app.route("/plans/<plan_id>/interviews/<interview_id>", methods=["GET"])
def get_interview(plan_id: str, interview_id: str):
    """Get interview data for editing"""
    interview = db.get_interview(int(interview_id))
    if interview:
        return jsonify({"success": True, "interview": interview})
    else:
        return jsonify({"success": False, "error": "Entrevista não encontrada"}), 404


@app.route("/plans/<plan_id>/sections/<section_name>/status", methods=["POST"])
def update_section_status(plan_id: str, section_name: str):
    """Update section status (open/closed)"""
    logger.info(f"\n=== UPDATE SECTION STATUS ===")
    logger.info(f"Plan ID: {plan_id}")
    logger.info(f"Section Name: {section_name}")

    data = request.get_json()
    logger.info(f"Dados recebidos: {data}")

    status = data.get("status")  # 'open' or 'closed'
    closed_by = data.get("closed_by", "Sistema")
    notes = data.get("notes", "")

    logger.info(f"Status: {status}, Closed By: {closed_by}, Notes: {notes}")

    if status not in ["open", "closed"]:
        logger.info(f"Erro: Status inválido - {status}")
        return jsonify({"success": False, "error": "Status inválido"}), 400

    result = db.update_section_status(
        int(plan_id), section_name, status, closed_by, notes
    )
    logger.info(f"Resultado da atualização no banco: {result}")

    if result:
        logger.info(f"Sucesso! Retornando status: {status}")
        return jsonify({"success": True, "status": status})
    else:
        logger.info("Erro ao atualizar status no banco de dados")
        return (
            jsonify({"success": False, "error": "Erro ao atualizar status da seção"}),
            500,
        )


@app.route("/plans/<plan_id>/sections/<section_name>/status", methods=["GET"])
def get_section_status(plan_id: str, section_name: str):
    """Get section status"""
    section_status = db.get_section_status(int(plan_id), section_name)
    if section_status:
        return jsonify({"success": True, "section": section_status})
    else:
        # Se não existe registro, assumir que está aberto
        return jsonify({"success": True, "section": {"status": "open"}})


@app.route("/plans/<plan_id>/sections/alignment/consultant-notes", methods=["POST"])
def save_alignment_consultant_notes(plan_id: str):
    """Save alignment consultant notes"""
    consultant_notes = request.form.get("consultant_notes", "")

    if db.update_section_consultant_notes(
        int(plan_id), "alignments-found", consultant_notes
    ):
        flash("Parecer do consultor salvo com sucesso!", "success")
    else:
        flash("Erro ao salvar parecer do consultor.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/sections/misalignment/consultant-notes", methods=["POST"])
def save_misalignment_consultant_notes(plan_id: str):
    """Save misalignment consultant notes"""
    consultant_notes = request.form.get("consultant_notes", "")

    if db.update_section_consultant_notes(
        int(plan_id), "misalignments-critical", consultant_notes
    ):
        flash("Parecer do consultor salvo com sucesso!", "success")
    else:
        flash("Erro ao salvar parecer do consultor.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/sections/workshop/consultant-notes", methods=["POST"])
def save_workshop_consultant_notes(plan_id: str):
    """Save workshop consultant notes"""
    consultant_notes = request.form.get("consultant_notes", "")

    if db.update_section_consultant_notes(
        int(plan_id), "workshop-final-analysis", consultant_notes
    ):
        flash("Parecer do consultor salvo com sucesso!", "success")
    else:
        flash("Erro ao salvar parecer do consultor.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route(
    "/plans/<plan_id>/sections/directionals/consultant-analysis", methods=["POST"]
)
def save_directionals_consultant_analysis(plan_id: str):
    """Save directionals consultant analysis"""
    consultant_directionals = request.form.get("consultant_directionals", "")

    logger.info(f"DEBUG: Salvando análise do consultor - plan_id: {plan_id}")
    logger.info(
        f"DEBUG: Conteúdo: {consultant_directionals[:100] if consultant_directionals else 'VAZIO'}"
    )

    # Get existing section data to preserve approvals
    section_status = db.get_section_status(int(plan_id), "directionals-approvals")
    existing_approvals = []

    logger.info(f"DEBUG: Section status existente: {section_status}")

    if section_status and section_status.get("notes"):
        try:
            # Try to parse existing data as JSON
            existing_data = json.loads(section_status.get("notes", "{}"))
            existing_approvals = existing_data.get("approvals", [])
        except (json.JSONDecodeError, TypeError):
            # If it's not JSON, it was plain text, no approvals to preserve
            pass

    # Create combined data with consultant notes and existing approvals
    combined_data = {
        "consultant_notes": consultant_directionals,
        "approvals": existing_approvals,
    }

    logger.info(f"DEBUG: Combined data: {combined_data}")

    # Save combined data as JSON
    result = db.update_section_consultant_notes(
        int(plan_id), "directionals-approvals", json.dumps(combined_data)
    )

    logger.info(f"DEBUG: Resultado do salvamento: {result}")

    if result:
        flash("Análise do consultor salva com sucesso!", "success")
    else:
        flash("Erro ao salvar análise do consultor.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/workshop-adjustments", methods=["POST"])
def add_workshop_adjustment(plan_id: str):
    """Add workshop adjustment"""
    adjustment_data = {
        "type": request.form.get("type", ""),
        "original": request.form.get("original", ""),
        "adjusted": request.form.get("adjusted", ""),
        "reason": request.form.get("reason", ""),
    }

    # Get existing adjustments
    section_status = db.get_section_status(int(plan_id), "workshop-final-analysis")
    try:
        adjustments = (
            json.loads(section_status.get("adjustments", "[]"))
            if section_status
            else []
        )
    except (json.JSONDecodeError, TypeError):
        adjustments = []

    # Add new adjustment
    adjustments.append(adjustment_data)

    # Save updated adjustments
    if db.update_section_adjustments(
        int(plan_id), "workshop-final-analysis", json.dumps(adjustments)
    ):
        flash("Ajuste registrado com sucesso!", "success")
    else:
        flash("Erro ao registrar ajuste.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/directionals-approvals", methods=["POST"])
def add_directionals_approval(plan_id: str):
    """Add directionals approval"""
    approval_data = {
        "partner": request.form.get("partner", ""),
        "status": request.form.get("status", ""),
        "comments": request.form.get("comments", ""),
        "date": request.form.get("date", ""),
    }

    # Get existing approvals
    section_status = db.get_section_status(int(plan_id), "directionals-approvals")
    try:
        # Parse the JSON data correctly from notes field
        if section_status and section_status.get("notes"):
            combined_data = json.loads(section_status.get("notes", "{}"))
            approvals = combined_data.get("approvals", [])
        else:
            approvals = []
    except (json.JSONDecodeError, TypeError):
        approvals = []

    # Add new approval
    approvals.append(approval_data)

    # Get existing consultant_notes to preserve them
    consultant_notes = ""
    try:
        if section_status and section_status.get("notes"):
            combined_data = json.loads(section_status.get("notes", "{}"))
            consultant_notes = combined_data.get("consultant_notes", "")
    except (json.JSONDecodeError, TypeError):
        pass

    # Combine approvals and consultant_notes
    combined_data = {"approvals": approvals, "consultant_notes": consultant_notes}

    # Save updated data using update_section_consultant_notes to maintain consistency
    if db.update_section_consultant_notes(
        int(plan_id), "directionals-approvals", json.dumps(combined_data)
    ):
        flash("Aprovação registrada com sucesso!", "success")
    else:
        flash("Erro ao registrar aprovação.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


# Vision Records CRUD operations
@app.route("/plans/<plan_id>/vision-records", methods=["POST"])
def add_vision_record(plan_id: str):
    """Add new vision record"""
    participants_text = request.form.get("participants", "")  # Texto livre
    consultants_text = request.form.get("consultants", "")  # Texto livre
    vision_date = request.form.get("vision_date")
    format_type = request.form.get("format")
    notes = request.form.get("notes", "")

    vision_data = {
        "participants": participants_text,
        "consultants": consultants_text,
        "vision_date": vision_date,
        "format": format_type,
        "notes": notes,
    }

    if db.add_vision_record(int(plan_id), vision_data):
        flash("Visão dos sócios registrada com sucesso!", "success")
    else:
        flash("Erro ao registrar visão dos sócios.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/vision-records/<vision_id>", methods=["PUT"])
def update_vision_record(plan_id: str, vision_id: str):
    """Update vision record"""
    if request.is_json:
        # AJAX request
        data = request.get_json()
        vision_data = {
            "participants": data.get("participants", ""),
            "consultants": data.get("consultants", ""),
            "vision_date": data.get("vision_date"),
            "format": data.get("format"),
            "notes": data.get("notes", ""),
        }
    else:
        # Form request
        participants_text = request.form.get("participants", "")
        consultants_text = request.form.get("consultants", "")
        vision_data = {
            "participants": participants_text,
            "consultants": consultants_text,
            "vision_date": request.form.get("vision_date"),
            "format": request.form.get("format"),
            "notes": request.form.get("notes", ""),
        }

    if db.update_vision_record(int(vision_id), vision_data):
        if request.is_json:
            return jsonify({"success": True})
        else:
            flash("Visão dos sócios atualizada com sucesso!", "success")
            return redirect(url_for("plan_drivers", plan_id=plan_id))
    else:
        if request.is_json:
            return (
                jsonify(
                    {"success": False, "error": "Erro ao atualizar visão dos sócios"}
                ),
                500,
            )
        else:
            flash("Erro ao atualizar visão dos sócios.", "error")
            return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/vision-records/<vision_id>", methods=["DELETE"])
def delete_vision_record(plan_id: str, vision_id: str):
    """Delete vision record"""
    if db.delete_vision_record(int(vision_id)):
        return jsonify({"success": True})
    else:
        return (
            jsonify({"success": False, "error": "Erro ao excluir visão dos sócios"}),
            500,
        )


@app.route("/plans/<plan_id>/vision-records/<vision_id>", methods=["GET"])
def get_vision_record(plan_id: str, vision_id: str):
    """Get vision record data for editing"""
    vision_record = db.get_vision_record(int(vision_id))
    if vision_record:
        return jsonify({"success": True, "vision_record": vision_record})
    else:
        return (
            jsonify({"success": False, "error": "Visão dos sócios não encontrada"}),
            404,
        )


# CRUD Operations for Market Records
@app.route("/plans/<plan_id>/market-records", methods=["POST"])
def add_market_record(plan_id: str):
    """Add new market record"""
    participants_text = request.form.get("market_participants", "")  # Texto livre
    consultants_text = request.form.get("market_consultants", "")  # Texto livre
    market_date = request.form.get("market_date")
    format_type = request.form.get("format")
    global_context = request.form.get("global_context", "")
    sector_context = request.form.get("sector_context", "")
    market_size = request.form.get("market_size", "")
    growth_space = request.form.get("growth_space", "")
    threats = request.form.get("threats", "")
    consumer_behavior = request.form.get("consumer_behavior", "")
    competition = request.form.get("competition", "")
    notes = request.form.get("notes", "")

    market_data = {
        "participants": participants_text,
        "consultants": consultants_text,
        "market_date": market_date,
        "format": format_type,
        "global_context": global_context,
        "sector_context": sector_context,
        "market_size": market_size,
        "growth_space": growth_space,
        "threats": threats,
        "consumer_behavior": consumer_behavior,
        "competition": competition,
        "notes": notes,
    }

    if db.add_market_record(int(plan_id), market_data):
        flash("Possibilidades do mercado registradas com sucesso!", "success")
    else:
        flash("Erro ao registrar possibilidades do mercado.", "error")

    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/market-records/<market_id>", methods=["PUT"])
def update_market_record(plan_id: str, market_id: str):
    """Update market record"""
    if request.is_json:
        # AJAX request
        data = request.get_json()
        market_data = {
            "participants": data.get("market_participants", ""),
            "consultants": data.get("market_consultants", ""),
            "market_date": data.get("market_date"),
            "format": data.get("format"),
            "global_context": data.get("global_context", ""),
            "sector_context": data.get("sector_context", ""),
            "market_size": data.get("market_size", ""),
            "growth_space": data.get("growth_space", ""),
            "threats": data.get("threats", ""),
            "consumer_behavior": data.get("consumer_behavior", ""),
            "competition": data.get("competition", ""),
            "notes": data.get("notes", ""),
        }
    else:
        # Form request
        participants_text = request.form.get("market_participants", "")
        consultants_text = request.form.get("market_consultants", "")
        market_data = {
            "participants": participants_text,
            "consultants": consultants_text,
            "market_date": request.form.get("market_date"),
            "format": request.form.get("format"),
            "global_context": request.form.get("global_context", ""),
            "sector_context": request.form.get("sector_context", ""),
            "market_size": request.form.get("market_size", ""),
            "growth_space": request.form.get("growth_space", ""),
            "threats": request.form.get("threats", ""),
            "consumer_behavior": request.form.get("consumer_behavior", ""),
            "competition": request.form.get("competition", ""),
            "notes": request.form.get("notes", ""),
        }

    if db.update_market_record(int(market_id), market_data):
        if request.is_json:
            return jsonify({"success": True})
        else:
            flash("Possibilidades do mercado atualizadas com sucesso!", "success")
            return redirect(url_for("plan_drivers", plan_id=plan_id))
    else:
        if request.is_json:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Erro ao atualizar possibilidades do mercado",
                    }
                ),
                500,
            )
        else:
            flash("Erro ao atualizar possibilidades do mercado!", "error")
            return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/market-records/<market_id>", methods=["DELETE"])
def delete_market_record(plan_id: str, market_id: str):
    """Delete market record"""
    if db.delete_market_record(int(market_id)):
        return jsonify({"success": True})
    else:
        return (
            jsonify(
                {"success": False, "error": "Erro ao excluir possibilidades do mercado"}
            ),
            500,
        )


@app.route("/plans/<plan_id>/market-records/<market_id>", methods=["GET"])
def get_market_record(plan_id: str, market_id: str):
    """Get market record data for editing"""
    market_record = db.get_market_record(int(market_id))
    if market_record:
        return jsonify({"success": True, "market_record": market_record})
    else:
        return (
            jsonify(
                {"success": False, "error": "Possibilidades do mercado não encontradas"}
            ),
            404,
        )


# CRUD Operations for Company Records
@app.route("/plans/<plan_id>/company-records", methods=["POST"])
def add_company_record(plan_id: str):
    """Add new company record"""
    payload = request.get_json() if request.is_json else request.form
    participants_text = (
        payload.get("company_participants") or payload.get("participants") or ""
    ).strip()
    consultants_text = (
        payload.get("company_consultants") or payload.get("consultants") or ""
    ).strip()
    company_date = payload.get("company_date")
    bsc_financial = (payload.get("bsc_financial") or "").strip()
    bsc_commercial = (payload.get("bsc_commercial") or "").strip()
    bsc_process = (payload.get("bsc_process") or "").strip()
    bsc_learning = (payload.get("bsc_learning") or "").strip()
    tri_commercial = (payload.get("tri_commercial") or "").strip()
    tri_adm_fin = (payload.get("tri_adm_fin") or "").strip()
    tri_operational = (payload.get("tri_operational") or "").strip()
    notes = (payload.get("company_notes") or payload.get("notes") or "").strip()

    company_data = {
        "participants": participants_text,
        "consultants": consultants_text,
        "company_date": company_date,
        "bsc_financial": bsc_financial,
        "bsc_commercial": bsc_commercial,
        "bsc_process": bsc_process,
        "bsc_learning": bsc_learning,
        "tri_commercial": tri_commercial,
        "tri_adm_fin": tri_adm_fin,
        "tri_operational": tri_operational,
        "notes": notes,
    }

    if not any(
        [
            participants_text,
            consultants_text,
            bsc_financial,
            bsc_commercial,
            bsc_process,
            bsc_learning,
            tri_commercial,
            tri_adm_fin,
            tri_operational,
            notes,
        ]
    ):
        message = "Informe ao menos um campo para registrar possibilidades da empresa."
        if request.is_json:
            return jsonify({"success": False, "error": message}), 400
        flash(message, "error")
        return redirect(url_for("plan_drivers", plan_id=plan_id))

    created = db.add_company_record(int(plan_id), company_data)
    if request.is_json:
        if created:
            return jsonify({"success": True, "company_record": company_data}), 201
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro ao registrar possibilidades da empresa.",
                }
            ),
            500,
        )

    if created:
        flash("Possibilidades da empresa registradas com sucesso!", "success")
    else:
        flash("Erro ao registrar possibilidades da empresa.", "error")
    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/company-records/<company_id>", methods=["PUT"])
def update_company_record(plan_id: str, company_id: str):
    """Update company record"""
    if request.is_json:
        data = request.get_json()
        company_data = {
            "participants": data.get("company_participants", ""),
            "consultants": data.get("company_consultants", ""),
            "company_date": data.get("company_date"),
            "bsc_financial": data.get("bsc_financial", ""),
            "bsc_commercial": data.get("bsc_commercial", ""),
            "bsc_process": data.get("bsc_process", ""),
            "bsc_learning": data.get("bsc_learning", ""),
            "tri_commercial": data.get("tri_commercial", ""),
            "tri_adm_fin": data.get("tri_adm_fin", ""),
            "tri_operational": data.get("tri_operational", ""),
            "notes": data.get("company_notes", ""),
        }
    else:
        participants_text = request.form.get("company_participants", "")
        consultants_text = request.form.get("company_consultants", "")
        company_data = {
            "participants": participants_text,
            "consultants": consultants_text,
            "company_date": request.form.get("company_date"),
            "bsc_financial": request.form.get("bsc_financial", ""),
            "bsc_commercial": request.form.get("bsc_commercial", ""),
            "bsc_process": request.form.get("bsc_process", ""),
            "bsc_learning": request.form.get("bsc_learning", ""),
            "tri_commercial": request.form.get("tri_commercial", ""),
            "tri_adm_fin": request.form.get("tri_adm_fin", ""),
            "tri_operational": request.form.get("tri_operational", ""),
            "notes": request.form.get("company_notes", ""),
        }

    if db.update_company_record(int(company_id), company_data):
        if request.is_json:
            return jsonify({"success": True})
        else:
            flash("Possibilidades da empresa atualizadas com sucesso!", "success")
            return redirect(url_for("plan_drivers", plan_id=plan_id))
    else:
        if request.is_json:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Erro ao atualizar possibilidades da empresa",
                    }
                ),
                500,
            )
        else:
            flash("Erro ao atualizar possibilidades da empresa!", "error")
            return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/company-records/<company_id>", methods=["DELETE"])
def delete_company_record(plan_id: str, company_id: str):
    """Delete company record"""
    if db.delete_company_record(int(company_id)):
        return jsonify({"success": True})
    else:
        return (
            jsonify(
                {"success": False, "error": "Erro ao excluir possibilidades da empresa"}
            ),
            500,
        )


@app.route("/plans/<plan_id>/company-records/<company_id>", methods=["GET"])
def get_company_record(plan_id: str, company_id: str):
    """Get company record data for editing"""
    company_record = db.get_company_record(int(company_id))
    if company_record:
        return jsonify({"success": True, "company_record": company_record})
    else:
        return (
            jsonify(
                {"success": False, "error": "Possibilidades da empresa não encontradas"}
            ),
            404,
        )


# CRUD Operations for Alignment Records
@app.route("/plans/<plan_id>/alignment-records", methods=["POST"])
def add_alignment_record(plan_id: str):
    """Add new alignment record"""
    payload = request.get_json() if request.is_json else request.form
    alignment_data = {
        "topic": (payload.get("topic") or "").strip(),
        "description": (payload.get("description") or "").strip(),
        "consensus": (payload.get("consensus") or "").strip(),
        "priority": (payload.get("priority") or "").strip(),
        "notes": (payload.get("notes") or "").strip(),
    }

    if not alignment_data["topic"]:
        message = "Tópico do alinhamento é obrigatório."
        if request.is_json:
            return jsonify({"success": False, "error": message}), 400
        flash(message, "error")
        return redirect(url_for("plan_drivers", plan_id=plan_id))

    created = db.add_alignment_record(int(plan_id), alignment_data)
    if request.is_json:
        if created:
            return jsonify({"success": True, "alignment": alignment_data}), 201
        return (
            jsonify({"success": False, "error": "Erro ao registrar alinhamento."}),
            500,
        )

    if created:
        flash("Alinhamento registrado com sucesso!", "success")
    else:
        flash("Erro ao registrar alinhamento.", "error")
    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/alignment-records/<alignment_id>", methods=["PUT"])
def update_alignment_record(plan_id: str, alignment_id: str):
    """Update alignment record"""
    if request.is_json:
        data = request.get_json()
        alignment_data = {
            "topic": data.get("topic", ""),
            "description": data.get("description", ""),
            "consensus": data.get("consensus", ""),
            "priority": data.get("priority", ""),
            "notes": data.get("notes", ""),
        }
    else:
        alignment_data = {
            "topic": request.form.get("topic", ""),
            "description": request.form.get("description", ""),
            "consensus": request.form.get("consensus", ""),
            "priority": request.form.get("priority", ""),
            "notes": request.form.get("notes", ""),
        }

    if db.update_alignment_record(int(alignment_id), alignment_data):
        if request.is_json:
            return jsonify({"success": True})
        else:
            flash("Alinhamento atualizado com sucesso!", "success")
            return redirect(url_for("plan_drivers", plan_id=plan_id))
    else:
        if request.is_json:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar alinhamento"}),
                500,
            )
        else:
            flash("Erro ao atualizar alinhamento!", "error")
            return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/alignment-records/<alignment_id>", methods=["DELETE"])
def delete_alignment_record(plan_id: str, alignment_id: str):
    """Delete alignment record"""
    if db.delete_alignment_record(int(alignment_id)):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Erro ao excluir alinhamento"}), 500


@app.route("/plans/<plan_id>/alignment-records/<alignment_id>", methods=["GET"])
def get_alignment_record(plan_id: str, alignment_id: str):
    """Get alignment record data for editing"""
    alignment_record = db.get_alignment_record(int(alignment_id))
    if alignment_record:
        return jsonify({"success": True, "alignment_record": alignment_record})
    else:
        return jsonify({"success": False, "error": "Alinhamento não encontrado"}), 404


# CRUD Operations for Misalignment Records
@app.route("/plans/<plan_id>/misalignment-records", methods=["POST"])
def add_misalignment_record(plan_id: str):
    """Add new misalignment record"""
    payload = request.get_json() if request.is_json else request.form
    misalignment_data = {
        "issue": (payload.get("issue") or "").strip(),
        "description": (payload.get("description") or "").strip(),
        "severity": (payload.get("severity") or "").strip(),
        "impact": (payload.get("impact") or "").strip(),
        "notes": (payload.get("notes") or "").strip(),
    }

    if not misalignment_data["issue"]:
        message = "Título do desalinhamento é obrigatório."
        if request.is_json:
            return jsonify({"success": False, "error": message}), 400
        flash(message, "error")
        return redirect(url_for("plan_drivers", plan_id=plan_id))

    created = db.add_misalignment_record(int(plan_id), misalignment_data)
    if request.is_json:
        if created:
            return jsonify({"success": True, "misalignment": misalignment_data}), 201
        return (
            jsonify({"success": False, "error": "Erro ao registrar desalinhamento."}),
            500,
        )

    if created:
        flash("Desalinhamento registrado com sucesso!", "success")
    else:
        flash("Erro ao registrar desalinhamento.", "error")
    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/misalignment-records/<misalignment_id>", methods=["PUT"])
def update_misalignment_record(plan_id: str, misalignment_id: str):
    """Update misalignment record"""
    if request.is_json:
        data = request.get_json()
        misalignment_data = {
            "issue": data.get("issue", ""),
            "description": data.get("description", ""),
            "severity": data.get("severity", ""),
            "impact": data.get("impact", ""),
            "notes": data.get("notes", ""),
        }
    else:
        misalignment_data = {
            "issue": request.form.get("issue", ""),
            "description": request.form.get("description", ""),
            "severity": request.form.get("severity", ""),
            "impact": request.form.get("impact", ""),
            "notes": request.form.get("notes", ""),
        }

    if db.update_misalignment_record(int(misalignment_id), misalignment_data):
        if request.is_json:
            return jsonify({"success": True})
        else:
            flash("Desalinhamento atualizado com sucesso!", "success")
            return redirect(url_for("plan_drivers", plan_id=plan_id))
    else:
        if request.is_json:
            return (
                jsonify(
                    {"success": False, "error": "Erro ao atualizar desalinhamento"}
                ),
                500,
            )
        else:
            flash("Erro ao atualizar desalinhamento!", "error")
            return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route(
    "/plans/<plan_id>/misalignment-records/<misalignment_id>", methods=["DELETE"]
)
def delete_misalignment_record(plan_id: str, misalignment_id: str):
    """Delete misalignment record"""
    if db.delete_misalignment_record(int(misalignment_id)):
        return jsonify({"success": True})
    else:
        return (
            jsonify({"success": False, "error": "Erro ao excluir desalinhamento"}),
            500,
        )


@app.route("/plans/<plan_id>/misalignment-records/<misalignment_id>", methods=["GET"])
def get_misalignment_record(plan_id: str, misalignment_id: str):
    """Get misalignment record data for editing"""
    misalignment_record = db.get_misalignment_record(int(misalignment_id))
    if misalignment_record:
        return jsonify({"success": True, "misalignment_record": misalignment_record})
    else:
        return (
            jsonify({"success": False, "error": "Desalinhamento não encontrado"}),
            404,
        )


# CRUD Operations for Directional Records
@app.route("/plans/<plan_id>/directional-records", methods=["POST"])
def add_directional_record(plan_id: str):
    """Add new directional record"""
    payload = request.get_json() if request.is_json else request.form
    directional_data = {
        "title": (
            payload.get("title") or payload.get("directional_title") or ""
        ).strip(),
        "description": (
            payload.get("description") or payload.get("directional_description") or ""
        ).strip(),
        "type": (payload.get("type") or payload.get("directional_type") or "").strip(),
        "priority": (
            payload.get("priority") or payload.get("directional_priority") or ""
        ).strip(),
        "status": (payload.get("status") or "active").strip(),
        "owner": (payload.get("owner") or "").strip(),
        "notes": (payload.get("notes") or "").strip(),
    }

    if not directional_data["title"]:
        message = "Título do direcionador é obrigatório."
        if request.is_json:
            return jsonify({"success": False, "error": message}), 400
        flash(message, "error")
        return redirect(url_for("plan_drivers", plan_id=plan_id))

    created = db.add_directional_record(int(plan_id), directional_data)
    if request.is_json:
        if created:
            return jsonify({"success": True, "directional": directional_data}), 201
        return (
            jsonify({"success": False, "error": "Erro ao registrar direcionador."}),
            500,
        )

    if created:
        flash("Direcionador registrado com sucesso!", "success")
    else:
        flash("Erro ao registrar direcionador.", "error")
    return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/directional-records/<directional_id>", methods=["PUT"])
def update_directional_record(plan_id: str, directional_id: str):
    """Update directional record"""
    if request.is_json:
        data = request.get_json()
        directional_data = {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "type": data.get("type", ""),
            "priority": data.get("priority", ""),
            "status": data.get("status", ""),
            "owner": data.get("owner", ""),
            "notes": data.get("notes", ""),
        }
    else:
        directional_data = {
            "title": request.form.get("directional_title", ""),
            "description": request.form.get("directional_description", ""),
            "type": request.form.get("directional_type", ""),
            "priority": request.form.get("directional_priority", ""),
            "status": request.form.get("status", ""),
            "owner": request.form.get("owner", ""),
            "notes": request.form.get("notes", ""),
        }

    if db.update_directional_record(int(directional_id), directional_data):
        if request.is_json:
            return jsonify({"success": True})
        else:
            flash("Direcionador atualizado com sucesso!", "success")
            return redirect(url_for("plan_drivers", plan_id=plan_id))
    else:
        if request.is_json:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar direcionador"}),
                500,
            )
        else:
            flash("Erro ao atualizar direcionador!", "error")
            return redirect(url_for("plan_drivers", plan_id=plan_id))


@app.route("/plans/<plan_id>/directional-records/<directional_id>", methods=["DELETE"])
def delete_directional_record(plan_id: str, directional_id: str):
    """Delete directional record"""
    if db.delete_directional_record(int(directional_id)):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Erro ao excluir direcionador"}), 500


@app.route("/plans/<plan_id>/directional-records/<directional_id>", methods=["GET"])
def get_directional_record(plan_id: str, directional_id: str):
    """Get directional record data for editing"""
    directional_record = db.get_directional_record(int(directional_id))
    if directional_record:
        return jsonify({"success": True, "directional_record": directional_record})
    else:
        return jsonify({"success": False, "error": "Direcionador não encontrado"}), 404


# ============================================================================
# OKR Routes - Global and Area OKRs
# ============================================================================


# OKR Global Routes
@app.route("/plans/<plan_id>/okr-global/workshop", methods=["POST"])
def add_workshop_okr_record(plan_id: str):
    """Add new OKR record in workshop stage"""
    try:
        participant_lookup_full = _build_participant_lookup(int(plan_id))
        plan_row = db.get_plan(int(plan_id))
        company_id = plan_row.get("company_id") if plan_row else None
        indicator_lookup_full = (
            _build_indicator_lookup(company_id) if company_id else {}
        )

        owner_id_raw = (request.form.get("okr_owner_id") or "").strip()
        owner_name = (request.form.get("okr_owner") or "").strip()
        owner_id = int(owner_id_raw) if owner_id_raw.isdigit() else None
        if owner_id is not None and not owner_name:
            participant_data = participant_lookup_full.get(str(owner_id)) or {}
            owner_name = (participant_data.get("name") or "").strip()

        # Extract OKR data
        okr_data = {
            "objective": request.form.get("okr_objective", ""),
            "okr_type": request.form.get("okr_type", ""),
            "type_display": request.form.get("okr_type", "").title()
            if request.form.get("okr_type")
            else "",
            "owner_id": owner_id,
            "owner": request.form.get("okr_owner", ""),
            "deadline": request.form.get("okr_deadline"),
            "observations": request.form.get("okr_observations", ""),
            "directional": request.form.get("okr_directional", ""),
        }
        okr_data["owner"] = owner_name or okr_data["owner"]

        # Extract key results
        key_results = _extract_key_results_from_form(request.form)
        for kr in key_results:
            owner_id_val = kr.get("owner_id")
            if owner_id_val is not None:
                participant_data = participant_lookup_full.get(str(owner_id_val)) or {}
                if not kr.get("owner"):
                    kr["owner"] = (participant_data.get("name") or "").strip()
            indicator_id_val = kr.get("indicator_id")
            if indicator_id_val is not None:
                indicator_data = indicator_lookup_full.get(str(indicator_id_val)) or {}
                if indicator_data and not kr.get("indicator_label"):
                    kr["indicator_label"] = (
                        indicator_data.get("label") or indicator_data.get("name") or ""
                    )

        # Save to database
        okr_id = db.add_global_okr_record(
            int(plan_id), "workshop", okr_data, key_results
        )

        if okr_id:
            flash("OKR Global (Workshop) salvo com sucesso!", "success")
        else:
            flash("Erro ao salvar OKR Global.", "error")

    except Exception as e:
        logger.info(f"Error adding workshop OKR: {e}")
        flash("Erro ao salvar OKR Global.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/approval", methods=["POST"])
def add_okr_approval_record(plan_id: str):
    """Add new OKR record in approval stage"""
    try:
        participant_lookup_full = _build_participant_lookup(int(plan_id))
        plan_row = db.get_plan(int(plan_id))
        company_id = plan_row.get("company_id") if plan_row else None
        indicator_lookup_full = (
            _build_indicator_lookup(company_id) if company_id else {}
        )

        owner_id_raw = (request.form.get("okr_owner_id") or "").strip()
        owner_name = (request.form.get("okr_owner") or "").strip()
        owner_id = int(owner_id_raw) if owner_id_raw.isdigit() else None
        if owner_id is not None and not owner_name:
            participant_data = participant_lookup_full.get(str(owner_id)) or {}
            owner_name = (participant_data.get("name") or "").strip()

        # Extract OKR data
        okr_data = {
            "objective": request.form.get("okr_objective", ""),
            "okr_type": request.form.get("okr_type", ""),
            "type_display": request.form.get("okr_type", "").title()
            if request.form.get("okr_type")
            else "",
            "owner_id": owner_id,
            "owner": request.form.get("okr_owner", ""),
            "deadline": request.form.get("okr_deadline"),
            "observations": request.form.get("okr_observations", ""),
            "directional": request.form.get("okr_directional", ""),
        }
        okr_data["owner"] = owner_name or okr_data["owner"]

        # Extract key results
        key_results = _extract_key_results_from_form(request.form)
        for kr in key_results:
            owner_id_val = kr.get("owner_id")
            if owner_id_val is not None:
                participant_data = participant_lookup_full.get(str(owner_id_val)) or {}
                if not kr.get("owner"):
                    kr["owner"] = (participant_data.get("name") or "").strip()
            indicator_id_val = kr.get("indicator_id")
            if indicator_id_val is not None:
                indicator_data = indicator_lookup_full.get(str(indicator_id_val)) or {}
                if indicator_data and not kr.get("indicator_label"):
                    kr["indicator_label"] = (
                        indicator_data.get("label") or indicator_data.get("name") or ""
                    )

        # Save to database
        okr_id = db.add_global_okr_record(
            int(plan_id), "approval", okr_data, key_results
        )

        if okr_id:
            flash("OKR Global (Aprovação) salvo com sucesso!", "success")
        else:
            flash("Erro ao salvar OKR Global.", "error")

    except Exception as e:
        logger.info(f"Error adding approval OKR: {e}")
        flash("Erro ao salvar OKR Global.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


# OKR Global Preliminary Routes
@app.route("/plans/<plan_id>/okr-global/preliminary", methods=["POST"])
def add_preliminary_okr_record(plan_id: str):
    """Add preliminary OKR analysis"""
    try:
        analysis = request.form.get("okr_analysis", "")

        if not analysis:
            flash("Análise é obrigatória.", "error")
            return redirect(url_for("plan_okr_global", plan_id=plan_id))

        record_id = db.add_okr_preliminary_record(int(plan_id), analysis)

        if record_id:
            flash("Análise preliminar salva com sucesso!", "success")
        else:
            flash("Erro ao salvar análise preliminar.", "error")

    except Exception as e:
        logger.info(f"Error adding preliminary OKR: {e}")
        flash("Erro ao salvar análise preliminar.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/preliminary/<record_id>", methods=["GET"])
def get_preliminary_okr_data(plan_id: str, record_id: str):
    """Get preliminary OKR record data for editing"""
    try:
        record = db.get_okr_preliminary_record(int(record_id))
        if record:
            return jsonify({"success": True, "data": record})
        else:
            return (
                jsonify({"success": False, "message": "Registro não encontrado"}),
                404,
            )
    except Exception as e:
        logger.info(f"Error getting preliminary OKR: {e}")
        return jsonify({"success": False, "message": "Erro ao buscar registro"}), 500


@app.route("/plans/<plan_id>/okr-global/preliminary/<record_id>", methods=["POST"])
def edit_preliminary_okr_record(plan_id: str, record_id: str):
    """Edit preliminary OKR analysis"""
    try:
        analysis = request.form.get("okr_analysis", "")

        if not analysis:
            flash("Análise é obrigatória.", "error")
            return redirect(url_for("plan_okr_global", plan_id=plan_id))

        success = db.update_okr_preliminary_record(int(record_id), analysis)

        if success:
            flash("Análise preliminar atualizada com sucesso!", "success")
        else:
            flash("Erro ao atualizar análise preliminar.", "error")

    except Exception as e:
        logger.info(f"Error updating preliminary OKR: {e}")
        flash("Erro ao atualizar análise preliminar.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route(
    "/plans/<plan_id>/okr-global/preliminary/<record_id>/delete", methods=["POST"]
)
def delete_preliminary_okr_record(plan_id: str, record_id: str):
    """Delete preliminary OKR analysis"""
    try:
        success = db.delete_okr_preliminary_record(int(record_id))

        if success:
            flash("Análise preliminar excluída com sucesso!", "success")
        else:
            flash("Erro ao excluir análise preliminar.", "error")

    except Exception as e:
        logger.info(f"Error deleting preliminary OKR: {e}")
        flash("Erro ao excluir análise preliminar.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/workshop-discussions", methods=["POST"])
def save_workshop_discussions(plan_id: str):
    """Save workshop discussions for OKR Global"""
    try:
        discussions = request.form.get("workshop_discussions", "")

        success = db.save_workshop_discussions(int(plan_id), "preliminary", discussions)

        if success:
            flash("Discussões salvas com sucesso!", "success")
        else:
            flash("Erro ao salvar discussões.", "error")

    except Exception as e:
        logger.info(f"Error saving workshop discussions: {e}")
        flash("Erro ao salvar discussões.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/workshop-discussions/delete", methods=["POST"])
def delete_workshop_discussions(plan_id: str):
    """Delete workshop discussions for OKR Global"""
    try:
        success = db.delete_workshop_discussions(int(plan_id), "preliminary")

        if success:
            flash("Discussões excluídas com sucesso!", "success")
        else:
            flash("Erro ao excluir discussões.", "error")

    except Exception as e:
        logger.info(f"Error deleting workshop discussions: {e}")
        flash("Erro ao excluir discussões.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/approval-discussions", methods=["POST"])
def save_approval_discussions(plan_id: str):
    """Save approval discussions for OKR Global"""
    try:
        discussions = request.form.get("approval_discussions", "")

        success = db.save_workshop_discussions(int(plan_id), "final", discussions)

        if success:
            flash("Discussões salvas com sucesso!", "success")
        else:
            flash("Erro ao salvar discussões.", "error")

    except Exception as e:
        logger.info(f"Error saving approval discussions: {e}")
        flash("Erro ao salvar discussões.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/approval-discussions/delete", methods=["POST"])
def delete_approval_discussions(plan_id: str):
    """Delete approval discussions for OKR Global"""
    try:
        success = db.delete_workshop_discussions(int(plan_id), "final")

        if success:
            flash("Discussões excluídas com sucesso!", "success")
        else:
            flash("Erro ao excluir discussões.", "error")

    except Exception as e:
        logger.info(f"Error deleting approval discussions: {e}")
        flash("Erro ao excluir discussões.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/workshop/<record_id>", methods=["POST"])
def edit_workshop_okr_record(plan_id: str, record_id: str):
    """Edit workshop OKR record"""
    try:
        participant_lookup_full = _build_participant_lookup(int(plan_id))
        plan_row = db.get_plan(int(plan_id))
        company_id = plan_row.get("company_id") if plan_row else None
        indicator_lookup_full = (
            _build_indicator_lookup(company_id) if company_id else {}
        )

        owner_id_raw = (request.form.get("okr_owner_id") or "").strip()
        owner_name = (request.form.get("okr_owner") or "").strip()
        owner_id = int(owner_id_raw) if owner_id_raw.isdigit() else None
        if owner_id is not None and not owner_name:
            participant_data = participant_lookup_full.get(str(owner_id)) or {}
            owner_name = (participant_data.get("name") or "").strip()

        # Extract OKR data
        okr_data = {
            "objective": request.form.get("okr_objective", ""),
            "okr_type": request.form.get("okr_type", ""),
            "type_display": request.form.get("okr_type", "").title()
            if request.form.get("okr_type")
            else "",
            "owner_id": owner_id,
            "owner": request.form.get("okr_owner", ""),
            "deadline": request.form.get("okr_deadline"),
            "observations": request.form.get("okr_observations", ""),
            "directional": request.form.get("okr_directional", ""),
        }
        okr_data["owner"] = owner_name or okr_data["owner"]

        # Extract key results
        key_results = _extract_key_results_from_form(request.form)
        for kr in key_results:
            owner_id_val = kr.get("owner_id")
            if owner_id_val is not None:
                participant_data = participant_lookup_full.get(str(owner_id_val)) or {}
                if not kr.get("owner"):
                    kr["owner"] = (participant_data.get("name") or "").strip()
            indicator_id_val = kr.get("indicator_id")
            if indicator_id_val is not None:
                indicator_data = indicator_lookup_full.get(str(indicator_id_val)) or {}
                if indicator_data and not kr.get("indicator_label"):
                    kr["indicator_label"] = (
                        indicator_data.get("label") or indicator_data.get("name") or ""
                    )

        # Update in database
        success = db.update_global_okr_record(int(record_id), okr_data, key_results)

        if success:
            flash("OKR Global (Workshop) atualizado com sucesso!", "success")
        else:
            flash("Erro ao atualizar OKR Global.", "error")

    except Exception as e:
        logger.info(f"Error updating workshop OKR: {e}")
        flash("Erro ao atualizar OKR Global.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/approval/<record_id>", methods=["POST"])
def edit_approval_okr_record(plan_id: str, record_id: str):
    """Edit approval OKR record"""
    try:
        participant_lookup_full = _build_participant_lookup(int(plan_id))
        plan_row = db.get_plan(int(plan_id))
        company_id = plan_row.get("company_id") if plan_row else None
        indicator_lookup_full = (
            _build_indicator_lookup(company_id) if company_id else {}
        )

        owner_id_raw = (request.form.get("okr_owner_id") or "").strip()
        owner_name = (request.form.get("okr_owner") or "").strip()
        owner_id = int(owner_id_raw) if owner_id_raw.isdigit() else None
        if owner_id is not None and not owner_name:
            participant_data = participant_lookup_full.get(str(owner_id)) or {}
            owner_name = (participant_data.get("name") or "").strip()

        # Extract OKR data
        okr_data = {
            "objective": request.form.get("okr_objective", ""),
            "okr_type": request.form.get("okr_type", ""),
            "type_display": request.form.get("okr_type", "").title()
            if request.form.get("okr_type")
            else "",
            "owner_id": owner_id,
            "owner": request.form.get("okr_owner", ""),
            "deadline": request.form.get("okr_deadline"),
            "observations": request.form.get("okr_observations", ""),
            "directional": request.form.get("okr_directional", ""),
        }
        okr_data["owner"] = owner_name or okr_data["owner"]

        # Extract key results
        key_results = _extract_key_results_from_form(request.form)
        for kr in key_results:
            owner_id_val = kr.get("owner_id")
            if owner_id_val is not None:
                participant_data = participant_lookup_full.get(str(owner_id_val)) or {}
                if not kr.get("owner"):
                    kr["owner"] = (participant_data.get("name") or "").strip()
            indicator_id_val = kr.get("indicator_id")
            if indicator_id_val is not None:
                indicator_data = indicator_lookup_full.get(str(indicator_id_val)) or {}
                if indicator_data and not kr.get("indicator_label"):
                    kr["indicator_label"] = (
                        indicator_data.get("label") or indicator_data.get("name") or ""
                    )

        # Update in database
        success = db.update_global_okr_record(int(record_id), okr_data, key_results)

        if success:
            flash("OKR Global (Aprovação) atualizado com sucesso!", "success")
        else:
            flash("Erro ao atualizar OKR Global.", "error")

    except Exception as e:
        logger.info(f"Error updating approval OKR: {e}")
        flash("Erro ao atualizar OKR Global.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/workshop/<record_id>/delete", methods=["POST"])
def delete_workshop_okr_record(plan_id: str, record_id: str):
    """Delete workshop OKR record"""
    try:
        success = db.delete_global_okr_record(int(record_id))

        if success:
            flash("OKR Global (Workshop) excluído com sucesso!", "success")
        else:
            flash("Erro ao excluir OKR Global.", "error")

    except Exception as e:
        logger.info(f"Error deleting workshop OKR: {e}")
        flash("Erro ao excluir OKR Global.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/approval/<record_id>/delete", methods=["POST"])
def delete_approval_okr_record(plan_id: str, record_id: str):
    """Delete approval OKR record"""
    try:
        success = db.delete_global_okr_record(int(record_id))

        if success:
            flash("OKR Global (Aprovação) excluído com sucesso!", "success")
        else:
            flash("Erro ao excluir OKR Global.", "error")

    except Exception as e:
        logger.info(f"Error deleting approval OKR: {e}")
        flash("Erro ao excluir OKR Global.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/duplicate/<type>/<record_id>", methods=["POST"])
def duplicate_okr_record(plan_id: str, type: str, record_id: str):
    """Duplicate OKR record from one stage to another"""
    try:
        # Get the original record
        original = db.get_global_okr_record(int(record_id))

        if not original:
            flash("OKR original não encontrado.", "error")
            return redirect(url_for("plan_okr_global", plan_id=plan_id))

        # Determine target stage
        if type == "workshop":
            target_stage = "approval"
            stage_name = "Aprovação"
        elif type == "approval":
            target_stage = "workshop"
            stage_name = "Workshop"
        else:
            flash("Tipo de OKR inválido.", "error")
            return redirect(url_for("plan_okr_global", plan_id=plan_id))

        # Prepare OKR data
        okr_data = {
            "objective": original.get("objective", ""),
            "okr_type": original.get("okr_type", ""),
            "type_display": original.get("type_display", ""),
            "owner_id": original.get("owner_id"),
            "owner": original.get("owner", ""),
            "deadline": original.get("deadline"),
            "observations": original.get("observations", ""),
            "directional": original.get("directional", ""),
        }

        # Copy key results
        key_results = []
        for position, kr in enumerate(original.get("key_results", [])):
            key_results.append(
                {
                    "label": kr.get("label", ""),
                    "target": kr.get("target"),
                    "deadline": kr.get("deadline"),
                    "owner_id": kr.get("owner_id"),
                    "owner": kr.get("owner"),
                    "indicator_id": kr.get("indicator_id"),
                    "indicator_label": kr.get("indicator_label"),
                    "position": position,
                }
            )

        # Create duplicate in target stage
        okr_id = db.add_global_okr_record(
            int(plan_id), target_stage, okr_data, key_results
        )

        if okr_id:
            flash(f"OKR duplicado para {stage_name} com sucesso!", "success")
        else:
            flash("Erro ao duplicar OKR.", "error")

    except Exception as e:
        logger.info(f"Error duplicating OKR: {e}")
        import traceback

        traceback.print_exc()
        flash("Erro ao duplicar OKR.", "error")

    return redirect(url_for("plan_okr_global", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-global/preliminary-analysis/status", methods=["POST"])
def update_okr_preliminary_analysis_section_status(plan_id: str):
    """Update OKR preliminary analysis section status"""
    try:
        data = request.get_json()
        status = data.get("status", "closed")

        success = db.update_section_status(
            int(plan_id), "preliminary-analysis-okr", status, None
        )

        if success:
            return jsonify({"success": True, "message": "Status atualizado"})
        else:
            return (
                jsonify({"success": False, "message": "Erro ao atualizar status"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating preliminary analysis status: {e}")
        return jsonify({"success": False, "message": "Erro ao atualizar status"}), 500


@app.route("/plans/<plan_id>/okr-global/workshop-final/status", methods=["POST"])
def update_okr_workshop_final_section_status(plan_id: str):
    """Update OKR workshop final section status"""
    try:
        data = request.get_json()
        status = data.get("status", "closed")

        success = db.update_section_status(
            int(plan_id), "workshop-final-okr", status, None
        )

        if success:
            return jsonify({"success": True, "message": "Status atualizado"})
        else:
            return (
                jsonify({"success": False, "message": "Erro ao atualizar status"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating workshop final status: {e}")
        return jsonify({"success": False, "message": "Erro ao atualizar status"}), 500


@app.route("/plans/<plan_id>/okr-global/approvals/status", methods=["POST"])
def update_okr_approvals_section_status(plan_id: str):
    """Update OKR approvals section status"""
    try:
        data = request.get_json()
        status = data.get("status", "closed")

        success = db.update_section_status(int(plan_id), "okr-approvals", status, None)

        if success:
            return jsonify({"success": True, "message": "Status atualizado"})
        else:
            return (
                jsonify({"success": False, "message": "Erro ao atualizar status"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating approvals status: {e}")
        return jsonify({"success": False, "message": "Erro ao atualizar status"}), 500


@app.route("/plans/<plan_id>/okr-global/ai-suggestions", methods=["POST"])
def generate_ai_okr_suggestions(plan_id: str):
    """Generate AI suggestions for OKRs"""
    try:
        # This would be where AI suggestions are generated
        # For now, just return a placeholder response
        return jsonify(
            {
                "success": True,
                "message": "Sugestões de IA ainda não implementadas",
                "suggestions": [],
            }
        )

    except Exception as e:
        logger.info(f"Error generating AI suggestions: {e}")
        return jsonify({"success": False, "message": "Erro ao gerar sugestões"}), 500


# OKR Area Routes
@app.route("/plans/<plan_id>/okr-area/preliminary", methods=["POST"])
def add_preliminary_area_okr_record(plan_id: str):
    """Add preliminary area OKR analysis"""
    try:
        analysis = request.form.get("okr_analysis", "")

        if not analysis:
            flash("Análise é obrigatória.", "error")
            return redirect(url_for("plan_okr_area", plan_id=plan_id))

        record_id = db.add_okr_area_preliminary_record(int(plan_id), analysis)

        if record_id:
            flash("Análise preliminar salva com sucesso!", "success")
        else:
            flash("Erro ao salvar análise preliminar.", "error")

    except Exception as e:
        logger.info(f"Error adding preliminary area OKR: {e}")
        flash("Erro ao salvar análise preliminar.", "error")

    return redirect(url_for("plan_okr_area", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-area/workshop", methods=["POST"])
def add_area_okr_record(plan_id: str):
    """Add area OKR in workshop stage"""
    try:
        from datetime import datetime
        import json

        participant_lookup_full = _build_participant_lookup(int(plan_id))
        plan_row = db.get_plan(int(plan_id))
        company_id = plan_row.get("company_id") if plan_row else None
        indicator_lookup_full = (
            _build_indicator_lookup(company_id) if company_id else {}
        )

        owner_id_raw = (request.form.get("okr_owner_id") or "").strip()
        owner_id = owner_id_raw if owner_id_raw else ""
        owner_name = (request.form.get("okr_owner") or "").strip()
        if owner_id and not owner_name:
            participant_data = participant_lookup_full.get(owner_id) or {}
            owner_name = (participant_data.get("name") or "").strip()

        # Get existing workshop data
        workshop_status = db.get_section_status(int(plan_id), "area-okr-workshop")
        existing_okrs = []

        if workshop_status and workshop_status.get("notes"):
            try:
                workshop_data = json.loads(workshop_status["notes"])
                if isinstance(workshop_data, dict) and "okrs" in workshop_data:
                    existing_okrs = workshop_data["okrs"]
            except Exception as exc:
                pass

        # Create new OKR
        new_okr = {
            "id": len(existing_okrs) + 1,
            "global_ref": request.form.get("okr_global_ref", ""),
            "area": request.form.get("okr_area", ""),
            "objective": request.form.get("okr_objective", ""),
            "type": request.form.get("okr_type", ""),
            "type_display": request.form.get("okr_type", "").title()
            if request.form.get("okr_type")
            else "",
            "owner_id": owner_id,
            "owner": owner_name,
            "deadline": request.form.get("okr_deadline", ""),
            "observations": request.form.get("okr_observations", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "key_results": [],
        }

        # Extract key results
        key_results_payload = _extract_key_results_from_form(request.form)
        for kr in key_results_payload:
            kr_owner_id_val = kr.get("owner_id")
            kr_owner_id = str(kr_owner_id_val) if kr_owner_id_val is not None else ""
            participant_data = participant_lookup_full.get(kr_owner_id) or {}
            kr_owner_name = (
                kr.get("owner") or (participant_data.get("name") or "").strip()
            )
            indicator_id_val = kr.get("indicator_id")
            indicator_id = str(indicator_id_val) if indicator_id_val is not None else ""
            indicator_data = indicator_lookup_full.get(indicator_id) or {}
            indicator_label = (
                kr.get("indicator_label")
                or indicator_data.get("label")
                or indicator_data.get("name")
                or ""
            )

            new_okr["key_results"].append(
                {
                    "label": kr.get("label", ""),
                    "target": kr.get("target", ""),
                    "deadline": kr.get("deadline", ""),
                    "owner_id": kr_owner_id,
                    "owner": kr_owner_name,
                    "indicator_id": indicator_id,
                    "indicator_label": indicator_label,
                    "position": len(new_okr["key_results"]),
                }
            )

        # Add to existing OKRs
        existing_okrs.append(new_okr)

        # 1. Salvar na tabela okr_area_records (novo sistema)
        try:
            from database.postgres_helper import connect as pg_connect

            conn = pg_connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO okr_area_records 
                (plan_id, stage, objective, okr_type, type_display, department, 
                 owner_id, owner, deadline, observations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    plan_id,
                    "workshop",
                    new_okr["objective"],
                    new_okr["type"],
                    new_okr["type_display"],
                    new_okr["area"],
                    new_okr["owner_id"] if new_okr["owner_id"] else None,
                    new_okr["owner"],
                    new_okr["deadline"],
                    new_okr["observations"],
                ),
            )

            conn.commit()
            conn.close()
            logger.info(f"OKR salvo na tabela okr_area_records com sucesso!")
        except Exception as e:
            logger.info(f"Erro ao salvar na tabela okr_area_records: {e}")

        # 2. Salvar no sistema antigo (JSON) para compatibilidade
        workshop_data = {"okrs": existing_okrs}

        if db.update_section_status(
            int(plan_id), "area-okr-workshop", "open", json.dumps(workshop_data)
        ):
            flash("OKR de Área salvo com sucesso!", "success")
        else:
            flash("Erro ao salvar OKR de Área.", "error")

    except Exception as e:
        logger.info(f"Error adding area OKR: {e}")
        import traceback

        traceback.print_exc()
        flash("Erro ao salvar OKR de Área.", "error")

    return redirect(url_for("plan_okr_area", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-area/final", methods=["POST"])
def add_final_area_okr_record(plan_id: str):
    """Add final area OKR"""
    try:
        from datetime import datetime
        import json

        participant_lookup_full = _build_participant_lookup(int(plan_id))
        plan_row = db.get_plan(int(plan_id))
        company_id = plan_row.get("company_id") if plan_row else None
        indicator_lookup_full = (
            _build_indicator_lookup(company_id) if company_id else {}
        )

        owner_id_raw = (request.form.get("okr_owner_id") or "").strip()
        owner_id = owner_id_raw if owner_id_raw else ""
        owner_name = (request.form.get("okr_owner") or "").strip()
        if owner_id and not owner_name:
            participant_data = participant_lookup_full.get(owner_id) or {}
            owner_name = (participant_data.get("name") or "").strip()

        # Get existing final data
        final_status = db.get_section_status(int(plan_id), "final-area-okr")
        existing_okrs = []

        if final_status and final_status.get("notes"):
            try:
                final_data = json.loads(final_status["notes"])
                if isinstance(final_data, dict) and "okrs" in final_data:
                    existing_okrs = final_data["okrs"]
            except Exception as exc:
                pass

        # Create new OKR
        new_okr = {
            "id": len(existing_okrs) + 1,
            "global_ref": request.form.get("okr_global_ref", ""),
            "area": request.form.get("okr_area", ""),
            "objective": request.form.get("okr_objective", ""),
            "type": request.form.get("okr_type", ""),
            "type_display": request.form.get("okr_type", "").title()
            if request.form.get("okr_type")
            else "",
            "owner_id": owner_id,
            "owner": owner_name,
            "deadline": request.form.get("okr_deadline", ""),
            "observations": request.form.get("okr_observations", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "key_results": [],
        }

        # Extract key results
        key_results_payload = _extract_key_results_from_form(request.form)
        for kr in key_results_payload:
            kr_owner_id_val = kr.get("owner_id")
            kr_owner_id = str(kr_owner_id_val) if kr_owner_id_val is not None else ""
            participant_data = participant_lookup_full.get(kr_owner_id) or {}
            kr_owner_name = (
                kr.get("owner") or (participant_data.get("name") or "").strip()
            )
            indicator_id_val = kr.get("indicator_id")
            indicator_id = str(indicator_id_val) if indicator_id_val is not None else ""
            indicator_data = indicator_lookup_full.get(indicator_id) or {}
            indicator_label = (
                kr.get("indicator_label")
                or indicator_data.get("label")
                or indicator_data.get("name")
                or ""
            )

            new_okr["key_results"].append(
                {
                    "label": kr.get("label", ""),
                    "target": kr.get("target", ""),
                    "deadline": kr.get("deadline", ""),
                    "owner_id": kr_owner_id,
                    "owner": kr_owner_name,
                    "indicator_id": indicator_id,
                    "indicator_label": indicator_label,
                    "position": len(new_okr["key_results"]),
                }
            )

        # Add to existing OKRs
        existing_okrs.append(new_okr)

        # 1. Salvar na tabela okr_area_records (novo sistema)
        try:
            from database.postgres_helper import connect as pg_connect

            conn = pg_connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO okr_area_records 
                (plan_id, stage, objective, okr_type, type_display, department, 
                 owner_id, owner, deadline, observations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    plan_id,
                    "approval",
                    new_okr["objective"],
                    new_okr["type"],
                    new_okr["type_display"],
                    new_okr["area"],
                    new_okr["owner_id"] if new_okr["owner_id"] else None,
                    new_okr["owner"],
                    new_okr["deadline"],
                    new_okr["observations"],
                ),
            )

            conn.commit()
            conn.close()
            logger.info(f"OKR Final salvo na tabela okr_area_records com sucesso!")
        except Exception as e:
            logger.info(f"Erro ao salvar OKR Final na tabela okr_area_records: {e}")

        # 2. Salvar no sistema antigo (JSON) para compatibilidade
        final_data = {"okrs": existing_okrs}

        if db.update_section_status(
            int(plan_id), "final-area-okr", "open", json.dumps(final_data)
        ):
            flash("OKR de Área Final salvo com sucesso!", "success")
        else:
            flash("Erro ao salvar OKR de Área Final.", "error")

    except Exception as e:
        logger.info(f"Error adding final area OKR: {e}")
        import traceback

        traceback.print_exc()
        flash("Erro ao salvar OKR de Área Final.", "error")

    return redirect(url_for("plan_okr_area", plan_id=plan_id))


# OKR Area Discussions Routes
@app.route("/plans/<plan_id>/okr-area/workshop-discussions", methods=["POST"])
def save_area_workshop_discussions(plan_id: str):
    """Save area workshop discussions"""
    try:
        discussions = request.form.get("workshop_discussions", "")

        if db.save_workshop_discussions(int(plan_id), "area-preliminary", discussions):
            flash("Discussões salvas com sucesso!", "success")
        else:
            flash("Erro ao salvar discussões.", "error")

    except Exception as e:
        logger.info(f"Error saving area workshop discussions: {e}")
        flash("Erro ao salvar discussões.", "error")

    return redirect(url_for("plan_okr_area", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-area/final-discussions", methods=["POST"])
def save_final_area_discussions(plan_id: str):
    """Save final area discussions"""
    try:
        discussions = request.form.get("approval_discussions", "")

        if db.save_workshop_discussions(int(plan_id), "area-final", discussions):
            flash("Discussões finais salvas com sucesso!", "success")
        else:
            flash("Erro ao salvar discussões finais.", "error")

    except Exception as e:
        logger.info(f"Error saving final area discussions: {e}")
        flash("Erro ao salvar discussões finais.", "error")

    return redirect(url_for("plan_okr_area", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-area/workshop-discussions/delete", methods=["POST"])
def delete_area_workshop_discussions(plan_id: str):
    """Delete area workshop discussions"""
    try:
        if db.save_workshop_discussions(int(plan_id), "area-preliminary", ""):
            flash("Discussões excluídas com sucesso!", "success")
        else:
            flash("Erro ao excluir discussões.", "error")

    except Exception as e:
        logger.info(f"Error deleting area workshop discussions: {e}")
        flash("Erro ao excluir discussões.", "error")

    return redirect(url_for("plan_okr_area", plan_id=plan_id))


@app.route("/plans/<plan_id>/okr-area/final-discussions/delete", methods=["POST"])
def delete_final_area_discussions(plan_id: str):
    """Delete final area discussions"""
    try:
        if db.save_workshop_discussions(int(plan_id), "area-final", ""):
            flash("Discussões finais excluídas com sucesso!", "success")
        else:
            flash("Erro ao excluir discussões finais.", "error")

    except Exception as e:
        logger.info(f"Error deleting final area discussions: {e}")
        flash("Erro ao excluir discussões finais.", "error")

    return redirect(url_for("plan_okr_area", plan_id=plan_id))


# OKR Area Section Status Routes
@app.route("/plans/<plan_id>/okr-area/preliminary-analysis/status", methods=["POST"])
def update_area_preliminary_analysis_section_status(plan_id: str):
    """Update preliminary analysis section status"""
    try:
        data = request.get_json()
        status = data.get("status", "open")
        notes = data.get("conclusion_reason", "")

        if db.update_section_status(
            int(plan_id), "preliminary-analysis-area-okr", status, notes
        ):
            return jsonify({"success": True})
        else:
            return (
                jsonify({"success": False, "message": "Erro ao atualizar status"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating preliminary analysis section status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/plans/<plan_id>/okr-area/workshop/status", methods=["POST"])
def update_workshop_area_section_status(plan_id: str):
    """Update workshop area section status"""
    try:
        data = request.get_json()
        status = data.get("status", "open")
        notes = data.get("conclusion_reason", "")

        if db.update_section_status(int(plan_id), "area-okr-workshop", status, notes):
            return jsonify({"success": True})
        else:
            return (
                jsonify({"success": False, "message": "Erro ao atualizar status"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating workshop area section status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/plans/<plan_id>/okr-area/final/status", methods=["POST"])
def update_final_area_section_status(plan_id: str):
    """Update final area section status"""
    try:
        data = request.get_json()
        status = data.get("status", "open")
        notes = data.get("conclusion_reason", "")

        if db.update_section_status(int(plan_id), "final-area-okr", status, notes):
            return jsonify({"success": True})
        else:
            return (
                jsonify({"success": False, "message": "Erro ao atualizar status"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating final area section status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# OKR Area AI Routes
@app.route("/plans/<plan_id>/okr-area/ai-suggestions", methods=["POST"])
def generate_ai_area_okr_suggestions(plan_id: str):
    """Generate AI suggestions for area OKRs"""
    try:
        # This is a placeholder - implement AI generation logic here
        suggestions = "Sugestões de IA para OKRs de Área não estão configuradas ainda. Configure sua chave OpenAI para usar esta funcionalidade."

        return jsonify({"success": True, "suggestions": suggestions})

    except Exception as e:
        logger.info(f"Error generating AI suggestions: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# API Routes for AI Agents Management
@app.route("/api/agents", methods=["GET"])
def get_agents():
    """Get all AI agents"""
    try:
        agents = db.get_ai_agents()

        def _normalize(a):
            agent = dict(a) if isinstance(a, dict) else {}
            # Build activation block
            activation = (
                agent.get("activation")
                if isinstance(agent.get("activation"), dict)
                else {
                    "page": agent.get("page"),
                    "page_label": None,
                    "section": agent.get("section"),
                    "section_label": None,
                    "button_text": agent.get("button_text", ""),
                }
            )

            # Labels
            def _label_page(value):
                labels = {
                    "company": "Dados da Organização",
                    "participants": "Participantes",
                    "drivers": "Direcionadores",
                    "okr-global": "OKRs Globais",
                    "okr-area": "OKRs de Área",
                    "projects": "Projetos",
                    "reports": "Relatórios",
                }
                return labels.get(value, value)

            def _label_section(value):
                labels = {
                    "analyses": "Análises",
                    "summary": "Resumo Executivo",
                    "interviews": "Entrevistas",
                    "vision": "Visão",
                    "market": "Mercado",
                    "company": "Empresa",
                }
                return labels.get(value, value)

            activation["page_label"] = (
                _label_page(activation.get("page")) if activation.get("page") else ""
            )
            activation["section_label"] = (
                _label_section(activation.get("section"))
                if activation.get("section")
                else ""
            )

            # Input data
            input_data = (
                agent.get("input_data")
                if isinstance(agent.get("input_data"), dict)
                else {
                    "required": json.loads(agent.get("required_data", "[]"))
                    if isinstance(agent.get("required_data"), str)
                    else (agent.get("required_data") or []),
                    "optional": json.loads(agent.get("optional_data", "[]"))
                    if isinstance(agent.get("optional_data"), str)
                    else (agent.get("optional_data") or []),
                }
            )
            # Response format
            response_format = (
                agent.get("response_format")
                if isinstance(agent.get("response_format"), dict)
                else {
                    "type": agent.get("format_type", "markdown"),
                    "output_field": agent.get("output_field", "ai_insights"),
                    "template": agent.get("response_template", ""),
                }
            )
            # Advanced
            advanced_settings = (
                agent.get("advanced_settings")
                if isinstance(agent.get("advanced_settings"), dict)
                else {
                    "timeout": agent.get("timeout", 300),
                    "max_retries": agent.get("max_retries", 3),
                    "execution_mode": agent.get("execution_mode", "sequential"),
                    "cache_enabled": bool(agent.get("cache_enabled", True)),
                }
            )
            # Timestamps
            created_at = agent.get("created_at")
            updated_at = agent.get("updated_at")
            return {
                "id": agent.get("id"),
                "name": agent.get("name"),
                "description": agent.get("description"),
                "version": agent.get("version", "1.0"),
                "status": agent.get("status", "active"),
                "activation": activation,
                "input_data": input_data,
                "prompt_template": agent.get("prompt_template", ""),
                "response_format": response_format,
                "advanced_settings": advanced_settings,
                "created_at": created_at,
                "updated_at": updated_at,
            }

        normalized = []
        for a in agents or []:
            item = _normalize(a)
            try:
                item["integrations"] = get_agent_integrations(item.get("id"))
            except Exception:
                item["integrations"] = []
            normalized.append(item)
        return jsonify({"success": True, "agents": normalized})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/available-buttons", methods=["GET"])
def api_available_buttons():
    """Return available UI buttons by page/section to link agent triggers"""
    try:
        page = (request.args.get("page") or "").strip()
        section = (request.args.get("section") or "").strip()
        # Known buttons mapping per page/section
        mapping = {
            "company": {"analyses": ["Gerar buscas e análises de IA"], "summary": []},
            "okr-global": {"preliminary-analysis": ["? Gerar Sugestões da IA"]},
            "drivers": {"directionals-ai": []},
        }
        buttons = []
        if page in mapping:
            if section and section in mapping[page]:
                buttons = mapping[page][section]
            else:
                # Aggregate all page buttons if section not provided
                for _sec, opts in mapping[page].items():
                    buttons.extend(opts)
        return jsonify({"success": True, "buttons": buttons})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents", methods=["POST"])
def create_agent():
    """Create new AI agent"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["name", "id", "page", "section", "button_text"]
        for field in required_fields:
            if not data.get(field):
                return (
                    jsonify({"success": False, "error": f"Campo obrigatório: {field}"}),
                    400,
                )

        # Flatten payload for DB
        required_list = (
            [
                s.strip()
                for s in str(data.get("required_data", "")).split(",")
                if s.strip()
            ]
            if data.get("required_data")
            else []
        )
        optional_list = (
            [
                s.strip()
                for s in str(data.get("optional_data", "")).split(",")
                if s.strip()
            ]
            if data.get("optional_data")
            else []
        )
        db_payload = {
            "id": data["id"],
            "name": data["name"],
            "description": data.get("description", ""),
            "version": data.get("version", "1.0"),
            "status": data.get("status", "active"),
            "page": data["page"],
            "section": data["section"],
            "button_text": data["button_text"],
            "required_data": json.dumps(required_list),
            "optional_data": json.dumps(optional_list),
            "prompt_template": data.get("prompt_template", ""),
            "format_type": data.get("format_type", "markdown"),
            "output_field": data.get("output_field", "ai_insights"),
            "response_template": data.get("response_template", ""),
            "timeout": int(data.get("timeout", 300)),
            "max_retries": int(data.get("max_retries", 3)),
            "execution_mode": data.get("execution_mode", "sequential"),
            "cache_enabled": data.get("cache_enabled", "true") == "true",
        }
        success = db.create_ai_agent(db_payload)
        # Link integrations if provided
        try:
            integrations = data.get("integration_ids") or []
            set_agent_integrations(data["id"], integrations)
        except Exception:
            pass

        if success:
            return jsonify({"success": True, "message": "Agente criado com sucesso"})
        else:
            return jsonify({"success": False, "error": "Erro ao criar agente"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/<agent_id>", methods=["GET"])
def get_agent(agent_id):
    """Get specific AI agent"""
    try:
        a = db.get_ai_agent(agent_id)
        if a:
            # Get linked integrations
            from database.postgresql_db import get_agent_integrations

            integrations = get_agent_integrations(agent_id)

            # Normalize as in list endpoint
            return jsonify(
                {
                    "success": True,
                    "agent": {
                        "id": a.get("id"),
                        "name": a.get("name"),
                        "description": a.get("description"),
                        "version": a.get("version", "1.0"),
                        "status": a.get("status", "active"),
                        "activation": {
                            "page": a.get("page")
                            or (a.get("activation") or {}).get("page"),
                            "page_label": "",
                            "section": a.get("section")
                            or (a.get("activation") or {}).get("section"),
                            "section_label": "",
                            "button_text": a.get("button_text")
                            or (a.get("activation") or {}).get("button_text", ""),
                        },
                        "input_data": {
                            "required": json.loads(a.get("required_data", "[]"))
                            if isinstance(a.get("required_data"), str)
                            else (a.get("required_data") or []),
                            "optional": json.loads(a.get("optional_data", "[]"))
                            if isinstance(a.get("optional_data"), str)
                            else (a.get("optional_data") or []),
                        },
                        "prompt_template": a.get("prompt_template", ""),
                        "response_format": {
                            "type": a.get("format_type", "markdown")
                            if a.get("format_type")
                            else (a.get("response_format") or {}).get(
                                "type", "markdown"
                            ),
                            "output_field": a.get("output_field", "ai_insights")
                            if a.get("output_field")
                            else (a.get("response_format") or {}).get(
                                "output_field", "ai_insights"
                            ),
                            "template": a.get("response_template", "")
                            if a.get("response_template")
                            else (a.get("response_format") or {}).get("template", ""),
                        },
                        "advanced_settings": {
                            "timeout": a.get("timeout", 300),
                            "max_retries": a.get("max_retries", 3),
                            "execution_mode": a.get("execution_mode", "sequential"),
                            "cache_enabled": bool(a.get("cache_enabled", True)),
                        },
                        "integrations": integrations,
                        "created_at": a.get("created_at"),
                        "updated_at": a.get("updated_at"),
                    },
                }
            )
        else:
            return jsonify({"success": False, "error": "Agente não encontrado"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/<agent_id>", methods=["PUT"])
def update_agent(agent_id):
    """Update AI agent"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["name", "page", "section", "button_text"]
        for field in required_fields:
            if not data.get(field):
                return (
                    jsonify({"success": False, "error": f"Campo obrigatório: {field}"}),
                    400,
                )

        # Flatten for DB
        required_list = (
            [
                s.strip()
                for s in str(data.get("required_data", "")).split(",")
                if s.strip()
            ]
            if data.get("required_data")
            else []
        )
        optional_list = (
            [
                s.strip()
                for s in str(data.get("optional_data", "")).split(",")
                if s.strip()
            ]
            if data.get("optional_data")
            else []
        )
        db_payload = {
            "name": data["name"],
            "description": data.get("description", ""),
            "version": data.get("version", "1.0"),
            "status": data.get("status", "active"),
            "page": data["page"],
            "section": data["section"],
            "button_text": data["button_text"],
            "required_data": json.dumps(required_list),
            "optional_data": json.dumps(optional_list),
            "prompt_template": data.get("prompt_template", ""),
            "format_type": data.get("format_type", "markdown"),
            "output_field": data.get("output_field", "ai_insights"),
            "response_template": data.get("response_template", ""),
            "timeout": int(data.get("timeout", 300)),
            "max_retries": int(data.get("max_retries", 3)),
            "execution_mode": data.get("execution_mode", "sequential"),
            "cache_enabled": data.get("cache_enabled", "true") == "true",
        }
        success = db.update_ai_agent(agent_id, db_payload)
        # Update links
        try:
            integrations = data.get("integration_ids") or []
            set_agent_integrations(agent_id, integrations)
        except Exception:
            pass

        if success:
            return jsonify(
                {"success": True, "message": "Agente atualizado com sucesso"}
            )
        else:
            return jsonify({"success": False, "error": "Erro ao atualizar agente"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/<agent_id>", methods=["DELETE"])
def delete_agent(agent_id):
    """Delete AI agent"""
    try:
        success = db.delete_ai_agent(agent_id)

        if success:
            return jsonify({"success": True, "message": "Agente excluído com sucesso"})
        else:
            return jsonify({"success": False, "error": "Erro ao excluir agente"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/available-fields", methods=["GET"])
def get_available_fields():
    """Return available input fields for an agent based on page/section"""
    try:
        page = request.args.get("page", "").strip()
        section = request.args.get("section", "").strip()

        # Base field catalog
        base_fields = [
            {"value": "trade_name", "label": "Nome Fantasia"},
            {"value": "legal_name", "label": "Razão Social"},
            {"value": "cnpj", "label": "CNPJ"},
            {"value": "cnaes", "label": "CNAEs"},
            {"value": "segment", "label": "Segmento"},
            {"value": "city", "label": "Cidade"},
            {"value": "state", "label": "Estado"},
            {"value": "coverage_physical", "label": "Cobertura Física"},
            {"value": "coverage_online", "label": "Cobertura Online"},
            {"value": "experience_total", "label": "Experiência Total"},
            {"value": "experience_segment", "label": "Experiência no Segmento"},
            {"value": "mission", "label": "Missão"},
            {"value": "vision", "label": "Visão"},
            {"value": "values", "label": "Valores"},
            {"value": "financials", "label": "Financeiros (linhas)"},
            {"value": "financial_total_revenue", "label": "Receita Total"},
            {"value": "financial_total_margin", "label": "Margem Média"},
            {"value": "driver_topics", "label": "Direcionadores"},
            {"value": "participants", "label": "Participantes"},
            {"value": "ai_insights", "label": "Insights de IA"},
            {"value": "consultant_analysis", "label": "Análise do Consultor"},
        ]

        # Page-specific additions/pruning
        page_map = {
            "company": base_fields,
            "participants": [
                {"value": "participants", "label": "Participantes"},
                {"value": "ai_insights", "label": "Insights de IA"},
                {"value": "consultant_analysis", "label": "Análise do Consultor"},
            ],
            "drivers": [
                {"value": "driver_topics", "label": "Direcionadores"},
                {"value": "market", "label": "Mercado (texto livre)"},
                {"value": "ai_insights", "label": "Insights de IA"},
                {"value": "consultant_analysis", "label": "Análise do Consultor"},
            ],
            "okr-global": [
                {"value": "okr_global_records", "label": "OKRs Globais"},
                {"value": "ai_insights", "label": "Insights de IA"},
                {"value": "consultant_analysis", "label": "Análise do Consultor"},
            ],
            "okr-area": [
                {"value": "okr_area_records", "label": "OKRs de Área"},
                {"value": "ai_insights", "label": "Insights de IA"},
                {"value": "consultant_analysis", "label": "Análise do Consultor"},
            ],
            "projects": [
                {"value": "projects", "label": "Projetos"},
                {"value": "ai_insights", "label": "Insights de IA"},
                {"value": "consultant_analysis", "label": "Análise do Consultor"},
            ],
            "reports": [
                {"value": "summary_report", "label": "Resumo do Relatório"},
                {"value": "ai_insights", "label": "Insights de IA"},
                {"value": "consultant_analysis", "label": "Análise do Consultor"},
            ],
        }

        fields = page_map.get(page, base_fields)

        # Optional: further narrow by section if needed
        if page == "company" and section == "vision":
            fields = [
                f
                for f in fields
                if f["value"]
                in ("mission", "vision", "values", "ai_insights", "consultant_analysis")
            ]
        elif page == "drivers" and section == "market":
            fields = [
                f
                for f in fields
                if f["value"] in ("driver_topics", "ai_insights", "consultant_analysis")
            ]

        return jsonify({"success": True, "fields": fields})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/<agent_id>/run", methods=["POST"])
def run_custom_agent(agent_id):
    """Executa um agente customizado"""
    try:
        # Obter configuração do agente
        agent = db.get_ai_agent(agent_id)
        if not agent:
            return jsonify({"success": False, "error": "Agente não encontrado"}), 404

        # Obter plan_id do payload
        payload = request.get_json() or {}
        plan_id = payload.get("plan_id")

        # TODO: Implementar lógica de execução do agente customizado
        return jsonify(
            {"success": True, "message": "Agente executado com sucesso", "result": {}}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _portfolio_exists(cursor, company_id: int, portfolio_id: int) -> bool:
    """Check if a portfolio exists for the given company and portfolio ID."""
    cursor.execute(
        "SELECT 1 FROM portfolios WHERE company_id = %s AND id = %s",
        (company_id, portfolio_id),
    )
    return cursor.fetchone() is not None


def _serialize_portfolio(row) -> Dict[str, Any]:
    """Serialize a portfolio row to a dictionary."""
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "code": row["code"],
        "name": row["name"],
        "responsible_id": row["responsible_id"]
        if "responsible_id" in row.keys()
        else None,
        "responsible_name": row["responsible_name"]
        if "responsible_name" in row.keys()
        else None,
        "notes": row["notes"],
        "project_count": row["project_count"] if "project_count" in row.keys() else 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.route("/api/companies/<int:company_id>/portfolios", methods=["GET", "POST"])
def api_company_portfolios(company_id: int):
    """List or create portfolios for a company."""
    if request.method == "GET":
        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.company_id,
                    p.code,
                    p.name,
                    p.responsible_id,
                    e.name AS responsible_name,
                    p.notes,
                    p.created_at,
                    p.updated_at,
                    COUNT(DISTINCT proj.id) AS project_count
                FROM portfolios p
                LEFT JOIN employees e ON e.id = p.responsible_id
                LEFT JOIN company_projects proj ON proj.plan_id = p.id
                WHERE p.company_id = %s
                GROUP BY p.id, p.company_id, p.code, p.name, p.responsible_id, 
                         e.name, p.notes, p.created_at, p.updated_at
                ORDER BY LOWER(p.name)
                """,
                (company_id,),
            )
            rows = cursor.fetchall()
            conn.close()

            portfolios = []
            for row in rows:
                portfolios.append(
                    {
                        "id": row["id"],
                        "company_id": row["company_id"],
                        "code": row["code"],
                        "name": row["name"],
                        "responsible_id": row["responsible_id"],
                        "responsible_name": row["responsible_name"],
                        "notes": row["notes"],
                        "project_count": row["project_count"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

            return jsonify({"success": True, "portfolios": portfolios})
        except Exception as exc:
            logger.info(f"Erro ao listar portfólios: {exc}")
            import traceback

            traceback.print_exc()
            return (
                jsonify({"success": False, "message": "Erro ao listar portfólios."}),
                500,
            )

    # POST - Create portfolio
    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").strip()
    name = (payload.get("name") or "").strip()
    responsible_id = payload.get("responsible_id")
    notes = (payload.get("notes") or "").strip() or None

    if not code:
        return (
            jsonify(
                {"success": False, "message": "Código do portfólio é obrigatório."}
            ),
            400,
        )
    if not name:
        return (
            jsonify({"success": False, "message": "Nome do portfólio é obrigatório."}),
            400,
        )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 1 FROM portfolios
            WHERE company_id = %s AND LOWER(code) = LOWER(?)
            """,
            (company_id, code),
        )
        if cursor.fetchone():
            conn.close()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Já existe um portfólio com este código para a empresa.",
                    }
                ),
                409,
            )

        cursor.execute(
            """
            INSERT INTO portfolios (company_id, code, name, responsible_id, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                company_id,
                code,
                name,
                int(responsible_id)
                if responsible_id and str(responsible_id).strip()
                else None,
                notes,
            ),
        )
        new_id = cursor.fetchone()[0]
        conn.commit()

        cursor.execute(
            """
            SELECT
                p.id,
                p.company_id,
                p.code,
                p.name,
                p.responsible_id,
                e.name AS responsible_name,
                p.notes,
                p.created_at,
                p.updated_at,
                0 AS project_count
            FROM portfolios p
            LEFT JOIN employees e ON e.id = p.responsible_id
            WHERE p.company_id = %s AND p.id = %s
            """,
            (company_id, new_id),
        )
        created_row = cursor.fetchone()
        conn.close()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Portfólio criado com sucesso.",
                    "portfolio": _serialize_portfolio(created_row),
                }
            ),
            201,
        )
    except Exception as exc:
        logger.info(f"Erro ao criar portfolio: {exc}")
        return jsonify({"success": False, "message": "Erro ao criar portfólio."}), 500


@app.route(
    "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>",
    methods=["PUT", "DELETE"],
)
def api_portfolio(company_id: int, portfolio_id: int):
    """Update or delete a portfolio."""
    if request.method == "DELETE":
        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()
            if not _portfolio_exists(cursor, company_id, portfolio_id):
                conn.close()
                return (
                    jsonify({"success": False, "message": "Portfólio não encontrado."}),
                    404,
                )

            # Verificar se há projetos associados ao portfólio
            # Considerar apenas projetos do tipo GRV (portfólios GRV)
            cursor.execute(
                "SELECT COUNT(*) FROM company_projects WHERE plan_id = %s AND (plan_type = 'GRV' OR plan_type IS NULL)",
                (portfolio_id,),
            )
            project_count = cursor.fetchone()[0]

            if project_count > 0:
                conn.close()
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Não é possível excluir o portfólio. Existem {project_count} projeto(s) associado(s) a este portfólio.",
                        }
                    ),
                    409,
                )

            cursor.execute(
                "DELETE FROM portfolios WHERE company_id = %s AND id = %s",
                (company_id, portfolio_id),
            )
            conn.commit()
            conn.close()
            return jsonify(
                {"success": True, "message": "Portfólio excluído com sucesso."}
            )
        except Exception as exc:
            logger.info(f"Erro ao excluir portfolio: {exc}")
            import traceback

            traceback.print_exc()
            return (
                jsonify({"success": False, "message": "Erro ao excluir portfólio."}),
                500,
            )

    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").strip()
    name = (payload.get("name") or "").strip()
    responsible_id = payload.get("responsible_id")
    notes = (payload.get("notes") or "").strip() or None

    if not code or not name:
        return (
            jsonify({"success": False, "message": "Código e nome são obrigatórios."}),
            400,
        )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        if not _portfolio_exists(cursor, company_id, portfolio_id):
            conn.close()
            return (
                jsonify({"success": False, "message": "Portfólio não encontrado."}),
                404,
            )

        cursor.execute(
            """
            SELECT 1 FROM portfolios
            WHERE company_id = %s AND LOWER(code) = LOWER(?) AND id <> ?
            """,
            (company_id, code, portfolio_id),
        )
        if cursor.fetchone():
            conn.close()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Já existe outro portfólio com este código.",
                    }
                ),
                409,
            )

        cursor.execute(
            """
            UPDATE portfolios
            SET code = %s, name = ?, responsible_id = %s, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE company_id = %s AND id = %s
            """,
            (
                code,
                name,
                int(responsible_id)
                if responsible_id and str(responsible_id).strip()
                else None,
                notes,
                company_id,
                portfolio_id,
            ),
        )
        conn.commit()

        cursor.execute(
            """
            SELECT
                p.id,
                p.company_id,
                p.code,
                p.name,
                p.responsible_id,
                e.name AS responsible_name,
                p.notes,
                p.created_at,
                p.updated_at,
                0 AS project_count
            FROM portfolios p
            LEFT JOIN employees e ON e.id = p.responsible_id
            WHERE p.company_id = %s AND p.id = %s
            """,
            (company_id, portfolio_id),
        )
        updated_row = cursor.fetchone()
        conn.close()

        return jsonify(
            {
                "success": True,
                "message": "Portfólio atualizado com sucesso.",
                "portfolio": _serialize_portfolio(updated_row),
            }
        )
    except Exception as exc:
        logger.info(f"Erro ao atualizar portfolio: {exc}")
        import traceback

        traceback.print_exc()
        return (
            jsonify({"success": False, "message": "Erro ao atualizar portfólio."}),
            500,
        )


# ============ COMPANY PROJECTS APIS ============


def _sanitize_company_code(raw_code: Optional[str], company_id: int) -> str:
    """Return sanitized company code used as project prefix."""
    if raw_code:
        cleaned = "".join(ch for ch in str(raw_code).strip().upper() if ch.isalnum())
        if cleaned:
            return cleaned
    return str(company_id).zfill(2)


def _normalize_activity_date(value: Any) -> Optional[str]:
    """Normalize activity date strings to ISO format (YYYY-MM-DD)."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    if _date_parser:
        try:
            return _date_parser.parse(text).date().isoformat()
        except Exception:
            return None
    return None


def _parse_project_activities(raw: Any) -> List[Dict[str, Any]]:
    """Parse activities JSON/text into a list of dictionaries."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [activity for activity in raw if isinstance(activity, dict)]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [activity for activity in parsed if isinstance(activity, dict)]
        except Exception:
            return []
    return []


def _ensure_activity_codes(
    activities: List[Dict[str, Any]], project_code: Optional[str]
) -> List[Dict[str, Any]]:
    """Guarantee that each activity carries a sequential code derived from the project code."""
    if not activities:
        if project_code:
            return [{"code": f"{project_code}.01", "status": "pending"}]
        return []
    normalized: List[Dict[str, Any]] = []
    for index, activity in enumerate(activities, start=1):
        item = dict(activity)
        code = str(item.get("code") or "").strip()
        if not code and project_code:
            code = f"{project_code}.{index:02d}"
        item["code"] = code or ""
        normalized.append(item)
    return normalized


def _compute_project_status_from_activities(activities: List[Dict[str, Any]]) -> str:
    """Derive project status considering the state of its activities."""
    if not activities:
        return "planned"
    statuses = {
        str((activity.get("status") or "")).strip().lower()
        for activity in activities
        if activity.get("status") is not None
    }
    completed_markers = {"completed", "concluido", "concluida", "done"}
    delayed_markers = {"delayed", "late", "overdue", "atrasado", "atrasada"}
    progress_markers = {
        "in_progress",
        "on_time",
        "progress",
        "executing",
        "executando",
        "em andamento",
    }
    if statuses and statuses.issubset(completed_markers):
        return "completed"
    if statuses & delayed_markers:
        return "delayed"
    if statuses & progress_markers:
        return "in_progress"
    return "planned"


def _calculate_activities_budget(activities: List[Dict[str, Any]]) -> Decimal:
    """Aggregate monetary values found in activity payloads."""
    total = Decimal("0")
    for activity in activities:
        raw_value = (
            activity.get("amount")
            or activity.get("budget")
            or activity.get("orcamento")
            or activity.get("valor")
        )
        decimal_value = _to_decimal(raw_value)
        if decimal_value is not None:
            total += decimal_value
    return total


def _derive_activity_schedule(
    activities: List[Dict[str, Any]],
    project_start: Optional[str],
    project_end: Optional[str],
) -> Dict[str, Optional[str]]:
    """Determine schedule bounds using activity deadlines with project dates as fallback."""
    collected_dates: List[str] = []
    for activity in activities:
        for candidate_key in ("when", "deadline", "due_date", "completion_date"):
            normalized = _normalize_activity_date(activity.get(candidate_key))
            if normalized:
                collected_dates.append(normalized)
    start_candidate = _normalize_activity_date(project_start) or project_start
    end_candidate = _normalize_activity_date(project_end) or project_end
    if collected_dates:
        collected_dates.sort()
        start_candidate = collected_dates[0]
        end_candidate = collected_dates[-1]
    return {"start": start_candidate, "end": end_candidate}


def _compute_next_project_code(cursor, company_id: int) -> Dict[str, Any]:
    """Generate a unique project code and sequence for the given company."""
    cursor.execute("SELECT client_code FROM companies WHERE id = %s", (company_id,))
    company_row = cursor.fetchone()
    company_code = _sanitize_company_code(
        company_row["client_code"] if company_row else None, company_id
    )

    cursor.execute(
        """
        SELECT
            COALESCE(MAX(code_sequence), 0) AS max_seq,
            COUNT(*) AS total_projects
        FROM company_projects
        WHERE company_id = %s
        """,
        (company_id,),
    )
    seq_row = cursor.fetchone() or {}
    max_seq = int(seq_row.get("max_seq") or 0)
    total_projects = int(seq_row.get("total_projects") or 0)
    base_seq = max(max_seq, total_projects)
    next_seq = base_seq + 1
    project_code = f"{company_code}.J.{next_seq}"
    return {"code": project_code, "sequence": next_seq, "company_code": company_code}


def _open_portfolio_connection():
    """Open a connection to the portfolio database with row_factory configured."""
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    return conn


def _serialize_company_project(row) -> Dict[str, Any]:
    raw_activities = row["activities"]
    project_code = row["code"] if "code" in row.keys() else None
    activities = _parse_project_activities(raw_activities)
    activities = _ensure_activity_codes(activities, project_code)

    delayed_markers = {"delayed", "late", "overdue", "atrasado", "atrasada"}
    delayed_count = sum(
        1
        for activity in activities
        if str(activity.get("status", "")).lower() in delayed_markers
    )

    status_value = _compute_project_status_from_activities(activities)
    budget_total = _calculate_activities_budget(activities)
    schedule = _derive_activity_schedule(activities, row["start_date"], row["end_date"])

    responsible_name = (
        row["responsible_name"] if "responsible_name" in row.keys() else None
    )
    owner_display = row["owner"] or responsible_name

    # Calcular prazo previsto (maior prazo das atividades)
    predicted_deadline = None
    if activities:
        activity_deadlines = []
        for activity in activities:
            # Tentar pegar o campo 'when' ou 'deadline' ou 'end_date'
            deadline = (
                activity.get("when")
                or activity.get("deadline")
                or activity.get("end_date")
            )
            if deadline:
                try:
                    from datetime import datetime

                    if isinstance(deadline, str):
                        # Tentar parsear a data
                        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
                            try:
                                dt = datetime.strptime(deadline, fmt)
                                activity_deadlines.append(dt)
                                break
                            except ValueError:
                                continue
                except Exception as exc:
                    pass

        if activity_deadlines:
            max_deadline = max(activity_deadlines)
            predicted_deadline = max_deadline.strftime("%Y-%m-%d")

    # Plan origin
    plan_origin = row["plan_origin"] if "plan_origin" in row.keys() else None

    # Plan mode - buscar do plano se o projeto está vinculado a um plano PEV
    plan_mode = "evolucao"  # default
    plan_id = row.get("plan_id")

    if plan_origin == "PEV" and plan_id:
        # Se está vinculado a um plano PEV, buscar plan_mode do plano
        try:
            # Primeiro tentar pegar da query (pode ser None se LEFT JOIN não encontrou)
            plan_mode_value = row.get("plan_mode")

            if plan_mode_value:
                plan_mode = str(plan_mode_value).lower()
            else:
                # Se não veio na query (None), buscar diretamente do banco
                db_instance = get_db()
                plan_data = db_instance.get_plan_with_company(int(plan_id))
                if plan_data:
                    plan_mode = (plan_data.get("plan_mode") or "evolucao").lower()
        except Exception as e:
            # Em caso de erro, usar evolução como padrão
            plan_mode = "evolucao"

    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "plan_id": row["plan_id"],
        "plan_name": row["plan_name"],
        "plan_origin": plan_origin,
        "plan_mode": plan_mode,
        "title": row["title"],
        "name": row["title"],  # Adicionar campo name para compatibilidade
        "description": row["description"],
        "status": status_value,
        "status_stored": row["status"],
        "priority": row["priority"],
        "owner": owner_display,
        "responsible_id": row["responsible_id"]
        if "responsible_id" in row.keys()
        else None,
        "responsible_name": responsible_name,
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "predicted_deadline": predicted_deadline,
        "schedule_start": schedule["start"],
        "schedule_end": schedule["end"],
        "okr_area_ref": row["okr_area_ref"],
        "okr_reference": row["okr_reference"]
        if "okr_reference" in row.keys()
        else None,
        "indicator_reference": row["indicator_reference"]
        if "indicator_reference" in row.keys()
        else None,
        "activities": activities,
        "notes": row["notes"],
        "budget_total": float(budget_total) if budget_total is not None else 0.0,
        "activities_count": len(activities),
        "delayed_activities": delayed_count,
        "code": project_code,
        "code_sequence": row["code_sequence"]
        if "code_sequence" in row.keys()
        else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _generate_project_code(cursor, company_id: int) -> tuple:
    """Generate automatic project code for a company.
    Returns tuple: (code_string, sequence_number)
    Example: ('AB.J.12', 12)
    """
    # Get company client_code
    cursor.execute("SELECT client_code FROM companies WHERE id = %s", (company_id,))
    company_row = cursor.fetchone()
    if not company_row or not company_row["client_code"]:
        return (None, None)

    client_code = company_row["client_code"].strip().upper()

    # Get next sequence number for this company's projects
    cursor.execute(
        "SELECT MAX(code_sequence) as max_seq FROM company_projects WHERE company_id = %s",
        (company_id,),
    )
    result = cursor.fetchone()
    next_sequence = (result["max_seq"] or 0) + 1

    # Format: CLIENT_CODE.J.SEQUENCE
    code = f"{client_code}.J.{next_sequence}"

    return (code, next_sequence)


@app.route("/api/companies/<int:company_id>/projects", methods=["GET", "POST"])
def api_company_projects(company_id: int):
    if request.method == "GET":
        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()

            # Filtro opcional por plan_id
            plan_id_filter = request.args.get("plan_id")

            if plan_id_filter:
                # Filtrar por plan_id específico
                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.company_id,
                        p.plan_id,
                        p.plan_type,
                        CASE 
                            WHEN p.plan_type = 'GRV' THEN pf.name
                            WHEN p.plan_type = 'PEV' THEN pl.name
                            ELSE COALESCE(pf.name, pl.name)
                        END AS plan_name,
                        p.plan_type AS plan_origin,
                        pl.plan_mode,
                        p.title,
                        p.description,
                        p.status,
                        p.priority,
                        p.owner,
                        p.responsible_id,
                        e.name AS responsible_name,
                        p.start_date,
                        p.end_date,
                        p.okr_area_ref,
                        p.okr_reference,
                        p.indicator_reference,
                        p.activities,
                        p.notes,
                        p.code,
                        p.code_sequence,
                        p.created_at,
                        p.updated_at
                    FROM company_projects p
                    LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
                    LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
                    LEFT JOIN employees e ON e.id = p.responsible_id
                    WHERE p.company_id = %s AND p.plan_id = %s
                    ORDER BY LOWER(p.title)
                    """,
                    (company_id, int(plan_id_filter)),
                )
            else:
                # Listar todos os projetos da empresa
                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.company_id,
                        p.plan_id,
                        p.plan_type,
                        CASE 
                            WHEN p.plan_type = 'GRV' THEN pf.name
                            WHEN p.plan_type = 'PEV' THEN pl.name
                            ELSE COALESCE(pf.name, pl.name)
                        END AS plan_name,
                        p.plan_type AS plan_origin,
                        pl.plan_mode,
                        p.title,
                        p.description,
                        p.status,
                        p.priority,
                        p.owner,
                        p.responsible_id,
                        e.name AS responsible_name,
                        p.start_date,
                        p.end_date,
                        p.okr_area_ref,
                        p.okr_reference,
                        p.indicator_reference,
                        p.activities,
                        p.notes,
                        p.code,
                        p.code_sequence,
                        p.created_at,
                        p.updated_at
                    FROM company_projects p
                    LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
                    LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
                    LEFT JOIN employees e ON e.id = p.responsible_id
                    WHERE p.company_id = %s
                    ORDER BY LOWER(p.title)
                    """,
                    (company_id,),
                )

            rows = cursor.fetchall()
            conn.close()
            return jsonify(
                {
                    "success": True,
                    "projects": [_serialize_company_project(row) for row in rows],
                }
            )
        except Exception as exc:
            logger.info(f"Erro ao buscar projetos: {exc}")
            return (
                jsonify({"success": False, "message": "Erro ao listar projetos."}),
                500,
            )

    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return (
            jsonify({"success": False, "message": "Título do projeto é obrigatório."}),
            400,
        )

    plan_id = payload.get("plan_id")
    plan_type = (payload.get("plan_type") or "").strip() or None  # 'PEV' or 'GRV'
    priority = (payload.get("priority") or "").strip() or None
    description = (payload.get("description") or "").strip() or None
    notes = (payload.get("notes") or "").strip() or None
    start_date = payload.get("start_date") or None
    end_date = payload.get("end_date") or None

    # New fields
    responsible_id = payload.get("responsible_id") or None
    okr_reference = (payload.get("okr_reference") or "").strip() or None
    indicator_reference = (payload.get("indicator_reference") or "").strip() or None

    activities_json = None
    activities_payload = payload.get("activities")
    if activities_payload:
        try:
            activities_json = json.dumps(activities_payload)
        except Exception:
            return (
                jsonify(
                    {"success": False, "message": "Formato de atividades inválido."}
                ),
                400,
            )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        plan_id_value = None
        if plan_id:
            # Verificar se é um plan PEV ou portfolio GRV
            cursor.execute("SELECT company_id FROM plans WHERE id = %s", (plan_id,))
            plan_row = cursor.fetchone()

            if plan_row and plan_row["company_id"] == company_id:
                # É um plan PEV válido
                plan_id_value = int(plan_id)
            else:
                # Verificar se é um portfolio GRV
                cursor.execute(
                    "SELECT company_id FROM portfolios WHERE id = %s", (plan_id,)
                )
                portfolio_row = cursor.fetchone()

                if portfolio_row and portfolio_row["company_id"] == company_id:
                    # É um portfolio GRV válido
                    plan_id_value = int(plan_id)
                else:
                    conn.close()
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "Planejamento ou portfólio inválido para esta empresa.",
                            }
                        ),
                        400,
                    )

        # Generate project code
        project_code, code_sequence = _generate_project_code(cursor, company_id)

        cursor.execute(
            """
            INSERT INTO company_projects (
                company_id, plan_id, plan_type, title, description, priority,
                responsible_id, start_date, end_date, 
                okr_reference, indicator_reference, activities, notes,
                code, code_sequence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                company_id,
                plan_id_value,
                plan_type,
                title,
                description,
                priority,
                responsible_id,
                start_date,
                end_date,
                okr_reference,
                indicator_reference,
                activities_json,
                notes,
                project_code,
                code_sequence,
            ),
        )
        new_id = cursor.fetchone()[0]
        conn.commit()

        cursor.execute(
            """
            SELECT
                p.id,
                p.company_id,
                p.plan_id,
                p.plan_type,
                CASE 
                    WHEN p.plan_type = 'GRV' THEN pf.name
                    WHEN p.plan_type = 'PEV' THEN pl.name
                    ELSE COALESCE(pf.name, pl.name)
                END AS plan_name,
                p.plan_type AS plan_origin,
                p.title,
                p.description,
                p.status,
                p.priority,
                p.owner,
                p.responsible_id,
                e.name AS responsible_name,
                p.start_date,
                p.end_date,
                p.okr_area_ref,
                p.okr_reference,
                p.indicator_reference,
                p.activities,
                p.notes,
                p.code,
                p.code_sequence,
                p.created_at,
                p.updated_at
            FROM company_projects p
            LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
            LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
            LEFT JOIN employees e ON e.id = p.responsible_id
            WHERE p.company_id = %s AND p.id = %s
            """,
            (company_id, new_id),
        )
        created_row = cursor.fetchone()
        conn.close()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Projeto criado com sucesso.",
                    "project": _serialize_company_project(created_row),
                }
            ),
            201,
        )
    except Exception as exc:
        logger.info(f"Erro ao criar projeto: {exc}")
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {"success": False, "message": f"Erro ao criar projeto: {str(exc)}"}
            ),
            500,
        )


@app.route(
    "/api/companies/<int:company_id>/projects/<int:project_id>",
    methods=["PUT", "DELETE"],
)
def api_company_project(company_id: int, project_id: int):
    if request.method == "DELETE":
        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM company_projects WHERE company_id = %s AND id = %s",
                (company_id, project_id),
            )
            if cursor.fetchone() is None:
                conn.close()
                return (
                    jsonify({"success": False, "message": "Projeto não encontrado."}),
                    404,
                )

            cursor.execute(
                "DELETE FROM company_projects WHERE company_id = %s AND id = %s",
                (company_id, project_id),
            )
            conn.commit()
            conn.close()
            return jsonify(
                {"success": True, "message": "Projeto excluído com sucesso."}
            )
        except Exception as exc:
            logger.info(f"Erro ao excluir projeto: {exc}")
            return (
                jsonify({"success": False, "message": "Erro ao excluir projeto."}),
                500,
            )

    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return (
            jsonify({"success": False, "message": "Título do projeto é obrigatório."}),
            400,
        )

    plan_id = payload.get("plan_id")
    plan_type = (payload.get("plan_type") or "").strip() or None  # 'PEV' or 'GRV'
    priority = (payload.get("priority") or "").strip() or None
    description = (payload.get("description") or "").strip() or None
    notes = (payload.get("notes") or "").strip() or None
    start_date = payload.get("start_date") or None
    end_date = payload.get("end_date") or None

    # New fields
    responsible_id = payload.get("responsible_id") or None
    okr_reference = (payload.get("okr_reference") or "").strip() or None
    indicator_reference = (payload.get("indicator_reference") or "").strip() or None

    activities_json = None
    activities_payload = payload.get("activities")
    if activities_payload:
        try:
            activities_json = json.dumps(activities_payload)
        except Exception:
            return (
                jsonify(
                    {"success": False, "message": "Formato de atividades inválido."}
                ),
                400,
            )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM company_projects WHERE company_id = %s AND id = %s",
            (company_id, project_id),
        )
        if cursor.fetchone() is None:
            conn.close()
            return (
                jsonify({"success": False, "message": "Projeto não encontrado."}),
                404,
            )

        plan_id_value = None
        if plan_id:
            # Verificar se é um plan PEV ou portfolio GRV
            cursor.execute("SELECT company_id FROM plans WHERE id = %s", (plan_id,))
            plan_row = cursor.fetchone()

            if plan_row and plan_row["company_id"] == company_id:
                # É um plan PEV válido
                plan_id_value = int(plan_id)
                if not plan_type:  # Se não foi fornecido no payload, definir como PEV
                    plan_type = "PEV"
            else:
                # Verificar se é um portfolio GRV
                cursor.execute(
                    "SELECT company_id FROM portfolios WHERE id = %s", (plan_id,)
                )
                portfolio_row = cursor.fetchone()

                if portfolio_row and portfolio_row["company_id"] == company_id:
                    # É um portfolio GRV válido
                    plan_id_value = int(plan_id)
                    if (
                        not plan_type
                    ):  # Se não foi fornecido no payload, definir como GRV
                        plan_type = "GRV"
                else:
                    conn.close()
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "Planejamento ou portfólio inválido para esta empresa.",
                            }
                        ),
                        400,
                    )

        cursor.execute(
            """
            UPDATE company_projects
            SET plan_id = %s, plan_type = ?, title = ?, description = ?, priority = ?,
                responsible_id = %s, start_date = ?, end_date = ?,
                okr_reference = ?, indicator_reference = ?,
                activities = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE company_id = %s AND id = %s
            """,
            (
                plan_id_value,
                plan_type,
                title,
                description,
                priority,
                responsible_id,
                start_date,
                end_date,
                okr_reference,
                indicator_reference,
                activities_json,
                notes,
                company_id,
                project_id,
            ),
        )
        conn.commit()

        cursor.execute(
            """
            SELECT
                p.id,
                p.company_id,
                p.plan_id,
                p.plan_type,
                CASE 
                    WHEN p.plan_type = 'GRV' THEN pf.name
                    WHEN p.plan_type = 'PEV' THEN pl.name
                    ELSE COALESCE(pf.name, pl.name)
                END AS plan_name,
                p.plan_type AS plan_origin,
                p.title,
                p.description,
                p.status,
                p.priority,
                p.owner,
                p.responsible_id,
                e.name AS responsible_name,
                p.start_date,
                p.end_date,
                p.okr_area_ref,
                p.okr_reference,
                p.indicator_reference,
                p.activities,
                p.notes,
                p.code,
                p.code_sequence,
                p.created_at,
                p.updated_at
            FROM company_projects p
            LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
            LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
            LEFT JOIN employees e ON e.id = p.responsible_id
            WHERE p.company_id = %s AND p.id = %s
            """,
            (company_id, project_id),
        )
        updated_row = cursor.fetchone()
        conn.close()

        return jsonify(
            {
                "success": True,
                "message": "Projeto atualizado com sucesso.",
                "project": _serialize_company_project(updated_row),
            }
        )
    except Exception as exc:
        logger.info(f"Erro ao atualizar projeto: {exc}")
        return jsonify({"success": False, "message": "Erro ao atualizar projeto."}), 500


def _generate_activity_code(cursor, company_id: int, project_id: int) -> tuple:
    """Generate automatic activity code for a project.
    Returns tuple: (code_string, sequence_number)
    Example: ('AA.J.12.01', 1)
    """
    # Get project code
    cursor.execute("SELECT code FROM company_projects WHERE id = %s", (project_id,))
    project_row = cursor.fetchone()
    if not project_row or not project_row["code"]:
        return (None, None)

    project_code = project_row["code"]

    # Get existing activities to find max sequence
    cursor.execute(
        "SELECT activities FROM company_projects WHERE id = %s", (project_id,)
    )
    result = cursor.fetchone()
    activities_json = result["activities"] if result else None

    max_seq = 0
    if activities_json:
        try:
            import json

            activities = (
                json.loads(activities_json)
                if isinstance(activities_json, str)
                else activities_json
            )
            if isinstance(activities, list):
                for act in activities:
                    code = act.get("code", "")
                    if code and "." in code:
                        parts = code.split(".")
                        if len(parts) >= 4:
                            try:
                                seq = int(parts[3])
                                max_seq = max(max_seq, seq)
                            except ValueError:
                                pass
        except Exception as exc:
            pass

    next_sequence = max_seq + 1
    code = f"{project_code}.{next_sequence:02d}"

    return (code, next_sequence)


@app.route(
    "/api/companies/<int:company_id>/projects/<int:project_id>/activities",
    methods=["GET", "POST"],
)
def api_project_activities(company_id: int, project_id: int):
    """List or create activities for a project"""
    if request.method == "GET":
        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT activities, code FROM company_projects WHERE company_id = %s AND id = %s",
                (company_id, project_id),
            )
            row = cursor.fetchone()

            if not row:
                conn.close()
                return (
                    jsonify({"success": False, "message": "Projeto não encontrado."}),
                    404,
                )

            activities_raw = row["activities"]
            project_code = row["code"]

            activities = []
            if activities_raw:
                try:
                    activities = (
                        json.loads(activities_raw)
                        if isinstance(activities_raw, str)
                        else activities_raw
                    )
                    if not isinstance(activities, list):
                        activities = []
                except Exception:
                    activities = []

            activities, changed, _ = normalize_project_activities(
                activities, project_code
            )

            if changed:
                cursor.execute(
                    "UPDATE company_projects SET activities = %s, updated_at = CURRENT_TIMESTAMP WHERE company_id = %s AND id = %s",
                    (
                        json.dumps(activities, ensure_ascii=False),
                        company_id,
                        project_id,
                    ),
                )
                conn.commit()

            conn.close()
            return jsonify({"success": True, "activities": activities})
        except Exception as exc:
            logger.info(f"Erro ao listar atividades: {exc}")
            import traceback

            traceback.print_exc()
            return (
                jsonify({"success": False, "message": "Erro ao listar atividades."}),
                500,
            )

    # POST - Create activity
    payload = request.get_json(silent=True) or {}
    what = (payload.get("what") or "").strip()

    if not what:
        return (
            jsonify(
                {"success": False, "message": "Descrição da atividade é obrigatória."}
            ),
            400,
        )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT activities, code FROM company_projects WHERE company_id = %s AND id = %s",
            (company_id, project_id),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return (
                jsonify({"success": False, "message": "Projeto não encontrado."}),
                404,
            )

        project_code = row["code"]
        activities_raw = row["activities"]

        activities = []
        if activities_raw:
            try:
                activities = (
                    json.loads(activities_raw)
                    if isinstance(activities_raw, str)
                    else activities_raw
                )
                if not isinstance(activities, list):
                    activities = []
            except Exception:
                activities = []

        activities, _, _ = normalize_project_activities(activities, project_code)

        existing_ids = [act["id"] for act in activities]
        new_id = max(existing_ids) + 1 if existing_ids else 1

        new_activity = {
            "id": new_id,
            "code": None,
            "what": what,
            "who": payload.get("who"),
            "when": payload.get("when"),
            "how": payload.get("how"),
            "amount": payload.get("amount"),
            "observations": payload.get("observations"),
            "stage": "inbox",
            "status": "pending",
            "completion_date": None,
            "logs": payload.get("logs", []),
        }

        activities.append(new_activity)

        activities, _, _ = normalize_project_activities(activities, project_code)

        cursor.execute(
            "UPDATE company_projects SET activities = %s, updated_at = CURRENT_TIMESTAMP WHERE company_id = %s AND id = %s",
            (json.dumps(activities, ensure_ascii=False), company_id, project_id),
        )
        conn.commit()
        conn.close()

        created_activity = next(
            (act for act in activities if act.get("id") == new_id), new_activity
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Atividade criada com sucesso.",
                    "activity": created_activity,
                }
            ),
            201,
        )
    except Exception as exc:
        logger.info(f"Erro ao criar atividade: {exc}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": "Erro ao criar atividade."}), 500


@app.route(
    "/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>",
    methods=["PUT", "DELETE"],
)
def api_project_activity(company_id: int, project_id: int, activity_id: int):
    """Update or delete a project activity"""
    if request.method == "DELETE":
        try:
            conn = _open_portfolio_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT activities, code FROM company_projects WHERE company_id = %s AND id = %s",
                (company_id, project_id),
            )
            row = cursor.fetchone()

            if not row:
                conn.close()
                return (
                    jsonify({"success": False, "message": "Projeto não encontrado."}),
                    404,
                )

            activities_json = row["activities"]
            project_code = row["code"]
            activities = []

            if activities_json:
                try:
                    import json

                    activities = (
                        json.loads(activities_json)
                        if isinstance(activities_json, str)
                        else activities_json
                    )
                    if not isinstance(activities, list):
                        activities = []
                except Exception as exc:
                    activities = []

            # Remove activity
            activities = [a for a in activities if a.get("id") != activity_id]
            activities, changed, _ = normalize_project_activities(
                activities, project_code
            )

            # Save back
            import json

            cursor.execute(
                "UPDATE company_projects SET activities = %s, updated_at = CURRENT_TIMESTAMP WHERE company_id = %s AND id = %s",
                (json.dumps(activities, ensure_ascii=False), company_id, project_id),
            )
            conn.commit()
            conn.close()

            return jsonify(
                {"success": True, "message": "Atividade excluída com sucesso."}
            )
        except Exception as exc:
            logger.info(f"Erro ao excluir atividade: {exc}")
            return (
                jsonify({"success": False, "message": "Erro ao excluir atividade."}),
                500,
            )

    # PUT - Update activity
    payload = request.get_json(silent=True) or {}
    what = (payload.get("what") or "").strip()

    if not what:
        return (
            jsonify(
                {"success": False, "message": "Descrição da atividade é obrigatória."}
            ),
            400,
        )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT activities, code FROM company_projects WHERE company_id = %s AND id = %s",
            (company_id, project_id),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return (
                jsonify({"success": False, "message": "Projeto não encontrado."}),
                404,
            )

        activities_json = row["activities"]
        project_code = row["code"]
        activities = []

        if activities_json:
            try:
                import json

                activities = (
                    json.loads(activities_json)
                    if isinstance(activities_json, str)
                    else activities_json
                )
                if not isinstance(activities, list):
                    activities = []
            except Exception as exc:
                activities = []

        # Find and update activity
        activity_found = False
        for activity in activities:
            if activity.get("id") == activity_id:
                activity["what"] = what
                activity["who"] = payload.get("who")
                activity["when"] = payload.get("when")
                activity["how"] = payload.get("how")
                activity["amount"] = payload.get("amount")
                activity["observations"] = payload.get("observations")
                # Update logs if provided
                if "logs" in payload:
                    activity["logs"] = payload["logs"]
                activity_found = True
                break

        if not activity_found:
            conn.close()
            return (
                jsonify({"success": False, "message": "Atividade não encontrada."}),
                404,
            )

        activities, _, _ = normalize_project_activities(activities, project_code)

        cursor.execute(
            "UPDATE company_projects SET activities = %s, updated_at = CURRENT_TIMESTAMP WHERE company_id = %s AND id = %s",
            (json.dumps(activities, ensure_ascii=False), company_id, project_id),
        )
        conn.commit()
        conn.close()

        return jsonify(
            {"success": True, "message": "Atividade atualizada com sucesso."}
        )
    except Exception as exc:
        logger.info(f"Erro ao atualizar atividade: {exc}")
        return (
            jsonify({"success": False, "message": "Erro ao atualizar atividade."}),
            500,
        )


@app.route(
    "/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/stage",
    methods=["PATCH"],
)
def api_project_activity_stage(company_id: int, project_id: int, activity_id: int):
    """Update activity stage (for Kanban drag and drop)"""
    payload = request.get_json(silent=True) or {}
    stage = (payload.get("stage") or "").strip()

    if not stage:
        return jsonify({"success": False, "message": "Estágio é obrigatório."}), 400

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT activities, code FROM company_projects WHERE company_id = %s AND id = %s",
            (company_id, project_id),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return (
                jsonify({"success": False, "message": "Projeto não encontrado."}),
                404,
            )

        activities_json = row["activities"]
        project_code = row["code"]
        activities = []

        if activities_json:
            try:
                import json

                activities = (
                    json.loads(activities_json)
                    if isinstance(activities_json, str)
                    else activities_json
                )
                if not isinstance(activities, list):
                    activities = []
            except Exception as exc:
                activities = []

        # Find and update stage
        activity_found = False
        for activity in activities:
            if activity.get("id") == activity_id:
                activity["stage"] = stage

                # Update logs if provided
                if "logs" in payload:
                    activity["logs"] = payload["logs"]

                # Update completion_date if provided
                if "completion_date" in payload:
                    activity["completion_date"] = payload["completion_date"]

                # Auto-update status based on stage
                if stage == "completed":
                    activity["status"] = "completed"
                    if (
                        not activity.get("completion_date")
                        and "completion_date" not in payload
                    ):
                        from datetime import datetime

                        activity["completion_date"] = datetime.now().strftime(
                            "%Y-%m-%d"
                        )
                else:
                    activity["status"] = stage

                activity_found = True
                break

        if not activity_found:
            conn.close()
            return (
                jsonify({"success": False, "message": "Atividade não encontrada."}),
                404,
            )

        activities, _, _ = normalize_project_activities(activities, project_code)

        cursor.execute(
            "UPDATE company_projects SET activities = %s, updated_at = CURRENT_TIMESTAMP WHERE company_id = %s AND id = %s",
            (json.dumps(activities, ensure_ascii=False), company_id, project_id),
        )
        conn.commit()
        conn.close()

        return jsonify(
            {
                "success": True,
                "message": "Atividade movida com sucesso.",
                "stage": stage,
            }
        )
    except Exception as exc:
        logger.info(f"Erro ao atualizar estágio: {exc}")
        return jsonify({"success": False, "message": "Erro ao atualizar estágio."}), 500


@app.route(
    "/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/transfer",
    methods=["POST"],
)
def api_transfer_activity(company_id: int, project_id: int, activity_id: int):
    """Transfer activity from one project to another"""
    payload = request.get_json(silent=True) or {}
    target_project_id = payload.get("target_project_id")

    if not target_project_id:
        return (
            jsonify(
                {"success": False, "message": "ID do projeto de destino é obrigatório."}
            ),
            400,
        )

    if target_project_id == project_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Não é possível transferir para o mesmo projeto.",
                }
            ),
            400,
        )

    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        # Get source project activities
        cursor.execute(
            "SELECT activities, code FROM company_projects WHERE company_id = %s AND id = %s",
            (company_id, project_id),
        )
        source_row = cursor.fetchone()

        if not source_row:
            conn.close()
            return (
                jsonify(
                    {"success": False, "message": "Projeto de origem não encontrado."}
                ),
                404,
            )

        # Get target project activities
        cursor.execute(
            "SELECT activities, code FROM company_projects WHERE company_id = %s AND id = %s",
            (company_id, target_project_id),
        )
        target_row = cursor.fetchone()

        if not target_row:
            conn.close()
            return (
                jsonify(
                    {"success": False, "message": "Projeto de destino não encontrado."}
                ),
                404,
            )

        # Parse activities
        import json

        source_activities_json = source_row["activities"]
        source_code = source_row["code"]
        source_activities = []
        if source_activities_json:
            try:
                source_activities = (
                    json.loads(source_activities_json)
                    if isinstance(source_activities_json, str)
                    else source_activities_json
                )
                if not isinstance(source_activities, list):
                    source_activities = []
            except Exception as exc:
                source_activities = []

        target_activities_json = target_row["activities"]
        target_code = target_row["code"]
        target_activities = []
        if target_activities_json:
            try:
                target_activities = (
                    json.loads(target_activities_json)
                    if isinstance(target_activities_json, str)
                    else target_activities_json
                )
                if not isinstance(target_activities, list):
                    target_activities = []
            except Exception as exc:
                target_activities = []

        source_activities, _, _ = normalize_project_activities(
            source_activities, source_code
        )
        target_activities, _, target_max_sequence = normalize_project_activities(
            target_activities, target_code
        )

        # Find activity to transfer
        activity_to_transfer = None
        for activity in source_activities:
            if activity.get("id") == activity_id:
                activity_to_transfer = activity
                break

        if not activity_to_transfer:
            conn.close()
            return (
                jsonify({"success": False, "message": "Atividade não encontrada."}),
                404,
            )

        # Remove from source project
        source_activities = [a for a in source_activities if a.get("id") != activity_id]

        target_ids = [act["id"] for act in target_activities]
        new_target_id = max(target_ids) + 1 if target_ids else 1

        next_sequence = target_max_sequence + 1 if target_code else None
        activity_code = (
            f"{target_code}.{next_sequence:02d}"
            if target_code and next_sequence
            else None
        )

        if not activity_code:
            fallback_code, _ = _generate_activity_code(
                cursor, company_id, target_project_id
            )
            activity_code = fallback_code

        previous_code = activity_to_transfer.get("code")

        # Update activity with new code and reset stage
        activity_to_transfer["code"] = activity_code
        activity_to_transfer["id"] = new_target_id
        activity_to_transfer["stage"] = "inbox"  # Reset to inbox in new project
        activity_to_transfer["status"] = "pending"  # Reset status
        activity_to_transfer["completion_date"] = None  # Clear completion date

        # Add transfer history
        if "transfer_history" not in activity_to_transfer:
            activity_to_transfer["transfer_history"] = []

        from datetime import datetime

        transfer_entry = {
            "from_project_id": project_id,
            "to_project_id": target_project_id,
            "timestamp": datetime.now().isoformat(),
            "note": payload.get("note", ""),
            "old_code": previous_code or "",
            "new_code": activity_code,
        }
        activity_to_transfer["transfer_history"].append(transfer_entry)

        # Add transfer as diary log
        if "logs" not in activity_to_transfer:
            activity_to_transfer["logs"] = []

        transfer_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "transfer",
            "text": f"Atividade transferida do projeto {project_id} para o projeto {target_project_id}",
            "note": payload.get("note", ""),
            "old_code": previous_code or "",
            "new_code": activity_code,
        }
        activity_to_transfer["logs"].append(transfer_log)

        # Add to target project
        target_activities.append(activity_to_transfer)

        source_activities, _, _ = normalize_project_activities(
            source_activities, source_code
        )
        target_activities, _, _ = normalize_project_activities(
            target_activities, target_code
        )

        # Save both projects
        cursor.execute(
            "UPDATE company_projects SET activities = %s, updated_at = CURRENT_TIMESTAMP WHERE company_id = %s AND id = %s",
            (json.dumps(source_activities, ensure_ascii=False), company_id, project_id),
        )

        cursor.execute(
            "UPDATE company_projects SET activities = %s, updated_at = CURRENT_TIMESTAMP WHERE company_id = %s AND id = %s",
            (
                json.dumps(target_activities, ensure_ascii=False),
                company_id,
                target_project_id,
            ),
        )

        conn.commit()
        conn.close()

        return jsonify(
            {
                "success": True,
                "message": f"Atividade transferida com sucesso para o projeto de destino.",
                "new_code": activity_code,
            }
        )

    except Exception as exc:
        logger.info(f"Erro ao transferir atividade: {exc}")
        import traceback

        traceback.print_exc()
        return (
            jsonify({"success": False, "message": "Erro ao transferir atividade."}),
            500,
        )


@app.route(
    "/api/companies/<int:company_id>/projects/<int:project_id>/info", methods=["GET"]
)
def api_get_project_info(company_id: int, project_id: int):
    """Get basic project info for transfer history"""
    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                p.id,
                p.title AS name,
                p.code
            FROM company_projects p
            WHERE p.company_id = %s AND p.id = %s
            """,
            (company_id, project_id),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return (
                jsonify({"success": False, "message": "Projeto não encontrado."}),
                404,
            )

        return jsonify(
            {
                "success": True,
                "project": {"id": row["id"], "name": row["name"], "code": row["code"]},
            }
        )

    except Exception as exc:
        logger.info(f"Erro ao buscar projeto: {exc}")
        return jsonify({"success": False, "message": "Erro ao buscar projeto."}), 500


@app.route("/api/plans/<int:plan_id>/okr-global-records", methods=["GET"])
def api_plan_okr_global_records(plan_id: int):
    """Get OKR global records for a plan by stage"""
    stage = request.args.get("stage", "approval")
    try:
        records = db.get_global_okr_records(int(plan_id), stage)
        return jsonify({"success": True, "records": records})
    except Exception as exc:
        logger.info(f"Erro ao buscar OKRs: {exc}")
        return jsonify({"success": False, "message": "Erro ao listar OKRs."}), 500


@app.route("/api/plans/<int:plan_id>/projects", methods=["GET"])
def api_plan_projects(plan_id: int):
    try:
        conn = _open_portfolio_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                p.id,
                p.company_id,
                p.plan_id,
                pl.name AS plan_name,
                p.title,
                p.description,
                p.status,
                p.priority,
                p.owner,
                p.start_date,
                p.end_date,
                p.okr_area_ref,
                p.activities,
                p.notes,
                p.created_at,
                p.updated_at
            FROM company_projects p
            LEFT JOIN plans pl ON pl.id = p.plan_id
            WHERE p.plan_id = %s
            ORDER BY LOWER(p.title)
            """,
            (plan_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return jsonify(
            {
                "success": True,
                "projects": [_serialize_company_project(row) for row in rows],
            }
        )
    except Exception as exc:
        logger.info(f"Erro ao buscar projetos do plano: {exc}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Erro ao carregar projetos do planejamento.",
                }
            ),
            500,
        )


# User logs system routes are handled by blueprints

# ========================================
# MY WORK - Rota temporária REMOVIDA
# ========================================
# Agora usando blueprint: modules.my_work
# Acesse: /my-work/


# ========================================
# Health Check Endpoint
# ========================================
@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for Docker health monitoring
    Returns 200 OK if application is running and database is accessible
    """
    try:
        # Verificar conexão com banco de dados
        with models_db.engine.connect() as conn:
            conn.execute(models_db.text("SELECT 1"))

        return (
            jsonify(
                {"status": "healthy", "database": "connected", "application": "running"}
            ),
            200,
        )
    except Exception as e:
        return (
            jsonify(
                {"status": "unhealthy", "error": str(e), "database": "disconnected"}
            ),
            503,
        )


if __name__ == "__main__":
    try:
        # Print database configuration
        logger.info("Carregando configuração do banco...")
        db_config.print_config()

        logger.info("\nAPP29 - Sistema de Gestão Versus Starting...")
        logger.info("Database abstraction layer active")
        logger.info("Sistema de relatórios implementado")
        logger.info("Server running at: http://127.0.0.1:5003")
        logger.info("Available operations:")
        logger.info("   - View and edit company data")
        logger.info("   - Manage participants")
        logger.info("   - Manage drivers")
        logger.info("   - Manage OKRs (Global and Area)")
        logger.info("   - Manage projects")
        logger.info("   - Generate reports")
        logger.info("   - Strategic analysis with AI agents")
        logger.info("\nAI Agents available:")
        logger.info("   - Market Possibilities Agent (APM)")
        logger.info("   - Company Capacity Agent (ACE)")
        logger.info("   - Stakeholder Expectations Agent (AES)")
        logger.info("   - Coordinator Agent (AC)")
        logger.info("\nTo switch database:")
        logger.info("   - Set DB_TYPE environment variable (sqlite, postgresql)")
        logger.info("   - Configure connection parameters")

        # Inicializar Scheduler para tarefas agendadas
        logger.info("\n[SCHEDULER] Inicializando Scheduler de Tarefas...")
        try:
            from services.scheduler_service import (
                initialize_scheduler,
                shutdown_scheduler,
            )
            import atexit

            # Iniciar scheduler
            initialize_scheduler()

            # Registrar shutdown do scheduler ao fechar a aplicação
            atexit.register(shutdown_scheduler)

            logger.info(
                "[OK] Scheduler ativo - Rotinas serao executadas automaticamente!"
            )
        except Exception as e:
            logger.info(f"[AVISO] Scheduler nao pode ser iniciado: {e}")
            logger.info(
                "   Rotinas devem ser executadas manualmente via routine_scheduler.py"
            )

        logger.info("\nIniciando servidor...")
        # Reload trigger
        app.run(debug=True, host="0.0.0.0", port=5003, use_reloader=False)
    except Exception as e:
        logger.info(f">> ERRO AO INICIAR SERVIDOR: {e}")
        import traceback

        traceback.print_exc()
