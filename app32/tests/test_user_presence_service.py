import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.user_presence_service import UserPresenceService


def _presence(now, *, seen_seconds=0, expires_seconds=900, logout=False, revoked=False):
    return SimpleNamespace(
        last_seen_at=now - timedelta(seconds=seen_seconds),
        expires_at=now + timedelta(seconds=expires_seconds),
        logout_at=now if logout else None,
        revoked_at=now if revoked else None,
    )


def test_presence_status_windows_are_deterministic():
    now = datetime.utcnow()

    assert UserPresenceService._status_for(_presence(now, seen_seconds=30), now) == "online"
    assert UserPresenceService._status_for(_presence(now, seen_seconds=240), now) == "idle"
    assert UserPresenceService._status_for(_presence(now, expires_seconds=-1), now) == "offline"
    assert UserPresenceService._status_for(_presence(now, revoked=True), now) == "revoked"


def test_presence_device_metadata_does_not_store_full_user_agent():
    assert UserPresenceService._device_metadata("Mozilla/5.0 iPhone Safari/605.1") == ("mobile", "Safari")
    assert UserPresenceService._device_metadata("Mozilla/5.0 Windows Chrome/126.0") == ("desktop", "Chrome")


def test_presence_digest_is_keyed_and_does_not_expose_token():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "presence-test-secret"
    with app.app_context():
        digest = UserPresenceService._digest("opaque-session-token")

    assert len(digest) == 64
    assert "opaque-session-token" not in digest

