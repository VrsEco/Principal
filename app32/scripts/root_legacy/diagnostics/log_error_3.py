import traceback
import sys

with open('full_error_3.txt', 'w') as f:
    try:
        from api.routes.ai_board import ai_board_bp
        f.write("Import successful\n")
    except Exception:
        traceback.print_exc(file=f)
    except BaseException as e:
        f.write(f"BaseException: {str(e)}\n")
        traceback.print_exc(file=f)
