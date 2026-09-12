from scripts import verify_password_reset_release as preflight
from scripts.verify_password_reset_release import validate_public_base_url, validate_secret_key


def test_preflight_adds_app_root_when_executed_as_a_script():
    path = ["/runtime/app32/scripts"]

    preflight.ensure_app_root_on_path(path)

    assert path[0] == str(preflight.APP_ROOT)
    assert path.count(str(preflight.APP_ROOT)) == 1


def test_preflight_builds_the_flask_application_via_factory():
    content = preflight.Path(preflight.__file__).read_text(encoding="utf-8")

    assert "from app import create_app" in content
    assert 'create_app("production" if production else None)' in content


def test_public_base_url_requires_https_without_embedded_credentials():
    assert validate_public_base_url("https://app.gestaoversus.com.br")
    assert not validate_public_base_url("http://app.gestaoversus.com.br")
    assert not validate_public_base_url("https://user:pass@app.gestaoversus.com.br")
    assert not validate_public_base_url(None)


def test_secret_key_requires_non_default_value_with_minimum_length():
    assert validate_secret_key("a" * 32)
    assert not validate_secret_key("short")
    assert not validate_secret_key("dev-secret-" + ("a" * 40))
    assert not validate_secret_key(None)
