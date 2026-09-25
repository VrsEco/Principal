---
name: gestao_versus_core
description: Controle obrigatório do Gestão Versus: governança, roteamento e economia de contexto.
---

# Gestão Versus Core

## Aplicação obrigatória
1. Classifique o pedido e aplique `../../router/orchestrator.md`.
2. Aplique `../../references/constitution.md` e escolha o líder em `../../router/routing-matrix.md`.
3. Para execução com 3+ etapas, materialize antes um único card por entrega com `aa-j-31-card-execution`.
4. Carregue referências especializadas somente quando o assunto exigir o detalhe.

## Guardrails inegociáveis
- Stack: Python, Flask e PostgreSQL; SQLite e Vertex AI são proibidos.
- Toda leitura e escrita deve isolar `company_id`; nunca confie somente no id do objeto.
- Use MCP para estado operacional; rota HTTP só valida/adapta e não contém regra de negócio.
- Valide payloads com schema rigoroso. Segurança, RBAC e tenancy são requisitos arquiteturais.
- Responda em PT-BR, começando pela decisão, em 3–7 bullets e com detalhe proporcional ao pedido.

## Roteamento mínimo
- Incidente/produção: `gestao-versus-incident-response` / QA.
- Workflow V3, Sapiens, WhatsApp, intent ou sessão: `workflow-factory-versus` ou `sapiens-workflow-first` / Backend Service.
- Deploy/migração: `deploy_gestao_versus` / QA.
- Arquitetura e boundary: Arquiteto; API/MCP: Backend API; dados: DBA; UI: Frontend; IA: AI Engineer.
- Não expanda além de um líder e os apoios estritamente necessários.

## Deploy de agentes do Squad Engenharia
- Qualquer deploy solicitado por Codex ou Claude deve aplicar
  `deploy_gestao_versus` e a SPEC
  `app32/docs/spec/controle_deploy_agentes_squad_v1.md`.
- A solicitação passa pelo MCP de Deploy com identidade autenticada,
  `company_id`, autorização e trilha de auditoria. GitHub Actions é o único
  executor de produção; SSH manual é contingência formalmente registrada.
- A aprovação única de release definida em `deploy_gestao_versus` e na SPEC
  canônica vincula o Squad inteiro: ela cobre commit→PR→merge→workflow→smoke
  somente dentro do SHA e parâmetros aprovados; o gate `production` continua
  obrigatório e novas variáveis de impacto exigem nova aprovação.
- Reconciliação Configr/Git/checkout deve seguir a SPEC
  `app32/docs/spec/reconciliação_baseline_configr_git_local_v1.md`; SHAs
  registrados são evidência histórica e devem ser revalidados.

## Sapiens e MCP remoto
- Use domínio canônico (`routine`, `processes`, `finance`); normalize aliases antes de RBAC, telemetria e workflow.
- `finance` não publica mutação em `user`; leituras executivas usam `admin` ou `analytics`. `analytics` é somente leitura; `ops` não substitui `admin`.
- No remoto, reutilize o registry de surfaces do stdio e injete por request `user_id`, `company_id`, `fallback_role` e `surface`. Override externo fica desligado em produção.
- Preserve isolamento entre tenants; para Claude remoto, o destino é HTTPS público + OAuth. Smoke mínimo: health, negação sem auth, segregação de surface e paridade stdio.
- Em WhatsApp com mais de uma empresa elegível, escolha a empresa antes da confirmação; consulta operacional clara e somente leitura não cai em fallback agentic por classificação textual.
- Para Sapiens, valide árvore oficial (1 Rotina; 2 Estratégica; 3 Financeira; 4 Sapiens; 5 Governança; 6 Implantação; 7 Factory), código sem ponto e escopo pessoal/equipe/empresa.
- Drift entre `capabilities`, `tenant_rbac`, `profiles`, `permission_matrix` e `playbooks` é falha arquitetural.

## Documentação e contexto
- Atualize antes o artefato canônico. Todo documento novo é exatamente um de: Paper, SPEC, Manifesto, Playbook, Runbook ou Harness; use `docs/spec/` para decisões oficiais.
- Consulte `docs/spec/politica_orcamento_contexto_v1.md` antes de trabalho longo, revisão ampla ou delegação.
- Mudança oficial de Sapiens, squads, MCP, surfaces, perfis, agentes ou harness atualiza a documentação dependente na ordem Paper → SPEC → Manifesto → Playbook → Runbook → Harness.
- Nunca varra ou carregue `vendor-skills` recursivamente. Abra somente arquivos identificados, com recorte de linhas e saída limitada.

## Formato
- **Decisão:** conclusão em uma linha.
- **Impacto:** uma ou duas consequências.
- **Próximo passo:** ação objetiva.
