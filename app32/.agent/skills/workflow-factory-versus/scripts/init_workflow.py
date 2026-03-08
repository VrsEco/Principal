from __future__ import annotations

import argparse
from pathlib import Path

SCHEMA_TEMPLATE = '''from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class {class_prefix}Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = "{action_key}"


class {class_prefix}Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class {class_prefix}Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str
'''

HANDLER_TEMPLATE = '''from __future__ import annotations

from typing import Callable

from ..schemas.{module} import {class_prefix}Input, {class_prefix}Request, {class_prefix}Result


class {class_prefix}ExecutionHandler:
    def __init__(
        self,
        *,
        execute_service: Callable[..., str],
    ):
        self._execute_service = execute_service

    def execute(self, request: {class_prefix}Request) -> {class_prefix}Result:
        _input = {class_prefix}Input()

        response_text = self._execute_service(
            action=_input.action,
            payload=dict(request.payload or {{}}),
            active_company_id=request.active_company_id,
            user_id=request.user_id,
            channel=request.channel,
        )
        return {class_prefix}Result(response_text=response_text)
'''

PRESENTER_TEMPLATE = '''from __future__ import annotations

from .channel_presenter import sanitize_for_channel
from .conversation_presenter import build_presenter_header


def build_{module}_response(*, title: str, body: str, channel: str) -> str:
    lines = build_presenter_header(title, channel=channel)
    lines.append(sanitize_for_channel(body, channel))
    return "\\n".join(lines)
'''

TEST_TEMPLATE = '''import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers.{module}_handler import {class_prefix}ExecutionHandler
from src.intelligence.workflows.schemas.{module} import {class_prefix}Request


def test_{module}_handler_formats_service_response():
    captured = {{}}

    def fake_execute_service(**kwargs):
        captured.update(kwargs)
        return "ok:{action_key}"

    handler = {class_prefix}ExecutionHandler(execute_service=fake_execute_service)
    result = handler.execute(
        {class_prefix}Request(
            payload={{"empresa": "AA"}},
            active_company_id=1,
            user_id=99,
            channel="whatsapp",
        )
    )

    assert captured["active_company_id"] == 1
    assert captured["user_id"] == 99
    assert captured["channel"] == "whatsapp"
    assert result.response_text == "ok:{action_key}"
'''

DOC_TEMPLATE = '''# Workflow {class_prefix}

## Objetivo
Descreva aqui o objetivo operacional do workflow `{action_key}`.

## Entradas esperadas
- empresa/contexto
- parametros do dominio

## Saida esperada
- resposta operacional clara
- presenter omnichannel quando aplicavel

## Checklist
- [ ] schema com `extra="forbid"`
- [ ] multi-tenancy
- [ ] policy/HITL avaliada
- [ ] testes minimos
- [ ] spec principal atualizada
'''


def write_file(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"Arquivo ja existe: {path}")
    path.write_text(content, encoding="utf-8")
    print(f"[created] {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold inicial de workflow V3 no padrao Versus.")
    parser.add_argument("--module", required=True, help="Nome do modulo em snake_case.")
    parser.add_argument("--class-prefix", required=True, help="Prefixo da classe em PascalCase.")
    parser.add_argument("--action-key", required=True, help="Action key canônica, ex.: collaborator.occupancy")
    parser.add_argument("--workflow-slug", required=True, help="Slug para o documento, ex.: collaborator-occupancy")
    parser.add_argument("--root", default=".", help="Raiz do workspace/app32")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    workflow_root = root / "src" / "intelligence" / "workflows"
    if not workflow_root.exists():
        raise SystemExit(f"Raiz invalida: {workflow_root} nao encontrado")

    mapping = {
        workflow_root / "schemas" / f"{args.module}.py": SCHEMA_TEMPLATE,
        workflow_root / "handlers" / f"{args.module}_handler.py": HANDLER_TEMPLATE,
        workflow_root / "presenters" / f"{args.module}_presenter.py": PRESENTER_TEMPLATE,
        root / "tests" / f"test_workflow_{args.module}_handler.py": TEST_TEMPLATE,
        root / "docs" / "specifications" / f"workflow_{args.workflow_slug}.md": DOC_TEMPLATE,
    }

    for path, template in mapping.items():
        content = template.format(
            module=args.module,
            class_prefix=args.class_prefix,
            action_key=args.action_key,
        )
        write_file(path, content, args.dry_run)

    print("\nProximos passos:")
    print("1. Ajustar schema/request/result ao dominio real.")
    print("2. Completar handler com dependencias explicitas e multi-tenancy.")
    print("3. Integrar presenter ao contrato omnichannel.")
    print("4. Exportar o modulo nos __init__.py relevantes.")
    print("5. Integrar no dispatcher/runtime/menu_engine quando aplicavel.")
    print("6. Atualizar docs/specifications/workflow_engine_v3.md e testes focados.")


if __name__ == "__main__":
    main()
