# SPEC — Classificação dos domínios publicados no mcp-versus

**Classe:** SPEC
**Data:** 2026-10-08
**Status:** aprovado nas recomendações pelo responsável do produto em 2026-10-08; nenhuma publicação de tool é feita por este documento
**Card:** a registrar (estabilização e experiência do MCP)
**Liderança:** @ARQUITETO; governança gestao_versus_core
**Complementa:** [Glossário oficial do mcp-versus](glossario_mcp_versus_v1.md) e [Identidade OAuth/OIDC e implantação Keycloak APP32/MCP](identidade_oauth_keycloak_app32_mcp_v1.md).

## 1. Decisão

1. O mcp-versus é o único MCP do APP32. O que o usuário vê deve **espelhar** o que o APP32 lhe concede (grant ∩ RBAC ∩ teto ∩ gate humano).
2. Hoje 64 das 348 capacidades do catálogo (18%) são publicáveis pelas listas fixas do registro de surfaces, e oito domínios têm zero exposição. Este SPEC define **o que publicar, em que ordem e com que pré-requisitos**.
3. Publicação é por **ondas**: leituras de risco baixo primeiro (onda 1); mutações depois, sempre com gate humano e `company_id` explícito (onda 2).
4. Nada é publicado sem os pré-requisitos da seção 5.

## 2. Critérios de classificação

| Classe | Critério |
|---|---|
| **Publicar** | Uso diário do usuário final; isolado por empresa (`tenant_safe`); leitura de risco baixo, ou mutação de risco médio/alto **com gate humano**. |
| **Manter** | Já publicado e coerente. |
| **Dividir** | Domínio misto: parte publica, parte fica fora ou vai para decisão própria. |
| **Avaliar depois** | Valor claro, mas exige coorte própria ou maior maturidade de contrato. |
| **Fora** | Administração crítica, SQL livre ou ferramenta do chat legado sem contrato de MCP. |

Fonte dos números: catálogo de capabilities na `main` em 2026-10-08, comando `app32/scripts/qa/mcp_drift_report.py` e domínio/risco/gate/tags de cada capability. A classificação é **por domínio e por risco declarado**; exceções individuais são conferidas na migração de cada domínio.

## 3. Classificação por domínio

Risco = baixo/médio/alto+ (alto e crítico). "Hoje" = capabilities publicáveis pelas listas fixas.

| Domínio | Total | Hoje | Risco | Gates | Classe | Onda |
|---|---:|---:|---|---:|---|---|
| routine | 39 | 0 | 18/18/3 | 5 | Publicar. Leituras primeiro; aprovações com gate | 1 e 2 |
| strategy | 37 | 0 | 15/20/2 | 15 | Publicar em fases (leituras e depois mutações, todas com gate) | 1 e 2 |
| finance | 86 | 9 | 35/49/2 | 5 | Publicar por coorte: 42 leituras na onda 1; 50 mutações com idempotência e gate | 1 e 2 |
| meetings | 20 | 18 | 3/16/1 | 6 | Manter e completar as 2 restantes | 1 |
| processes | 21 | 7 | 9/9/3 | 4 | Publicar o restante; leituras (BPMN/POP) primeiro | 1 e 2 |
| projects | 14 | 3 | 3/7/4 | 5 | Publicar; exclusões (soft delete) só com gate | 1 e 2 |
| identity_self_service | 20 | 5 | 18/2/0 | 0 | Publicar o restante (descoberta e contexto) | 1 |
| knowledge | 7 | 0 | 6/1/0 | 1 | Publicar as leituras (busca e resposta organizacional) | 1 |
| audit | 3 | 3 | 3/0/0 | 0 | Manter | — |
| workload | 2 | 0 | 2/0/0 | 0 | Publicar (leitura de carga da equipe) | 1 |
| operations | 4 | 0 | 1/3/0 | 0 | Publicar com gate (solicitações à Engenharia) | 2 |
| analytics | 3 | 0 | 2/0/1 | 1 | Dividir: 2 leituras do grafo estratégico publicam; `query_database` fica **fora** | 1 / fora |
| consultive | 12 | 0 | 7/5/0 | 5 | Avaliar depois: 7 leituras em coorte consultiva; 5 mutações com gate | 2 |
| governance | 63 | 4 | 31/29/3 | 7 | Dividir: `describe_*` e catálogos publicam; aprovação e deploy conforme §4 | 1 / §4 |
| whatsapp_status | 15 | 15 | 8/0/7 | 7 | Manter; visibilidade depende do modelo de escopos | — |
| identity_admin | 2 | 0 | 0/0/2 | 2 | **Fora** do MCP | — |

## 4. Decisões do responsável (2026-10-08)

