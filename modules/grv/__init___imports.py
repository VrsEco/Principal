import logging
from flask import (
    Blueprint,
    render_template,
    abort,
    url_for,
    make_response,
    request,
    jsonify,
    redirect,
    current_app,
)
from flask_login import login_required, current_user
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import subprocess
import sys
import threading
from typing import Any, Dict, Optional
from config_database import get_db
from middleware.auto_log_decorator import auto_log_crud
from services.routines_overview_service import build_routines_overview_context
from utils.company_access import get_user_allowed_company_ids

logger = logging.getLogger(__name__)
grv_bp = Blueprint("grv", __name__, url_prefix="/grv")

logger.info("MÓDULO GRV CARREGADO - VERSÃO COM API ROUTES")

# Import project hours API at the top
from modules.grv import project_hours_api
