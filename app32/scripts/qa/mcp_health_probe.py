"""Sonda externa de saúde do mcp-versus (somente leitura; não usa credenciais).

Uso:
    python scripts/qa/mcp_health_probe.py                       # produção (https://app.gestaoversus.com.br)
    python scripts/qa/mcp_health_probe.py --base https://host   # outro ambiente
    python scripts/qa/mcp_health_probe.py --json                # saída para scheduler/monitor
    python scripts/qa/mcp_health_probe.py --log logs/mcp_http_stderr.log --minutes 60   # no servidor: erros no log

Saída: código 0 = saudável, 1 = degradado (lento ou aviso no log), 2 = falha.
O que checa:
  1. /mcp/healthz responde 200 e dentro do limite de tempo;
  2. a descoberta OAuth (protected-resource/mcp/pilot) responde, aponta o servidor de autorização e anuncia os
     escopos base (mcp:access, mcp:user); 2b. o provedor de identidade (Keycloak) responde à própria descoberta;
  3. o endpoint MCP sem token responde 401 (o MCP exige autenticação; 5xx/timeout = problema);
  4. (opcional, no servidor) quantos avisos "permission discovery failed" / OperationalError / Traceback
     apareceram no log nos últimos N minutos (sintoma de "0 ferramentas").
Não valida a lista de ferramentas (isso exige token); para isso use list_user_app32_capabilities autenticado.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

DEFAULT_BASE = "https://app.gestaoversus.com.br"
SLOW_SECONDS = 3.0
FAIL_SECONDS = 10.0
LOG_PATTERNS = {
    "permission_discovery_failed": re.compile(r"permission discovery failed"),
    "operational_error": re.compile(r"OperationalError"),
    "traceback": re.compile(r"Traceback \(most recent call last\)"),
}


@dataclass
class Check:
    name: str
    status: str  # ok | slow | fail
    detail: str
    seconds: float | None = None


@dataclass
class Report:
    base: str
    checks: list[Check] = field(default_factory=list)
    log_counts: dict[str, int] | None = None

    @property
    def exit_code(self) -> int:
        if any(check.status == "fail" for check in self.checks):
            return 2
        if any(check.status == "slow" for check in self.checks):
            return 1
        if self.log_counts and (self.log_counts.get("permission_discovery_failed") or self.log_counts.get("operational_error")):
            return 1
        return 0


Fetcher = Callable[[str, float], tuple[int, bytes, float]]


def _fetch(url: str, timeout: float) -> tuple[int, bytes, float]:
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):  # noqa: D401
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "mcp-health-probe/1"})
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read(65536), time.monotonic() - started
    except urllib.error.HTTPError as error:
        return error.code, error.read(65536) if error.fp else b"", time.monotonic() - started


def _timed_status(seconds: float, ok: bool) -> str:
    if not ok or seconds >= FAIL_SECONDS:
        return "fail"
    return "slow" if seconds >= SLOW_SECONDS else "ok"


def run_checks(base: str, fetch: Fetcher = _fetch) -> list[Check]:
    base = base.rstrip("/")
    checks: list[Check] = []

    def safe(url: str) -> tuple[int | None, bytes, float | None, str | None]:
        try:
            status, body, seconds = fetch(url, FAIL_SECONDS)
            return status, body, seconds, None
        except Exception as exc:  # timeout, DNS, TLS
            return None, b"", None, type(exc).__name__

    status, _body, seconds, error = safe(f"{base}/mcp/healthz")
    if error:
        checks.append(Check("healthz", "fail", f"sem resposta ({error})"))
    else:
        checks.append(Check("healthz", _timed_status(seconds or 0, status == 200), f"HTTP {status}", seconds))

    status, body, seconds, error = safe(f"{base}/.well-known/oauth-protected-resource/mcp/pilot")
    authorization_server = None
    if error:
        checks.append(Check("oauth_discovery", "fail", f"sem resposta ({error})"))
    else:
        scopes: list[str] = []
        if status == 200:
            try:
                metadata = json.loads(body.decode("utf-8", "ignore"))
                servers = metadata.get("authorization_servers") or []
                authorization_server = servers[0] if servers else None
                scopes = list(metadata.get("scopes_supported") or [])
            except ValueError:
                authorization_server = None
        has_base_scopes = {"mcp:access", "mcp:user"} <= set(scopes)
        checks.append(
            Check(
                "oauth_discovery",
                _timed_status(seconds or 0, status == 200 and bool(authorization_server) and has_base_scopes),
                f"HTTP {status}, servidor de autorização={'sim' if authorization_server else 'não'}, "
                f"escopos base={'ok' if has_base_scopes else 'ausentes'}",
                seconds,
            )
        )

    if authorization_server:
        status, body, seconds, error = safe(f"{authorization_server.rstrip('/')}/.well-known/openid-configuration")
        if error:
            checks.append(Check("idp_discovery", "fail", f"sem resposta ({error})"))
        else:
            has_token_endpoint = False
            if status == 200:
                try:
                    has_token_endpoint = bool(json.loads(body.decode("utf-8", "ignore")).get("token_endpoint"))
                except ValueError:
                    has_token_endpoint = False
            checks.append(
                Check(
                    "idp_discovery",
                    _timed_status(seconds or 0, status == 200 and has_token_endpoint),
                    f"HTTP {status}, token_endpoint={'sim' if has_token_endpoint else 'não'}",
                    seconds,
                )
            )

    status, _body, seconds, error = safe(f"{base}/mcp/pilot/")
    if error:
        checks.append(Check("mcp_requires_auth", "fail", f"sem resposta ({error})"))
    else:
        checks.append(
            Check(
                "mcp_requires_auth",
                _timed_status(seconds or 0, status in (401, 403, 405)),
                f"HTTP {status} (esperado 401 sem token)",
                seconds,
            )
        )
    return checks


def scan_log(path: Path, minutes: int, now: datetime | None = None) -> dict[str, int]:
    """Conta sintomas no log do MCP nas últimas ``minutes`` (linhas sem data entram: o log é do processo atual)."""
    counts = {name: 0 for name in LOG_PATTERNS}
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(minutes=minutes)
    stamp = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})")
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = stamp.search(line)
        if match:
            try:
                when = datetime.fromisoformat(f"{match.group(1)}T{match.group(2)}").replace(tzinfo=timezone.utc)
            except ValueError:
                when = None
            if when is not None and when < cutoff:
                continue
        for name, pattern in LOG_PATTERNS.items():
            if pattern.search(line):
                counts[name] += 1
    return counts


def render(report: Report) -> str:
    lines = [f"mcp-versus: {report.base}"]
    for check in report.checks:
        timing = f" ({check.seconds:.2f}s)" if check.seconds is not None else ""
        lines.append(f"  [{check.status.upper():4}] {check.name}: {check.detail}{timing}")
    if report.log_counts is not None:
        lines.append("  log: " + ", ".join(f"{name}={count}" for name, count in report.log_counts.items()))
    lines.append({0: "RESULTADO: saudável", 1: "RESULTADO: degradado", 2: "RESULTADO: FALHA"}[report.exit_code])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--minutes", type=int, default=60)
    args = parser.parse_args(argv)

    report = Report(base=args.base, checks=run_checks(args.base))
    if args.log is not None:
        report.log_counts = scan_log(args.log, args.minutes)
    if args.json:
        print(json.dumps({**asdict(report), "exit_code": report.exit_code}, ensure_ascii=False))
    else:
        print(render(report))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
