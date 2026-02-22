from flask import Blueprint, session, jsonify
from flask_login import current_user, login_required

from models import db, Company, Project, Indicator, Process, ProcessInstance


diag_bp = Blueprint('diag', __name__)

@diag_bp.route('/api/debug-session')
@login_required
def debug_session():
    return jsonify({
        "user_id": current_user.id if current_user.is_authenticated else None,
        "user_role": current_user.role if current_user.is_authenticated else None,
        "active_company_id": session.get('active_company_id'),
        "all_session_keys": list(session.keys())
    })


@diag_bp.route('/api/diag/data-health')
@login_required
def data_health():
    """Diagnóstico rápido de dados por empresa (para achar telas vazias com dado no banco)."""
    active_company_id = session.get("active_company_id")
    company_id = None
    try:
        if active_company_id is not None and str(active_company_id).strip().lower() not in ("null", "undefined", "none", ""):
            company_id = int(float(active_company_id))
    except (TypeError, ValueError):
        company_id = None

    payload = {
        "user": {
            "id": current_user.id if current_user.is_authenticated else None,
            "role": getattr(current_user, "role", None),
        },
        "company_context": {
            "active_company_id_raw": active_company_id,
            "active_company_id": company_id,
        },
        "counts": {},
        "warnings": [],
    }

    # Counts base (sempre disponíveis via ORM)
    try:
        payload["counts"]["companies_active"] = Company.query.filter_by(is_active=True).count()
    except Exception as exc:
        payload["warnings"].append(f"Falha companies_active: {exc}")

    if company_id:
        # projects (tabela projects via ORM)
        try:
            payload["counts"]["projects_by_company"] = (
                Project.query.filter(Project.company_id == company_id).count()
            )
        except Exception as exc:
            payload["warnings"].append(f"Falha projects_by_company: {exc}")

        try:
            payload["counts"]["indicators_by_company"] = Indicator.query.filter(Indicator.company_id == company_id).count()
        except Exception as exc:
            payload["warnings"].append(f"Falha indicators_by_company: {exc}")

        try:
            payload["counts"]["processes_by_company"] = Process.query.filter(Process.company_id == company_id).count()
        except Exception as exc:
            payload["warnings"].append(f"Falha processes_by_company: {exc}")

        try:
            payload["counts"]["process_instances_by_company"] = (
                ProcessInstance.query.filter(ProcessInstance.company_id == company_id).count()
            )
        except Exception as exc:
            payload["warnings"].append(f"Falha process_instances_by_company: {exc}")

        # company_projects pode existir (herdado/compat). Vamos checar via SQL direto (sem depender de model).
        try:
            result = db.session.execute(
                db.text("SELECT COUNT(1) AS c FROM company_projects WHERE company_id = :cid"),
                {"cid": company_id},
            ).mappings().first()
            payload["counts"]["company_projects_by_company"] = int(result["c"]) if result and result.get("c") is not None else 0
        except Exception as exc:
            payload["warnings"].append(f"company_projects indisponível/erro: {exc}")

    return jsonify(payload)
