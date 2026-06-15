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
2. Comparador entre UI descoberta e contratos existentes.
3. Geração assistida de testes.
4. Execução human-like com Playwright/API.
5. Gate de deploy por cobertura crítica.
6. Expansão para processamentos, gerações automáticas, conexões externas e rollback completo.
