"""Limite de tamanho das respostas das tools publicadas no mcp-versus.

Respostas muito grandes estouram o limite do cliente de IA (ex.: o inventário de
tarefas da jornada devolveu 135 mil caracteres) e consomem contexto à toa. Este
guarda só atua quando a resposta passa do limite: corta as maiores listas, mantém
o restante intacto e informa de forma explícita o que foi cortado em
``_truncation``. Não altera as tools nem o que elas calculam; é pós-processamento.
"""
from __future__ import annotations

import functools
import inspect
import json
import os
from typing import Any, Callable

DEFAULT_MAX_CHARS = 60_000
MIN_MAX_CHARS = 5_000
_MAX_STRING = 2_000
_HINT = (
    "Resposta reduzida para caber no limite do cliente. Refine com filtros "
    "(employee_id, department, anchor_date, scope, período) para obter o detalhe."
)


def max_response_chars() -> int:
    raw = os.getenv("MCP_VERSUS_MAX_RESPONSE_CHARS", "").strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_CHARS
    return value if value >= MIN_MAX_CHARS else DEFAULT_MAX_CHARS


def _size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str))


def _collect_lists(node: Any, path: str, out: list[tuple[str, list]]) -> None:
    if isinstance(node, dict):
        for key, child in node.items():
            _collect_lists(child, f"{path}.{key}" if path else str(key), out)
    elif isinstance(node, list):
        if len(node) > 1:
            out.append((path or "$", node))
        for index, child in enumerate(node[:5]):  # caminho representativo; evita explosão
            _collect_lists(child, f"{path}[{index}]", out)


def _shorten_strings(node: Any) -> Any:
    if isinstance(node, dict):
        return {key: _shorten_strings(child) for key, child in node.items()}
    if isinstance(node, list):
        return [_shorten_strings(child) for child in node]
    if isinstance(node, str) and len(node) > _MAX_STRING:
        return node[:_MAX_STRING] + "…"
    return node


def limit_mcp_payload(result: Any, *, max_chars: int | None = None) -> Any:
    """Devolve ``result`` intacto se couber; senão, uma versão reduzida e marcada."""
    limit = max_chars if (max_chars and max_chars >= MIN_MAX_CHARS) else max_response_chars()
    try:
        original = _size(result)
        if original <= limit or not isinstance(result, (dict, list)):
            return result

        # Normaliza tipos não serializáveis (datas etc.) só quando vai reduzir.
        work: Any = json.loads(json.dumps(result, ensure_ascii=False, default=str))
        wrapped = isinstance(work, list)
        if wrapped:
            work = {"items": work}

        cut: dict[str, dict[str, Any]] = {}
        for _ in range(500):
            if _size(work) + 600 <= limit:  # folga para o bloco _truncation
                break
            candidates: list[tuple[str, list]] = []
            _collect_lists(work, "", candidates)
            candidates = [(p, lst) for p, lst in candidates if len(lst) > 1]
            if not candidates:
                work = _shorten_strings(work)
                break
            path, target = max(candidates, key=lambda item: _size(item[1]))
            total = cut.get(path, {}).get("total", len(target))
            keep = max(1, len(target) // 2)
            del target[keep:]
            cut[path] = {"path": path, "total": total, "kept": keep}

        work["_truncation"] = {
            "truncated": True,
            "original_chars": original,
            "max_chars": limit,
            "lists": sorted(cut.values(), key=lambda item: item["path"]),
            "hint": _HINT,
        }
        return work
    except Exception:  # o guarda nunca pode quebrar uma resposta válida
        return result


def guard_tool_callable(func: Callable[..., Any], guard: Callable[[Any], Any] = limit_mcp_payload) -> Callable[..., Any]:
    """Envolve uma tool preservando assinatura (o FastMCP deriva o esquema dela)."""
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def _async_guarded(*args: Any, **kwargs: Any) -> Any:
            return guard(await func(*args, **kwargs))

        _async_guarded.__app32_result_guarded__ = True  # type: ignore[attr-defined]
        return _async_guarded

    @functools.wraps(func)
    def _guarded(*args: Any, **kwargs: Any) -> Any:
        return guard(func(*args, **kwargs))

    _guarded.__app32_result_guarded__ = True  # type: ignore[attr-defined]
    return _guarded
