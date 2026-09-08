"""Local SE-COORD entry: JSON on stdin, advisory assessment on stdout. No LLM/DB."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError
from services.engineering_task_router_service import EngineeringTaskRouterService
from services.engineering_token_economy_service import EngineeringTokenEconomyService


def main() -> int:
    try:
        raw = sys.stdin.read(65537)
        if len(raw) > 65536:
            raise ValueError('input_too_large')
        assessment = EngineeringTaskRouterService.assess(json.loads(raw))
        token_economy = EngineeringTokenEconomyService.advise(assessment)
    except (ValueError, ValidationError):
        # Pydantic exceptions can embed the submitted content: never echo them.
        print(json.dumps({'success': False, 'error': 'invalid_assessment_request'}))
        return 2
    print(json.dumps({'success': True, 'assessment': assessment.model_dump(mode='json'),
                      'token_economy': token_economy.model_dump(mode='json'),
                      'telemetry': assessment.telemetry(), 'token_economy_telemetry': token_economy.telemetry()}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
