# Blueprint de Workflow V3

## Estrutura recomendada

### Schemas
- Arquivo: `src/intelligence/workflows/schemas/<modulo>.py`
- Conteudo comum:
  - `Input`
  - `Request`
  - `Result`
  - factories `build_from_action(...)` quando houver familia de acoes

### Handlers
- Arquivo: `src/intelligence/workflows/handlers/<modulo>_handler.py`
- Regras:
  - dependencias injetadas no construtor
  - `execute(...)` deterministico
  - retorno via `Result`
  - mensagens de erro claras e operacionais

### Presenters
- Arquivo: `src/intelligence/workflows/presenters/<modulo>_presenter.py`
- Regras:
  - nao acessar banco
  - adaptar saida por canal/familia de canal
  - reaproveitar `channel_presenter.py` e `conversation_presenter.py`

### Testes
- Arquivo: `tests/test_workflow_<modulo>_handler.py`
- Priorizar dublês simples e asserts operacionais

## Camada adicional para Sapiens
Quando o fluxo tambem for conversacional no Sapiens, acrescentar:
1. intenção canônica
2. regra de roteamento workflow-first
3. hidratação de contexto de sessão/canal
4. política de confirmação
5. regra de desambiguação de contexto
6. fallback explícito para LLM apenas se necessário

## Decisao de integracao
- **Consulta direta**: integrar em handler + presenter + dispatcher
- **Wizard**: integrar em coordinator + session runtime + presenter
- **Acao sensivel**: integrar tambem em `policy.py` e approval flow
- **Descoberta implicita**: enriquecer `keywords`, `intent_examples` e catalogo
- **Sapiens operacional**: alinhar com `sapiens-workflow-first`

## Padrao de nomes
- modulo: `snake_case`
- class prefix: `PascalCase`
- action key: `dominio.acao`
- teste: `test_workflow_<modulo>_handler.py`

## Atualizacoes frequentes
- `src/intelligence/workflows/__init__.py`
- `src/intelligence/workflows/direct_execution.py`
- `src/intelligence/workflows/registry.py`
- `src/intelligence/menu_engine.py`
- `docs/specifications/workflow_engine_v3.md`
