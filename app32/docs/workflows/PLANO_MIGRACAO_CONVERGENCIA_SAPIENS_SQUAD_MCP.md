# Plano de migração — Convergência Sapiens + Squad + MCP

## Fase 1 — Inventário
- Mapear `/agents/*`
- Classificar: hub, wrapper, onboarding, legado
- Definir destino canônico por rota

## Fase 2 — Wrapper-first
- Manter URLs antigas
- Transformar superfícies de domínio em wrappers do Sapiens
- Injetar contexto por querystring/preset controlado

## Fase 3 — Tool-first
- Extrair capacidades para services
- Espelhar em REST
- Espelhar em MCP

## Fase 4 — Onboarding canônico
- Consolidar `/companies/new` como rota principal
- Manter `/agents/cadastro` como espelho/controlador temporário
- Eliminar divergência semântica entre agente e wizard

## Fase 5 — Desativação gradual
- Avisos de convergência
- Redirecionamentos suaves
- Remoção das telas-agente sem lógica própria

## Critérios de pronto
- Sapiens operando como hub
- Squad como hub técnico
- Domínios relevantes cobertos por tools
- Smokes de navegação e chat aprovados
- Contratos REST + MCP documentados
