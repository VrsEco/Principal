from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app
from services.process_code_repair_service import rebuild_process_hierarchy_codes


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python repair_process_codes.py <company_id>")
        return 1

    company_id = int(sys.argv[1])
    app = create_app("production")
    with app.app_context():
        result = rebuild_process_hierarchy_codes(company_id)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
