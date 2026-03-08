# Checklist de Workflow V3

## 1. Classificacao
- O fluxo e consulta, mutacao ou wizard?
- Existe acao sensivel que exige HITL?
- O mesmo fluxo atende Web, WhatsApp, Instagram e Telegram?

## 2. Modelagem
- Criou schema Pydantic com `ConfigDict(extra="forbid")`?
- O schema tem nomes de campos canônicos?
- O handler recebe dependencias explicitas via construtor?
- O presenter ficou puro, sem query de banco?

## 3. Seguranca
- Toda query/lookup valida `company_id`?
- IDs foram resolvidos com escopo do tenant?
- Ha necessidade de `policy.py` / approval workflow?
- O fluxo evita `os.environ` e usa contexto explicitamente?

## 4. Integracao
- Exportou no `schemas/__init__.py`?
- Exportou no `handlers/__init__.py`?
- Atualizou `presenters/__init__.py`, se aplicavel?
- Registrou no dispatcher/runtime/menu adapter, se necessario?
- Atualizou a spec em `docs/specifications/workflow_engine_v3.md`?

## 5. Governanca
- O fluxo pode virar endpoint REST?
- O fluxo deve ser espelhado via MCP?
- O uso sera capturado no ledger de workflow usage?
- O gap radar deve reconhecer esse novo fluxo no futuro?

## 6. Testes
- Teste de sucesso principal
- Teste de input invalido
- Teste de escopo/empresa
- Teste de presenter por canal
- Teste de policy/HITL quando sensivel
