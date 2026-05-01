---
name: gestao_versus_core
description: Plano de controle do Gestão Versus. Use para aplicar governança global, escolher skill/especialista e manter a arquitetura enxuta e modular.
---

# Gestão Versus Core

Skill obrigatória de governança do projeto.

## Use para
- aplicar as regras globais do Gestão Versus
- decidir qual skill principal deve conduzir o trabalho
- escolher o especialista líder
- manter economia de contexto e separação correta entre agente, skill, referência e script

## Sequência curta
1. Ler `../../router/orchestrator.md`
2. Aplicar guardrails globais de `../../references/constitution.md`
3. Se houver 3 ou mais etapas, ativar obrigatoriamente `aa-j-31-card-execution` e materializar os cards antes da execução
4. Selecionar a skill principal, se existir:
   - incidente -> `gestao-versus-incident-response`
   - workflow V3 -> `workflow-factory-versus`
   - deploy/produção -> `deploy_gestao_versus`
5. Selecionar o especialista líder em `../../router/routing-matrix.md`
6. Consultar referências só se o detalhe for realmente necessário
7. Se o tema envolver Sapiens, validar aderencia à arvore oficial, aos codigos sem ponto, ao escopo pessoal/equipe/empresa e à taxonomia canônica de domínios

## Guardrails inegociáveis
- stack oficial Python/Flask/PostgreSQL
- multi-tenancy com `company_id`
- MCP First quando houver estado operacional
- sem lógica de negócio em rota
- respostas devem ser curtas e objetivas, com alvo de leitura entre 1 e 5 minutos, salvo quando o usuário pedir aprofundamento
- sem documentação longa dentro desta skill
- sem execução 3+ etapas sem cards reais em `AA.J.31`
- para Sapiens: arvore oficial por dominio, nao por estrutura legada
- para Sapiens: codigos de menu sem ponto, ex: `111`, `145`, `183`
- para Sapiens: escopo operacional explicito entre pessoal, equipe e empresa
- para Sapiens: dominio de tool precisa ser canonico antes da RBAC/policy
- para Sapiens: alias de dominio devem ser normalizados antes de permissao, telemetria e workflow resolution
- drift entre `capabilities`, `tenant_rbac`, `profiles`, `permission_matrix` e `playbooks` e falha arquitetural, nao detalhe de implementacao

## Governança adicional para Sapiens
- `1` Gestao da Rotina
- `2` Gestao Estrategica
- `3` Gestao Financeira
- `4` Sapiens
- `5` Governanca e Aprovacoes
- `6` Implantacao e Funcionamento
- `7` Sapiens Factory

## Taxonomia canônica obrigatória do Sapiens
- `routine` e o dominio canônico para consultas e operacoes de rotina
- `work`, `tasks` e `worklog` sao aliases de `routine`, nunca dominios canônicos independentes
- `processes` e dominio canônico suportado e precisa existir em contratos, policy e catálogo
- `finance` e dominio canônico sensível: nao publicar mutacao financeira em surface `user`
- leituras financeiras executivas devem ser tratadas como surfaces privilegiadas, tipicamente `admin` ou `analytics`
- toda capability nova deve nascer com dominio canônico, nunca depender de alias legado para autorizacao

## Regra de surfaces MCP
- `user` e surface operacional de menor privilégio e nao deve carregar dominio financeiro sensível
- `admin` concentra governanca, identidade administrativa e operacoes de alto impacto com gate humano quando exigido
- `analytics` existe para leitura/análise tenant-safe, nunca para mutacao operacional
- `ops` deve permanecer enxuta e focada em intervencao/suporte operacional, sem virar atalho de admin ou analytics

## Regra de MCP remoto
- MCP remoto HTTPS deve reaproveitar o mesmo registry canonico de surfaces usado no stdio; nao criar catalogo paralelo
- contexto remoto deve ser resolvido por request e nao por env fixa de processo quando houver autenticacao por usuario
- `user_id`, `company_id`, `fallback_role` e `surface` precisam ser injetados com isolamento por request antes da execucao das tools
- auth MVP por token interno e aceitavel apenas para homologacao/controlado; para claude.ai o alvo correto e OAuth
- conector remoto do claude.ai exige reachability publica por HTTPS e nao deve depender de pasta local do projeto ou tunel manual
- `company_id` continua obrigatorio no runtime remoto; qualquer possibilidade de tenant crossing e falha critica
- override de contexto por header/query so e aceitavel em modo controlado e desligado por padrao em producao
- smoke de MCP remoto deve validar no minimo: `/healthz`, negacao sem auth, segregacao de surfaces e preservacao do stdio

## Regra de canal relevante
- no WhatsApp, quando houver multiplas empresas elegiveis para a operacao, a selecao da empresa deve acontecer antes da confirmacao final
- quando a consulta operacional estiver clara e for somente leitura, nao empurrar fallback agentic por falha de classificação textual

## Referências
- `../../router/orchestrator.md`
- `../../router/routing-matrix.md`
- `../../references/constitution.md`
- `../../references/personas.md`
- `../../references/component-boundaries.md`
- `../../references/sapiens-official-tree.md`
