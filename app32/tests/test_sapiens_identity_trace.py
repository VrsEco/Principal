import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.identity import (
    build_identity_resolution_trace,
    resolve_user_identity_with_trace,
)


class DummyUser:
    id = 42


def test_build_whatsapp_identity_trace_normalizes_phone_variants():
    trace = build_identity_resolution_trace("+55 (71) 99642-6565", "whatsapp", user=DummyUser())

    assert trace.channel == "whatsapp"
    assert trace.normalized_identifier == "+55 (71) 99642-6565"
    assert trace.supported_channel is True
    assert trace.matched is True
    assert trace.user_id == 42
    assert "5571996426565" in trace.variants
    assert "7196426565" in trace.variants
    assert trace.to_safe_dict()["variants_count"] == len(trace.variants)
    assert "raw_identifier" not in trace.to_safe_dict()


def test_build_instagram_identity_trace_supports_url_and_handle_variants():
    trace = build_identity_resolution_trace("https://instagram.com/VersusGestao/", "instagram")

    assert trace.channel == "instagram"
    assert trace.supported_channel is True
    assert trace.matched is False
    assert trace.reason == "not_found"
    assert "versusgestao" in trace.variants
    assert "@versusgestao" in trace.variants


def test_build_identity_trace_marks_unsupported_channel():
    trace = build_identity_resolution_trace("abc", "sms")

    assert trace.supported_channel is False
    assert trace.strategy == "unsupported_channel"
    assert trace.reason == "unsupported_channel"
    assert trace.variants == ()


def test_resolve_user_identity_with_trace_uses_existing_resolver(monkeypatch):
    monkeypatch.setattr("src.intelligence.identity.resolve_user_identity", lambda identifier, channel: DummyUser())

    user, trace = resolve_user_identity_with_trace("5571996426565", "whatsapp")

    assert user.id == 42
    assert trace.matched is True
    assert trace.user_id == 42
    assert trace.reason == "matched_active_user"
