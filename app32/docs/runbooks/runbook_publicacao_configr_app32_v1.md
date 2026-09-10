# Runbook — Publicação APP32 no Configr

Classe documental: `Runbook`

## Pré-condições obrigatórias

1. Confirmar revisão aprovada e testes locais verdes.
2. Gerar backup de produção conforme `backup_producao_configr.md` e registrar o artefato.
3. Confirmar que o worktree remoto está limpo. Se não estiver, parar: preservar e
   reconciliar o drift em tarefa própria; nunca executar `reset --hard` sobre ele.
4. Confirmar que o checkout contém `app32/app.py` e `app32/requirements.txt`.

## Decisão de reconciliação vigente

- A branch local versionada é a fonte canônica do APP32. A bifurcação de
  produção da Central de Pessoas (`people_v3`) não deve ser promovida por
  merge automático nem preservada por cópia manual no deploy.
- O snapshot remoto permanece como evidência e rollback; mudanças de produção
  só podem retornar em commits revisados, coesos e testados contra a fonte
  canônica.
- Enquanto houver drift, o deploy permanece bloqueado. O bloqueio não alcança
  o website isolado do Keycloak, que possui runtime e banco independentes.

## Fluxo

1. Publicar apenas uma revisão identificada em `main`.
2. Executar o deploy `full` quando houver migration; usar `quick` somente sem alteração
   de schema/dependência.
3. O script valida o contrato `REPO -> APP`, aplica migrations antes do restart e
   configura uWSGI/MCP para `APP`.
4. Validar `/healthz`, `/mcp/healthz`, negação sem autenticação e smoke autorizado
   limitado à coorte aprovada.

## Rollback

1. Parar a expansão da coorte imediatamente.
2. Restaurar a revisão anterior conhecida e manter OAuth desabilitado para a coorte.
3. Validar health e segregação por `company_id` antes de reabrir o serviço.
4. Registrar causa, revisão, horário e decisão no card da entrega.

## Proibições

- Não publicar por cópia manual na raiz do host.
- Não expor segredos, tokens, issuer, URLs privadas ou dumps em logs/cards.
- Não habilitar OAuth enquanto o contrato de publicação não estiver validado no host.
