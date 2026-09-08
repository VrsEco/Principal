"""Compare a declared baseline/candidate JSON pair from stdin, without external I/O."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.intelligence.engineering_assessment import AssessmentModel
from services.engineering_measurement_service import EngineeringMeasurement, EngineeringMeasurementService


class ComparisonRequest(AssessmentModel):
    baseline: EngineeringMeasurement
    candidate: EngineeringMeasurement


def main():
    try:
        raw=sys.stdin.read(65537)
        if len(raw)>65536:
            raise ValueError('Input too large')
        request=ComparisonRequest.model_validate_json(raw)
        report=EngineeringMeasurementService.compare(request.baseline,request.candidate)
    except (ValueError,TypeError,OSError):
        print(json.dumps({'success':False,'error':'invalid_or_incomparable_measurements'}))
        return 2
    print(json.dumps({'success':True,'report':report}))
    if not report['quality_preserved_declared']:
        return 3
    if report['reported_total_tokens']['reduction_percent'] is None:
        return 4
    return 0


if __name__=='__main__':
    raise SystemExit(main())
