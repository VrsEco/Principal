"""Preflight seguro da release de redefinição de senha.

Executar no ambiente-alvo, após ``flask db upgrade`` e antes de liberar o
tráfego. O comando apenas lê configuração e schema: não envia e-mails, não
emite tokens e nunca imprime segredos.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


PASSWORD_RESET_REVISION = "20260912_1700"
PASSWORD_RESET_COLUMNS = {
    "id",
    "user_id",
    "token_hash",
    "requested_ip_hash",
    "expires_at",
    "used_at",
    "created_at",
}


# Ao executar ``python scripts/arquivo.py``, o Python inclui apenas ``scripts``
# no início do import path. O projeto Flask, porém, começa no diretório pai.
APP_ROOT = Path(__file__).resolve().parents[1]


def ensure_app_root_on_path(path: list[str] | None = None) -> None:
    """Garante que o diretório do APP32 seja importável em execução direta."""
    search_path = sys.path if path is None else path
    root = str(APP_ROOT)
    if root not in search_path:
        search_path.insert(0, root)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool


def validate_public_base_url(value: str | None) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password


def validate_secret_key(value: str | None) -> bool:
    normalized = str(value or "").strip()
    unsafe_markers = ("change-me", "changeme", "dev-secret", "default-secret", "test-secret")
    return len(normalized) >= 32 and not any(marker in normalized.lower() for marker in unsafe_markers)


def _email_delivery_is_configured(email_service) -> bool:
    """Checa somente presença de configuração; não conecta ao provedor."""
    email_service._reload_runtime_config()
    provider = str(email_service.provider or "").strip().lower()
    if provider == "smtp":
        return all(
            (
                email_service.smtp_server,
                email_service.smtp_username,
                email_service.smtp_secret,
                email_service.default_sender,
            )
        )
    if provider == "webhook":
        return bool(email_service.webhook_url)
    return False


def run_preflight(*, production: bool, environ: Mapping[str, str] | None = None) -> list[CheckResult]:
    """Executa validações sem revelar valores operacionais."""
    # Imports tardios evitam carregar a aplicação ao testar validadores puros.
    ensure_app_root_on_path()
    from app import create_app
    from models import db
    from services.email_service import email_service
    from sqlalchemy import inspect, text

    app = create_app("production" if production else None)

    # A aplicação carrega o dotenv antes de lermos o ambiente efetivo.
    env = os.environ if environ is None else environ
    results = [
        CheckResult("APP32_PUBLIC_BASE_URL_HTTPS", validate_public_base_url(env.get("APP32_PUBLIC_BASE_URL"))),
    ]

    with app.app_context():
        results.append(CheckResult("SECRET_KEY_FORTE", validate_secret_key(app.config.get("SECRET_KEY"))))

        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        has_table = "password_reset_tokens" in tables
        results.append(CheckResult("TABELA_PASSWORD_RESET_TOKENS", has_table))
        if has_table:
            columns = {column["name"] for column in inspector.get_columns("password_reset_tokens")}
            results.append(CheckResult("COLUNAS_PASSWORD_RESET_TOKENS", PASSWORD_RESET_COLUMNS.issubset(columns)))

        try:
            revisions = set(db.session.execute(text("SELECT version_num FROM alembic_version")).scalars())
        except Exception:
            revisions = set()
        results.append(CheckResult("MIGRATION_PASSWORD_RESET", PASSWORD_RESET_REVISION in revisions))

        response = app.test_client().get("/password-reset")
        results.append(CheckResult("ROTA_PUBLICA_PASSWORD_RESET", response.status_code == 200))

        if production:
            try:
                email_ok = _email_delivery_is_configured(email_service)
            except Exception:
                email_ok = False
            results.append(CheckResult("ENTREGA_DE_EMAIL_CONFIGURADA", email_ok))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida a release de redefinição de senha sem expor segredos.")
    parser.add_argument("--production", action="store_true", help="Exige um transporte de e-mail configurado.")
    args = parser.parse_args()

    results = run_preflight(production=args.production)
    for result in results:
        print(f"{'OK' if result.ok else 'FALHOU'} {result.name}")
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
