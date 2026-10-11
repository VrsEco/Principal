# Runbook — Coortes de leitura do mcp-versus

**Classe:** Runbook
**Data:** 2026-10-08
**Complementa:** [SPEC de classificação dos domínios](../spec/classificacao_dominios_mcp_versus_v1.md) e [Glossário do mcp-versus](../spec/glossario_mcp_versus_v1.md).

## 1. O que existe

Leituras do mcp-versus publicadas por **assunto**, cada uma validada pelo contrato automático
(`src/core/mcp_cohort_contract.py`, teste `test_mcp_read_cohort_contract.py`): risco baixo, sem gate,
verbo de leitura, `company_id` explícito, sem parâmetro de escrita, escopo alcançável pelo token,
permissão declarada e sem escrita no código da tool. Todas passam pelo limitador de tamanho de resposta.

| Assunto | Ferramentas | Padrão |
|---|---:|---|
| `strategy` | 13 | **ligado** |
| `processes` | 4 | **ligado** |
| `platform` | 3 | **ligado** |
| `knowledge` | 2 | **ligado** (variantes `*_secure`, `company_id` validado pelo grant; SPEC RAG 16.10) |
| `commercial` | 14 | desligado (dados sensíveis) |
| `finance` | 24 | desligado (dados sensíveis); `list_financial_closings` fica fora até existir `services.financial_closing_service` |
| `routine` | 16 | flag própria `MCP_VERSUS_ROUTINE_READ_ENABLED` |

## 2. Como ligar e desligar

Variável `MCP_VERSUS_READ_DOMAINS` no `.env` do servidor (`app32/.env`), lida ao iniciar o MCP:

| Valor | Efeito |
|---|---|
| ausente | `strategy`, `processes`, `platform`, `knowledge` |
| `strategy,processes,platform,commercial,finance` | exatamente a lista (acrescente os sensíveis) |
| `none` ou vazia | **interruptor de emergência**: nenhuma coorte nova |

Mudou o valor: reiniciar o runtime MCP pelo fluxo oficial (deploy `quick` com `restart_mcp=true`).
Assuntos fora da lista não são listados **nem registrados**.

## 3. Validação após o deploy

1. Confirmar no log do run: SHA esperado, `restart_mcp=true`, MCP ativo.
2. Reconectar o cliente e listar as capacidades (`list_user_app32_capabilities`): devem aparecer 49 + 14 (`routine`) + as coortes ligadas.
3. Chamar cada ferramenta nova na empresa de teste (somente leitura) e conferir: resposta estruturada, `_truncation` quando grande, negativa em empresa sem grant.
4. Ligar `commercial`/`finance` só depois de revisar amostras de dados reais com o responsável.

## 4. Reversão

- Imediata: `MCP_VERSUS_READ_DOMAINS=none` e reinício do MCP.
- Definitiva: reverter o PR e novo deploy aprovado.

## 5. Fora das coortes, por design

`get_my_work`, `get_tasks_today`, `search_organizational_knowledge`, `answer_organizational_question`
e `list_team_workload` (usam a "empresa ativa" da sessão; o conhecimento por empresa é atendido pelas
variantes `*_secure`, e as atividades pessoais por `list_my_work_secure`); a agenda da jornada
(`force_regenerate`); `get_project_task_analytics_report` (`include_deleted`); as 18
`describe_app32_*` de metadados internos; as ferramentas de deploy e **todas as mutações**
(onda 2, com gate humano).

## 6. Coortes de ESCRITA (sub-onda 2A)

Mutações novas entram por coorte própria, desligada por padrão. Variável `MCP_VERSUS_WRITE_DOMAINS` no `.env` do servidor (`app32/.env`), lida ao iniciar o MCP:

| Valor | Efeito |
|---|---|
| ausente, vazia ou `none` | nenhuma coorte de escrita (padrão) |
| `projects,operations,meetings,processes,routine,strategy,commercial` | liga exatamente os assuntos listados |

| Assunto | Ferramentas |
|---|---|
| `projects` | `create_project`, `update_project`, `update_project_task_secure` |
| `operations` | `request_engineering_suggestion`, `request_new_app32_integration` |
| `meetings` | `log_meeting_discussion` |
| `processes` | `create_process_bpmn_activity_tool`, `create_process_pop_step_for_bpmn_tool`, `draft_process_pop_step_description_tool`, `attach_process_pop_step_static_image_tool` (sub-onda 2B) |
| `routine` | 14 da jornada (sub-onda 2C): eventos de calendário, tarefa avulsa, solicitações de ausência e transferência, agenda (gerar, travar, destravar, mover), vínculos de rotina, blocos e regras. `delete_work_calendar_event_tool` exige aprovação |
| `strategy` | 17 de estratégia (sub-onda 2D): identidade e perfis estratégicos, vínculos de alinhamento, linha de visada, OKRs globais e de área, direcionador, participantes, seção do plano e revisão de maturação |
| `commercial` | 15 comerciais (sub-onda 2E): contratos (criar, editar, itens, encerrar), emissores, clientes, carteiras, catálogo, produtos e serviços e contrato da oferta. `close_commercial_contract` exige aprovação |

