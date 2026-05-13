import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from services.user_mcp_token_service import user_mcp_token_service


def main() -> None:
    app = create_app("production")
    with app.app_context():
        result = user_mcp_token_service.send_expiration_notifications()
        payload = {
            "success": True,
            "executed_at": datetime.utcnow().isoformat(),
            **result,
        }
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
