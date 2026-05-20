# Catálogo Sistêmico RBAC v1

Catálogo canônico usado pela matriz de autorizações em árvore dos cargos.

## Princípios

- multi-tenancy sempre escopado por `company_id`
- matriz única para módulos, telas, APIs REST e tools MCP
- compatível com o payload legado `Role.permissions`
- ações especiais suportadas: `configure`, `execute`, `grant`, `audit`

## Domínios cobertos

1. `auth`
2. `companies`
3. `projects`
4. `processes`
5. `plans`
6. `indicators`
7. `okrs`
8. `my_work`
9. `contracts`
10. `financial`
11. `incentives`
12. `operations`
13. `agents`
14. `mcp`
15. `integrations`

## Superfícies cobertas

- telas web
- funcionalidades internas
- famílias de API REST
- tools MCP
- webhooks e runtimes operacionais

## Presets de autorização

- presets do sistema continuam servindo como baseline reutilizável
- presets customizados podem ser salvos por empresa, sempre escopados por `company_id`
- o catálogo entregue para a UI combina:
  - `preset_groups.system`
  - `preset_groups.company`
  - lista consolidada em `presets`
- presets customizados reutilizam a mesma normalização do payload RBAC canônico

## Fonte de verdade

- serviço: `C:\GestaoVersus\app32\app32\services\rbac_permission_catalog_service.py`
- UI de gestão: `C:\GestaoVersus\app32\app32\templates\modules\companies\company_form_v2.html`
