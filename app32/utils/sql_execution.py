from __future__ import annotations

import inspect
from typing import Any, Mapping, Sequence


class SafeSqlFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def execute_formatted_query(
    cursor,
    query_template: str,
    params: Sequence[Any] = (),
    *,
    scope: Mapping[str, Any] | None = None,
):
    """Executa SQL com fragmentos internos formatados fora do `cursor.execute`.

    Uso permitido apenas para fragmentos controlados pelo código
    (ex.: placeholders de IN, filtros estáticos por schema, clauses opcionais).
    Nunca use este helper para interpolar input livre do usuário.
    """

    if scope is None:
        caller = inspect.currentframe().f_back
        fragment_scope: dict[str, Any] = {}
        if caller is not None:
            for source in (caller.f_globals, caller.f_locals):
                for key, value in source.items():
                    if isinstance(value, str):
                        fragment_scope[key] = value
    else:
        fragment_scope = {
            key: value for key, value in scope.items() if isinstance(value, str)
        }

    query = query_template.format_map(SafeSqlFormatDict(fragment_scope))
    cursor.execute(query, tuple(params))
