"""Helper script to inspect company projects, responsibles, executors and JSON activities."""
import argparse
import json
import os
import sys
from typing import Any, Dict

sys.path.append(os.getcwd())

from app_pev import app  # noqa: E402
from models import db  # noqa: E402


def _row_to_dict(row) -> Dict[str, Any]:
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    try:
        return dict(row)
    except Exception:
        return {}


def inspect(company_id: int, code_prefix: str):
    query = db.text(
        """
        SELECT
            cp.id,
            cp.code,
            cp.title,
            cp.company_id,
            cp.responsible_id,
            resp.name AS responsible_name,
            resp.email AS responsible_email,
            cp.executor_id,
            exec.name AS executor_name,
            exec.email AS executor_email,
            cp.activities
        FROM company_projects cp
        LEFT JOIN employees resp ON resp.id = cp.responsible_id
        LEFT JOIN employees exec ON exec.id = cp.executor_id
        WHERE cp.company_id = :company_id
          AND cp.code LIKE :code_prefix
        ORDER BY cp.code
        """
    )

    rows = db.session.execute(
        query, {"company_id": company_id, "code_prefix": code_prefix}
    ).fetchall()

    data = []
    for row in rows:
        payload = _row_to_dict(row)
        activities_value = payload.get("activities")
        try:
            payload["activities"] = (
                json.loads(activities_value) if activities_value else []
            )
        except json.JSONDecodeError:
            payload["activities"] = activities_value
        data.append(payload)

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Inspect company projects and their activities."
    )
    parser.add_argument("--company-id", type=int, required=True, help="Target company ID")
    parser.add_argument(
        "--code-prefix",
        default="%",
        help="LIKE pattern for project codes (default: %(default)s)",
    )
    args = parser.parse_args()

    with app.app_context():
        results = inspect(args.company_id, args.code_prefix)
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

