#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste completo de páginas principais.

Objetivo: garantir que as páginas básicas respondem e não retornam 5xx.
"""

import os
import sys
from typing import List, Tuple

import pytest
import requests

DEFAULT_BASE_URL = "http://127.0.0.1:5003"
BASE_URL = os.getenv("GV_BASE_URL", DEFAULT_BASE_URL)

PAGES = [
    ("/", "Home"),
    ("/login", "Login"),
    ("/main", "Main Menu"),
    ("/companies", "Empresas"),
    ("/pev/dashboard", "PEV Dashboard"),
    ("/grv/dashboard", "GRV Dashboard"),
    ("/configs", "Configurações"),
    ("/settings/reports", "Relatórios"),
    ("/integrations", "Integrações"),
    ("/configs/ai", "AI Config"),
]


def _check_server_up(base_url: str) -> bool:
    """Retorna True se o host estiver respondendo."""
    try:
        requests.get(base_url, timeout=5)
        return True
    except requests.RequestException:
        return False


def _exercise_pages(base_url: str) -> Tuple[int, List[str], List[str]]:
    """Executa requisições GET e separa avisos/erros."""
    ok = 0
    warnings: List[str] = []
    errors: List[str] = []

    for path, name in PAGES:
        try:
            resp = requests.get(base_url + path, timeout=5, allow_redirects=False)
        except requests.RequestException as exc:
            errors.append(f"{name}: conexão falhou ({exc})")
            continue

        status = resp.status_code
        if status in (200, 302):
            ok += 1
        elif status >= 500:
            errors.append(f"{name}: status {status}")
        else:
            warnings.append(f"{name}: status {status}")

    return ok, warnings, errors


def _print_summary(ok: int, warnings: List[str], errors: List[str]) -> None:
    separator = "=" * 80
    print(separator)
    print("TESTE COMPLETO DE PÁGINAS - PostgreSQL")
    print(separator)

    for msg in errors:
        print(f" ERRO: {msg}")
    for msg in warnings:
        print(f" WARN: {msg}")

    print("\n" + separator)
    print(f"RESUMO: {ok} OK | {len(warnings)} Avisos | {len(errors)} Erros")
    print(separator)


@pytest.mark.allpages
def test_all_pages_complete():
    """Falha apenas se houver 5xx ou conexão recusada."""
    if not _check_server_up(BASE_URL):
        pytest.skip(f"Servidor não está escutando em {BASE_URL}")

    ok, warnings, errors = _exercise_pages(BASE_URL)
    _print_summary(ok, warnings, errors)

    if errors:
        details = "\n".join(errors[:5])
        pytest.fail(f"{len(errors)} página(s) com erro:\n{details}")


if __name__ == "__main__":
    ok_count, warn_list, error_list = _exercise_pages(BASE_URL)
    _print_summary(ok_count, warn_list, error_list)
    sys.exit(0 if not error_list else 1)
