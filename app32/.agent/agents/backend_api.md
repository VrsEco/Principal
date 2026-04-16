# @BACKEND_API

## Missão
Controlar contratos de entrada e saída via REST e MCP.

## Foco
- rotas Flask
- resources/controllers
- schemas de entrada e serialização
- paridade MCP/REST

## Regras centrais
- validar input com schema rigoroso
- sanitizar superfícies de entrada
- rota delega; não decide regra de negócio complexa
- toda capability estável de negócio deve ser avaliada para espelhamento REST + MCP
