# Paper — Roadmap de Capabilities MCP do Domínio Comercial v1

## Contexto
- Origem: smoke completo M1 (`company_id=10`) em `2026-05-16`.
- Achado: o pilar Comercial está operacional na surface `user`, mas a cobertura atual depende de entidades genéricas:
  - `list_process_hierarchy`
  - `list_project_tasks_secure`
  - `create_project_task_secure`
- Não foram identificadas capabilities comerciais canônicas para:
  - pipeline
  - CRM/oportunidades
  - propostas
  - contratos comerciais

## Leitura arquitetural
Hoje o APP32 consegue sustentar parte do fluxo comercial via:
- **Processos** para a estrutura operacional
- **Projetos/Tarefas** para execução e follow-up

Isso resolve a operação mínima do laboratório, mas cria um gap entre:
- **cobertura funcional real do domínio Comercial**
- **catálogo MCP percebido por Claude/Cliente**

## Hipóteses de produto

### Opção A — Manter Comercial apoiado em Projects/Processes
Usar explicitamente o modelo atual como desenho oficial do MVP.

**Prós**
- menor custo de implementação
- menor superfície sensível
- reaproveita componentes já tenant-safe

**Contras**
- baixa legibilidade semântica para agentes e clientes
- smoke do domínio Comercial depende de interpretação indireta
- reduz clareza do roadmap de CRM nativo

### Opção B — Criar catálogo canônico mínimo do Comercial
Publicar capabilities dedicadas, ainda que apoiadas internamente em serviços já existentes.

Exemplos de capabilities candidatas:
- `list_commercial_pipeline`
- `list_commercial_opportunities`
- `create_commercial_opportunity`
- `list_commercial_proposals`
- `list_commercial_contracts`

**Prós**
- melhora semântica do domínio
- reduz ambiguidade em smoke e automação
- aproxima o catálogo MCP da linguagem de negócio

**Contras**
- exige contrato, RBAC, telemetria e documentação canônica
- pode introduzir alias indevido se não nascer no domínio correto

## Recomendação
Seguir em duas fases:

### Fase 1 — explicitar o desenho atual
- documentar oficialmente que o Comercial MVP usa `processes` + `projects`
- registrar isso no catálogo/harness para evitar interpretação de bug

### Fase 2 — decidir catálogo canônico
- avaliar se o domínio Comercial terá entidade própria de oportunidade/proposta/contrato
- se sim, publicar capabilities canônicas sem depender de alias legados

## Backlog recomendado
1. Documentar cobertura atual do Comercial na surface `user`
2. Definir taxonomia canônica do domínio Comercial no MCP
3. Priorizar primeiro capability realmente necessária:
   - `opportunities.read`
   - `opportunities.write`
   - `proposals.read`
   - `contracts.read`

## Critério de saída deste paper
Este paper vira `SPEC` quando houver decisão oficial entre:
- manter Comercial como composição intencional de Projects/Processes
- ou evoluir para catálogo Comercial canônico dedicado