- Assunto fora da lista não é listado nem registrado. Mudou o valor: reiniciar o MCP pelo fluxo oficial (deploy `quick` com `restart_mcp=true`).
- Criar e editar não exigem aprovação (regra D6); excluir e encerrar exigem (2 ferramentas nas coortes `routine` e `commercial`). Aprovação e identidade seguem o contrato de mutações: só entra na coorte a ferramenta sem violação na linha de base.
- Reversão imediata: `MCP_VERSUS_WRITE_DOMAINS=none` e reinício.
- Validação após ligar: reconectar, listar as capacidades e chamar cada ferramenta na empresa de teste. Para escritas, usar registros de teste e conferir o ator gravado (deve ser o usuário da sessão).

## 7. Sonda de saúde do mcp-versus

`app32/scripts/qa/mcp_health_probe.py` checa, sem credenciais e só com leitura:
1. `/mcp/healthz` (200 e tempo);
2. descoberta OAuth em `/.well-known/oauth-protected-resource/mcp/pilot` (servidor de autorização e escopos base `mcp:access` e `mcp:user`);
3. descoberta do Keycloak (`token_endpoint`);
4. o endpoint MCP sem token deve responder 401.

Códigos de saída: 0 saudável, 1 degradado (lento ou sintomas no log), 2 falha. Opções: `--json` para um monitor externo e, no servidor, `--log logs/mcp_http_stderr.log --minutes 60` para contar `permission discovery failed`, `OperationalError` e `Traceback`.

Limites: não valida a lista de ferramentas (exige token). Para isso, chamar `list_user_app32_capabilities` autenticado e conferir a contagem esperada. Sintoma "0 ferramentas": olhar primeiro `permission discovery failed` no log.

## 8. Conector administrativo curado (`/mcp/pilot/admin`, escopo `mcp:admin`)

Segundo conector, só para administradores da plataforma. O conector comum (`/mcp/pilot`) **não muda** e nunca recebe `mcp:admin`.

**O que expõe (lista fechada, `src/core/mcp_admin_cohort.py`, 8 ferramentas):** aprovações de ausência e de transferência da jornada; exclusão de bloco, tarefa manual e regra da jornada; exclusão de linha de visada de indicador, de vínculo de alinhamento estratégico e de contrato comercial. Todas exigem aprovação humana persistida (regra D6) e permissão por empresa.

**O que não expõe:** diagnósticos do sistema (`get_database_schema`, `get_system_health`), cadastro de usuários, status de empresa, implantação de agentes, WhatsApp Status e as exclusões de projeto e reunião (dependem do adaptador do parâmetro de confirmação, M9).

**Ativação (por ordem):**
1. Keycloak, realm `app32`: criar o client scope `mcp:admin` como **opcional** (nunca padrão) e restringi-lo por papel (Scope → desligar "Full scope allowed" e mapear só o papel de administrador da plataforma).
2. `.env` do servidor: `APP32_MCP_OIDC_ADMIN_ROUTE_ENABLED=1` e `bash scripts/manage_mcp_http.sh restart`.
3. Conferir: `/.well-known/oauth-protected-resource/mcp/pilot/admin` responde 200 com `scopes_supported` = `mcp:access`, `mcp:admin`.
4. Cadastrar o conector no cliente com `https://app.gestaoversus.com.br/mcp/pilot/admin` e autorizar com a conta de administrador.

**Desfazer:** remover a flag do `.env` e reiniciar (a rota some e a descoberta volta a 404).

### 8.1 Decisão (2026-10-11): as 8 ferramentas vão pelo conector comum (coorte `admin_ops`)
O desenho original prevalece: um único conector (`mcp-versus`), com a visibilidade filtrada pelo perfil do usuário. 7 das 8 ferramentas da seção 8 ganharam o escopo `mcp_user` e formam o assunto `admin_ops` das coortes de escrita (`MCP_VERSUS_WRITE_DOMAINS`, desligado por padrão). Cada uma exige permissão por empresa (`work_journey.approve`, `work_journey.delete`, `strategy.alignment.update`) e aprovação humana persistida (regra D6); quem não tem a permissão não as vê.

O conector `/mcp/pilot/admin` da seção 8 permanece no código, **desligado** (`APP32_MCP_OIDC_ADMIN_ROUTE_ENABLED` ausente), para o dia em que existir um caso de plataforma (usuários, empresas, agentes). Motivo da mudança: o Claude registra o cliente por cadastro dinâmico e pede a lista antiga de escopos, o que impedia obter `mcp:admin` sem alterar o provisionador de clientes do Keycloak (provedor próprio, sem código no repositório).

`delete_commercial_contract` **fica só no conector administrativo**: a governança vigente (teste de catálogo) mantém a exclusão de contrato fora do escopo `mcp_user` (suspender e encerrar contrato ficam no usuário). Mudar isso é decisão própria.
