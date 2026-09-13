#!/usr/bin/env python3
"""Obtencao local e unica do refresh token do Google Drive.

Execute em uma estacao confiavel, nunca no Configr. O navegador abre uma tela
do Google para que o proprietario da conta aprove o escopo minimo ``drive.file``.
O token retornado deve ser provisionado no Configr somente por canal SSH seguro.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests


AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPE = "https://www.googleapis.com/auth/drive.file"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-id", default=os.getenv("GV_GOOGLE_DRIVE_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("GV_GOOGLE_DRIVE_CLIENT_SECRET"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.client_id or not args.client_secret:
        raise SystemExit("Defina GV_GOOGLE_DRIVE_CLIENT_ID e GV_GOOGLE_DRIVE_CLIENT_SECRET fora do Git.")

    redirect_uri = f"http://127.0.0.1:{args.port}/oauth2callback"
    state = secrets.token_urlsafe(32)
    result: dict[str, str] = {}
    received = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - assinatura do stdlib
            query = parse_qs(urlparse(self.path).query)
            if query.get("state", [""])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Estado OAuth invalido.")
                return
            result["code"] = query.get("code", [""])[0]
            result["error"] = query.get("error", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Autorizacao recebida. Voce pode fechar esta aba.")
            received.set()

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", args.port), CallbackHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    authorization_params = {
        "client_id": args.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": DEFAULT_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    authorization_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(authorization_params)}"
    print(json.dumps({"authorization_url": authorization_url, "expires_in_seconds": args.timeout}))
    webbrowser.open(authorization_url)

    deadline = time.monotonic() + args.timeout
    while not received.wait(timeout=1):
        if time.monotonic() >= deadline:
            server.shutdown()
            raise SystemExit("Tempo de autorizacao OAuth esgotado.")
    server.shutdown()
    if result.get("error") or not result.get("code"):
        raise SystemExit(f"Autorizacao OAuth recusada: {result.get('error') or 'sem codigo'}")

    token_response = requests.post(
        TOKEN_ENDPOINT,
        data={
            "code": result["code"],
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    token_response.raise_for_status()
    refresh_token = token_response.json().get("refresh_token")
    if not refresh_token:
        raise SystemExit("Google nao retornou refresh token; revogue o app e tente novamente.")
    print(json.dumps({"ok": True, "refresh_token": refresh_token}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
