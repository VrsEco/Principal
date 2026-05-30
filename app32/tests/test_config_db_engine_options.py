from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from config import Config, ProductionConfig


def test_base_config_enables_db_connection_health_checks():
    assert Config.SQLALCHEMY_ENGINE_OPTIONS["pool_pre_ping"] is True
    assert Config.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] >= 300
    assert Config.SQLALCHEMY_ENGINE_OPTIONS["pool_use_lifo"] is True


def test_production_config_extends_engine_pool_options():
    assert ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS["pool_pre_ping"] is True
    assert ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS["pool_size"] >= 1
    assert ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS["max_overflow"] >= 0
