from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Avalia a assertividade do Workflow Discovery V3."
    )
    parser.add_argument(
        "--company-id",
        type=int,
        default=None,
        help="Company ID preferencial para avaliar o catálogo.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Quantidade máxima de candidatos por caso.",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=0.70,
        help="Acurácia mínima esperada para retornar sucesso.",
    )
    parser.add_argument(
        "--config",
        default=os.environ.get("FLASK_CONFIG", "development"),
        help="Configuração Flask usada para criar a aplicação.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, project_root)

    load_dotenv(os.path.join(project_root, ".env"))
    os.environ["FLASK_CONFIG"] = args.config

    from sqlalchemy import or_

    from app import create_app
    from models.agent_menu import AgentMenuOption
    from src.intelligence.workflows import (
        WorkflowRuntime,
        build_default_workflow_evaluation_cases,
        evaluate_workflow_discovery,
    )

    app = create_app(args.config)
    with app.app_context():
        query = AgentMenuOption.query.filter(AgentMenuOption.is_active.is_(True))
        if args.company_id is not None:
            query = query.filter(
                or_(
                    AgentMenuOption.company_id == args.company_id,
                    AgentMenuOption.company_id.is_(None),
                )
            )
        else:
            query = query.filter(AgentMenuOption.company_id.is_(None))

        options = query.order_by(
            AgentMenuOption.sort_order.asc(),
            AgentMenuOption.code.asc(),
        ).all()

        runtime = WorkflowRuntime()
        report = evaluate_workflow_discovery(
            runtime=runtime,
            cases=build_default_workflow_evaluation_cases(),
            options=options,
            preferred_company_id=args.company_id,
            top_k=args.top_k,
        )

    print("=" * 72)
    print("WORKFLOW DISCOVERY EVALUATION")
    print("=" * 72)
    print(f"total_cases      : {report.total_cases}")
    print(f"accuracy         : {report.accuracy:.2%}")
    print(f"top_k_accuracy   : {report.top_k_accuracy:.2%}")
    print(f"mrr              : {report.mean_reciprocal_rank:.4f}")
    print("")
    print("Por domínio:")
    for domain_report in report.domain_breakdown:
        print(
            f"- {domain_report.domain}: "
            f"acc={domain_report.accuracy:.2%} | "
            f"top_k={domain_report.top_k_accuracy:.2%} | "
            f"mrr={domain_report.mean_reciprocal_rank:.4f} | "
            f"casos={domain_report.total_cases}"
        )

    failures = [item for item in report.items if not item.success]
    if failures:
        print("")
        print("Falhas top-1:")
        for item in failures[:10]:
            print(
                f"- [{item.domain}] {item.label or item.text}: "
                f"esperado={item.expected_action_key} | "
                f"selecionado={item.selected_action_key} | "
                f"rank={item.expected_rank} | "
                f"top_matches={item.top_matches}"
            )

    return 0 if report.accuracy >= args.min_accuracy else 1


if __name__ == "__main__":
    raise SystemExit(main())
