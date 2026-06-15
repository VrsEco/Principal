# SPEC — QA Autocoverage Human-like v1

## Decisão
O robô de testes deve evoluir de suítes manuais cadastradas para uma malha automática de contratos por tela, campo, ação, processamento, conexão e rollback.

## Escopo obrigatório
- **UI:** detectar telas, campos, botões, links, formulários, modais, abas e ações declaradas em templates.
- **API/MCP:** detectar rotas, endpoints, tools, schemas e permissões por surface.
- **Fluxos humanos:** abrir tela, preencher, salvar, reabrir, editar, processar, cancelar/desfazer e limpar massa.
- **Multi-tenancy:** toda mutação precisa ser executada com `company_id` explícito em tenant autorizado.
- **Evidência:** cada execução deve gerar manifesto com cobertura, lacunas, status e artefatos.
- **Autodrift:** qualquer elemento novo sem contrato deve aparecer automaticamente como pendência de cobertura.

## Estados de cobertura
- `discovered`: elemento existe, mas ainda não possui contrato.
- `contracted`: elemento possui contrato declarativo.
- `exercised`: elemento foi executado em teste recente.
- `transactional`: elemento foi executado com criação/alteração/processamento/reversão.
- `residue_zero`: elemento transacional concluiu com limpeza validada.

## Contrato mínimo por elemento UI
Cada item descoberto deve ter:
- `screen_id`
- `template`
- `route`, quando resolvível
- `element_type`
- `selector`
- `label`
- `action_kind`
- `requires_data`
- `requires_confirmation`
- `requires_cleanup`

## Evolução incremental
1. Scanner automático de UI.
2. Gerador de contratos UI human-like com estratégia de dados, risco, confirmação e rollback.
3. Comparador entre UI descoberta, contratos gerados e contratos já exercitados.
4. Geração assistida de testes.
5. Execução human-like com Playwright/API.
6. Gate de deploy por cobertura crítica.
7. Expansão para processamentos, gerações automáticas, conexões externas e rollback completo.

## Contrato gerado
Cada elemento UI descoberto deve gerar um contrato contendo:
- `contract_id` estável.
- `execution_strategy`.
- `data_strategy`.
- `risk_level`.
- `priority`.
- `confirmation_strategy`.
- `cleanup_strategy`.
- `requires_company_id`.
- `requires_human_gate`.

Contratos de alto risco podem ser inventariados e planejados automaticamente, mas só podem ser executados em `DEV_FULL` com tenant autorizado, confirmação explícita e rollback validável.

## Execução segura inicial
A primeira execução automática de contratos deve ser **não persistente**:
- abrir rotas autenticadas;
- validar HTML sem erro público;
- localizar campos, links e botões esperados;
- simular contratos de preenchimento como validação de presença/renderização;
- não submeter formulários;
- não executar contratos `requires_company_id`;
- não executar contratos `requires_human_gate`;
- não executar contratos com `cleanup_strategy=rollback_or_delete_and_residue_zero`.

A execução de mutações reais só pode ser liberada por lotes com teardown comprovado na empresa M1.

## Execução destrutiva controlada
A segunda camada de execução usa suítes transacionais reais, sempre em `DEV_FULL`, com:
- `E2E_COMPANY_ID` obrigatório;
- `E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true`;
- massa marcada por execução;
- criação, edição, processamento/cancelamento e exclusão/restauração;
- auditoria conservadora de resíduo por `company_id`;
- resumo operacional publicado na Central QA.

O relatório `devfull_transactional` deve evidenciar:
- suítes executadas/aprovadas/falhas;
- passos mutáveis aprovados por tipo (`create`, `update`, `process`, `cancel`, `delete`);
- passos de rollback/limpeza;
- `residue_total=0`.

Essa camada é permitida na empresa M1 - Testes Versus e continua bloqueada para tenants comuns sem autorização explícita.
