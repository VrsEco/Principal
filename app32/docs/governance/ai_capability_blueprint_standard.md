# Padrão Canônico de Capability IA/Automação — APP32

Este documento formaliza o **contrato padrão de capability** do APP32 para que toda automação ou conexão com IA nasça com a mesma estrutura mínima.

## Estrutura mínima

1. **Schema**
   - Entrada validada por Pydantic.
   - `extra="forbid"`.
2. **Service**
   - Regra determinística.
   - Tenant scope obrigatório por `company_id`.
3. **Tool / Contrato**
   - Nome canônico da capability.
   - Contrato explícito para uso interno/externo.
4. **REST / MCP**
   - Exposição controlada quando a capability for estável.
5. **Workflow**
   - Orquestração conversacional/assistida quando houver jornada.
6. **UI / Sapiens**
   - Entrada operacional clara quando houver uso humano recorrente.
7. **Governança**
   - RBAC, audit trail e human gate quando aplicável.
8. **Teste + documentação**
   - Smoke, contrato e especificação operacional.

## Readiness mínimo

- schema publicado
- service publicado
- audit trail definido
- tenant scope validado
- RBAC/human gate classificado
- testes mínimos executados
- documentação da capability registrada

## Uso recomendado

- Inventário unificado de capabilities: `/ai-capability-inventory`
- Sapiens Factory: `/ai/factory`
- Malha de automações: `/ai-automation-mesh`
