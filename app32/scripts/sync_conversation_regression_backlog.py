from __future__ import annotations

import argparse
import json
from pathlib import Path

from app import create_app
from services.conversation_regression_backlog_service import ConversationRegressionBacklogService
from services.conversation_regression_service import ConversationRegressionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sincroniza backlog AA.J.31 a partir da suíte de regressão conversacional.")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--status", default="inbox")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--company-id", type=int, default=None)
    parser.add_argument("--snapshot-dir", default=None)
    parser.add_argument("--dry-run", action="store_true")
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
        snapshot = ConversationRegressionService.build_snapshot(workflow_gap_candidates=candidates)
        if args.snapshot_dir:
            ConversationRegressionService.persist_snapshot(snapshot, output_dir=args.snapshot_dir)
        result = ConversationRegressionBacklogService.apply_sync_payload(
            snapshot["backlog_sync"],
            user_id=args.user_id,
            persist=not args.dry_run,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
