# SPEC — Contrato de publicação Configr para APP32

Classe documental: `SPEC`

## Decisão

O único runtime publicável do APP32 é `app32/` dentro do checkout versionado.
O deploy deve sincronizar o repositório, executar dependências/migrations e reiniciar
uWSGI + MCP com `APP` apontando para esse diretório.

## Invariantes

1. `REPO` é o checkout Git; `APP=$REPO/app32` contém `app.py` e `requirements.txt`.
2. Deploy falha antes de `reset --hard` quando o worktree remoto não estiver limpo.
3. Após o reset, a ausência de `APP/app.py` ou `APP/requirements.txt` falha o release.
4. uWSGI e MCP usam o mesmo `APP`; não há cópia raiz alternativa como runtime.
5. Migration ocorre antes do restart e somente em release `full` previamente validado.
6. Backup/restauração e a reconciliação de drift são pré-condições externas à janela;
   o script não apaga drift para tentar prosseguir.

## Critérios de aceite

- Um teste estático valida o contrato do script de deploy.
- A validação local comprova a resolução de `REPO`/`APP` sem depender do host.
- Na janela de infraestrutura, o host comprova worktree limpo, backup recente,
  health web/MCP e a revisão efetivamente executada.

## Relação com OAuth

O rollout OAuth R07 permanece bloqueado até este contrato estar ativo no host.
Sem ele, um reset pode publicar uma árvore diferente daquela homologada e inviabiliza
garantias de autenticação, `company_id` e rollback.
