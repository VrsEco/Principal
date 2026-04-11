# Política de custo de inferência externa via MCP

## Diretriz
A Versus deve custodiar:

- segurança
- contratos
- ferramentas
- observabilidade
- governança operacional

A inferência intensiva pode ser executada:

- no runtime do cliente
- em agentes externos
- via integrações MCP aprovadas

## O que fica com a Versus
- API REST
- MCP Server
- autenticação
- RBAC
- filtros por `company_id`
- auditoria
- human gates
- ferramentas críticas

## O que pode ficar com o cliente
- modelo/família de LLM
- memória conversacional externa
- agentes privados
- copilots especializados
- custo de tokens de inferência avançada

## Regras
- Toda tool crítica precisa de contrato claro.
- Ações sensíveis exigem confirmação/human gate.
- Nunca expor acesso bruto irrestrito ao banco.
- Toda leitura e mutação precisa respeitar escopo tenant-safe.
- MCP externo só opera sobre surfaces aprovadas.

## Benefícios
- Redução do custo direto da Versus com IA
- Escalabilidade por cliente
- Menor acoplamento ao runtime interno
- Mais clareza entre plataforma e inferência