| # | Decisão |
|---|---|
| D1 | As ferramentas de solicitação e aprovação de deploy (`request_agent_deployment`, `approve_agent_deployment`, `get_agent_deployment`, `list_agent_deployments`) **permanecem no mcp-versus**, por haver um único MCP. Devem seguir o contrato vigente da SPEC `controle_deploy_agentes_squad_v1`: permissão administrativa explícita, tenant de governança e **aprovação humana** para aprovar; agente nunca aprova. Esta decisão define apenas o endereço (mcp-versus) e não amplia o que o fluxo de deploy já exige; os requisitos exatos são conferidos na migração do domínio `governance`. |
| D2 | A **onda 1** prioriza `routine`, `strategy` e leituras de `finance`, por valor diário e exposição atual de 0% a 10%. |
| D3 | `identity_admin` (listar e registrar usuários do sistema) fica **fora do MCP**; a criação de usuários segue pela interface do APP32. |

## 5. Pré-requisitos para publicar um domínio

Uma tool só entra no mcp-versus quando **todos** os itens abaixo estão cumpridos e verificados pelos testes de contrato (`test_mcp_manifest_drift`, `test_mcp_glossary_contract` e a suíte do registro de surfaces):

1. Declarada no catálogo com domínio, permissão, risco, gate humano e contexto exigido.
2. Domínio presente na matriz de permissões, nos playbooks e no RBAC por domínio.
3. Permissão exigida pela tool mapeada para o vocabulário que o APP32 resolve por empresa em cada chamada.
4. Escopo de surface coerente com o modelo vigente. O escopo `sapiens` identifica o canal do agente Sapiens dentro do app e **coexiste** com os escopos `mcp_*`; ele não impede nem substitui a publicação (ver Correção de 2026-10-08).
5. Mutação com `company_id` explícito, idempotência quando financeira e gate humano persistido quando o risco exigir.
6. Linha de base da catraca atualizada somente para **reduzir** divergências.
7. Evidência de teste e liberação em coorte antes de ampliar.

### Defeitos conhecidos a corrigir antes das publicações

| Domínio | Defeito |
|---|---|
| audit | Ausente da matriz de permissões e dos playbooks |
| knowledge | `answer_product_help` sem permissão declarada |
| identity_self_service | Uma tool de classificação financeira está no domínio de identidade |
| finance, strategy, consultive, governance | *(retirado, ver Correção)* O escopo `sapiens` não é defeito de publicação: marca o canal do agente Sapiens e coexiste com `mcp_*` |
| geral | 17 combinações distintas de escopos entre as tools; duas formas de registro (LangChain e registradores MCP); vocabulário de permissões das tools (118 nomes) diferente do da matriz |

## 6. Ordem de execução

| Etapa | Entrega | Efeito em produção |
|---|---|---|
| E1 | Corrigir os defeitos acima nas fontes (um PR por domínio) | nenhum, só contratos |
| E2 | Manifesto único de tools (declaração única que deriva catálogo, RBAC, playbooks e registro), em modo "compara" e depois "gera" | nenhum até o corte |
| E3 | Onda 1: publicar leituras de `routine`, `strategy`, `finance`, `knowledge`, `workload`, `identity_self_service`, `processes`, `projects`, `meetings` e `analytics` (2) | sim: deploy e restart do MCP, com coorte |
| E4 | Onda 2: publicar mutações com gate, por domínio | sim: por domínio |
| E5 | Remover as listas fixas do registro quando o manifesto único governar | sim |

Cada etapa com efeito em produção segue o fluxo oficial de deploy, plano único e aprovação explícita.

## 7. Fora do escopo e pontos em aberto

- O **modelo de escopos** (`mcp:<surface>` ou escopo único) segue decidido à parte, após os dados de sessão do Keycloak.
- A visibilidade do `whatsapp_status` depende desse modelo; o domínio já está completo nos contratos.
- A lista de tools por domínio não foi lida individualmente nas 348; a migração de cada domínio revisa o contrato tool a tool.
- Não altera autorização, identidade nem dados persistidos.

## 8. Critérios de aceite do SPEC

- Todo domínio do catálogo tem classe e onda neste documento (verificável contra `mcp_drift_report.py`).
- Nenhuma tool das classes Fora ou Avaliar depois é publicada sem revisão deste SPEC.
- Cada onda cita o PR e o teste de contrato que a comprova.

## 9. Correção de 2026-10-08 (medições posteriores à aprovação)

A versão inicial desta SPEC tratava o escopo `sapiens` como defeito que impedia a publicação. A medição no catálogo e nos registradores mostrou o contrário:

- **O `sapiens` é o marcador do canal do agente Sapiens dentro do app**, não escopo morto. Das 348 capabilities, **nenhuma** tem só `sapiens`; todas têm ao menos um escopo `mcp_*`, e 295 têm os dois.
- Já há 43 tools publicadas no mcp-versus que carregam `sapiens` junto de `mcp_*`.
- **345 das 348 capabilities têm implementação MCP registrada** (276 via registradores MCP e 72 via LangChain); as 3 restantes (conciliação financeira) já estão publicadas por registrador próprio do piloto.
- Consequência: publicar uma onda é, em essência, **liberar nomes na lista de publicação do registro**, com escopo e permissão corretos, testes e coorte. Não há necessidade de reescrever tools nem de remover o `sapiens`.
- O que continua verdadeiro: 17 combinações distintas de escopos, duas formas de registro e vocabulário de permissões duplicado são dívidas a reduzir no manifesto único (E2), mas não bloqueiam a onda 1.
