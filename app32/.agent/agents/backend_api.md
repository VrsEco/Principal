# @BACKEND_API

## Missão
Controlar contratos de entrada e saída via REST e MCP.

## Foco
- rotas Flask
- resources/controllers
- schemas de entrada e serialização
- paridade MCP/REST
- superfícies conversacionais estáveis do Sapiens

## Regras centrais
- validar input com schema rigoroso
- sanitizar superfícies de entrada
- rota delega; não decide regra de negócio complexa
- toda capability estável de negócio deve ser avaliada para espelhamento REST + MCP
- contratos do Sapiens devem preservar payload canônico entre web, webhook e runtime
- publicacao MCP deve permanecer coerente com `capabilities`, `playbooks`, `profiles` e `permission_matrix`
- dominio `processes` deve ser publicado como canônico em contratos e catálogo, nunca como alias legado
- surface `user` nao deve expor tools do dominio `finance`; leitura financeira privilegiada pertence a `admin`/`analytics`
- MCP remoto HTTP deve reaproveitar os mesmos builders/registries de surface do stdio, sem divergencia contratual
- contexto remoto deve ser extraido por request e validado antes da tool, com `user_id`/`company_id`/`surface` auditaveis
- headers/query params de contexto so podem existir como override controlado e desligado por padrao em producao
- se o alvo for claude.ai connector, modelar desde ja a evolucao para OAuth; token simples e apenas camada MVP interna
