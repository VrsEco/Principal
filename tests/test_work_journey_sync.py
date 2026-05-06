import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.work_journey_sync import build_process_instance_source_url


def test_build_process_instance_source_url_points_to_bpms_shell():
    assert build_process_instance_source_url(9, 123) == "/my-work/process-instance/123?company_id=9&from=work-journey"
