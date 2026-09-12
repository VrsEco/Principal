from scripts.verify_password_reset_release import validate_public_base_url, validate_secret_key


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
