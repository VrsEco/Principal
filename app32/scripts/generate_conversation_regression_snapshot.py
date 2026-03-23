from __future__ import annotations

import argparse
import json
from pathlib import Path

from app import create_app
from services.conversation_regression_service import ConversationRegressionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera snapshot operacional da suíte de regressão conversacional.")
    parser.add_argument("--output-dir", default=str(Path("artifacts") / "conversation_regression"))
    parser.add_argument("--status", default="inbox")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--company-id", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()
    with app.app_context():
        candidates = ConversationRegressionService.collect_workflow_gap_candidates(
            status=args.status,
            limit=args.limit,
            company_id=args.company_id,
        )
        snapshot = ConversationRegressionService.build_snapshot(
            workflow_gap_candidates=candidates,
        )
        paths = ConversationRegressionService.persist_snapshot(
            snapshot,
            output_dir=args.output_dir,
        )
    print(json.dumps({"generated": paths, "gap_count": len(candidates)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
