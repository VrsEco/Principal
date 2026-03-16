from flask import Blueprint, redirect, render_template, session, url_for
from flask_login import login_required
from sqlalchemy import text

from models import db
from utils.permissions import permission_required


indicator_analysis_safe_bp = Blueprint("indicator_analysis_safe", __name__)


def _serialize_rows(rows):
    return [dict(row._mapping) for row in rows]


@indicator_analysis_safe_bp.route("/indicators/analysis")
@login_required
@permission_required("indicators", "view")
def indicator_analysis():
    company_id = session.get("active_company_id")
    if not company_id:
        return redirect(url_for("auth.portal"))

    company_id = int(company_id)

    indicators_payload = []
    goals_payload = []
    data_payload = []

    try:
        indicators_sql = text(
            """
            SELECT
                i.id,
                i.code,
                i.name,
                i.indicator_type,
                i.source_module,
                i.unit
            FROM indicators i
            WHERE i.company_id = :company_id
              AND COALESCE(i.is_active, TRUE) = TRUE
            ORDER BY i.source_module NULLS LAST, i.name
            """
        )
        indicators_payload = _serialize_rows(
            db.session.execute(indicators_sql, {"company_id": company_id})
        )

        goals_sql = text(
            """
            SELECT
                g.id,
                g.indicator_id,
                g.goal_value,
                g.goal_date,
                g.period_start,
                g.period_end,
                g.status,
                g.goal_type
            FROM indicator_goals g
            WHERE g.company_id = :company_id
            ORDER BY g.goal_date DESC NULLS LAST, g.id DESC
            """
        )
        goals_payload = [
            {
                **row,
                "goal_value": float(row["goal_value"]) if row.get("goal_value") is not None else None,
                "goal_date": row["goal_date"].isoformat() if row.get("goal_date") else None,
                "period_start": row["period_start"].isoformat() if row.get("period_start") else None,
                "period_end": row["period_end"].isoformat() if row.get("period_end") else None,
            }
            for row in _serialize_rows(
                db.session.execute(goals_sql, {"company_id": company_id})
            )
        ]

        data_sql = text(
            """
            SELECT
                d.id,
                g.indicator_id,
                d.goal_id,
                d.value AS measured_value,
                d.record_date AS measured_date
            FROM indicator_data d
            JOIN indicator_goals g ON g.id = d.goal_id
            WHERE d.company_id = :company_id
              AND g.company_id = :company_id
            ORDER BY d.record_date DESC, d.id DESC
            """
        )
        data_payload = [
            {
                **row,
                "measured_value": float(row["measured_value"]) if row.get("measured_value") is not None else None,
                "measured_date": row["measured_date"].isoformat() if row.get("measured_date") else None,
            }
            for row in _serialize_rows(
                db.session.execute(data_sql, {"company_id": company_id})
            )
        ]
    except Exception:
        indicators_payload = []
        goals_payload = []
        data_payload = []

    return render_template(
        "modules/indicators/comparative_analysis.html",
        indicators_payload=indicators_payload,
        goals_payload=goals_payload,
        data_payload=data_payload,
    )


@indicator_analysis_safe_bp.route("/incentives/comparative")
@login_required
def comparative_legacy_redirect():
    return redirect(url_for("indicator_analysis_safe.indicator_analysis"))
