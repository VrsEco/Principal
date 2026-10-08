"""Contrato do glossário oficial do mcp-versus (SPEC glossario_mcp_versus_v1, T1).

Nas superfícies que o usuário vê (instaladores, geradores de comando/instrução e
console MCP) o conector se chama apenas ``mcp-versus``. Nomes antigos
(``sapiens-user``, ``app32-user|admin|analytics|ops``, ``pilot``) já existem em
alguns arquivos; a linha de base abaixo funciona como catraca: o número **não
pode aumentar** e, ao corrigir um uso, a linha de base deve ser reduzida.
"""
from __future__ import annotations

import re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN = {
    "sapiens-conector": re.compile(r"sapiens-(user|admin|analytics|finance)\b", re.IGNORECASE),
    "app32-surface": re.compile(r"app32-(user|admin|analytics|ops)\b", re.IGNORECASE),
    "pilot": re.compile(r"\b(pilot|piloto)\b", re.IGNORECASE),
}

SCOPE_FILES = (
    "services/mcp_versus_oauth_connector_service.py",
    "services/mcp_oauth_codex_connector_service.py",
    "services/user_mcp_token_service.py",
)
SCOPE_GLOBS = (
    "scripts/installers/*",
    "templates/**/*mcp*",
    "templates/**/*connect*",
)

# Linha de base em 2026-10-08 (main aceeb2863 + PR #110/#111). Só pode diminuir.
BASELINE = {
    ("scripts/installers/install-claude-sapiens-slash-commands.ps1", "sapiens-conector"): 1,
    ("scripts/installers/install-sapiens-antigravity-online.ps1", "sapiens-conector"): 1,
    ("scripts/installers/install-sapiens-runtime.ps1", "sapiens-conector"): 1,
    ("services/mcp_oauth_codex_connector_service.py", "pilot"): 2,
    ("services/mcp_versus_oauth_connector_service.py", "pilot"): 3,
    ("services/user_mcp_token_service.py", "sapiens-conector"): 5,
    ("templates/modules/operations/ai_mcp_console.html", "pilot"): 5,
}


def _scoped_files() -> list[str]:
    found = {f for f in SCOPE_FILES if (APP_ROOT / f).is_file()}
    for pattern in SCOPE_GLOBS:
        for path in APP_ROOT.glob(pattern):
            if path.is_file():
                found.add(path.relative_to(APP_ROOT).as_posix())
    return sorted(found)


def _counts() -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for rel in _scoped_files():
        text = (APP_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        for name, pattern in FORBIDDEN.items():
            n = len(pattern.findall(text))
            if n:
                counts[(rel, name)] = n
    return counts


def test_scope_is_not_silently_empty():
    files = _scoped_files()
    assert len(files) >= 8, f"escopo do glossário encolheu sem aviso: {files}"
    assert "services/mcp_versus_oauth_connector_service.py" in files


def test_canonical_connector_name_is_mcp_versus():
    text = (APP_ROOT / "services/mcp_versus_oauth_connector_service.py").read_text(encoding="utf-8")
    assert re.search(r'MCP_VERSUS_NAME[^=\n]*=\s*"mcp-versus"', text), (
        "O nome canônico do conector deve ser 'mcp-versus' (SPEC glossario_mcp_versus_v1)."
    )
    codex = (APP_ROOT / "services/mcp_oauth_codex_connector_service.py").read_text(encoding="utf-8")
    assert 'server_name = "mcp-versus"' in codex, "O Codex deve cair no nome canônico 'mcp-versus'."


def test_legacy_names_never_increase_in_user_facing_files():
    offenders = []
    for key, n in sorted(_counts().items()):
        allowed = BASELINE.get(key, 0)
        if n > allowed:
            rel, name = key
            offenders.append(f"{rel}: '{name}' {n} ocorrência(s), linha de base {allowed}")
    assert not offenders, (
        "Nome fora do glossário em superfície voltada ao usuário. Use 'mcp-versus' "
        "(docs/spec/glossario_mcp_versus_v1.md):\n  " + "\n  ".join(offenders)
    )


def test_baseline_is_tight_so_it_only_shrinks():
    counts = _counts()
    stale = []
    for key, allowed in sorted(BASELINE.items()):
        n = counts.get(key, 0)
        if n < allowed:
            stale.append(f"{key[0]}: '{key[1]}' agora {n}, linha de base {allowed}")
    assert not stale, (
        "Uso legado reduzido: atualize BASELINE em tests/test_mcp_glossary_contract.py "
        "para travar o ganho:\n  " + "\n  ".join(stale)
    )
