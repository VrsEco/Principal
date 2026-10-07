# Runbook — Release e conexão de Status WhatsApp

## Estado e bloqueios concretos (07/10/2026, America/Bahia)

Implementação LOCAL; não commitada/implantada. As 12 artes aprovadas estão
versionáveis em seeds com hashes, e o importador foi testado em PostgreSQL
descartável. Nenhum Status/agenda/solicitação foi criado em produção.

O endpoint real é https://app.gestaoversus.com.br/mcp/pilot/ (não o painel).
Health real /mcp/healthz respondeu 200; metadata OAuth respondeu 200; GET
sem autenticação respondeu 401 com WWW-Authenticate. Isso não prova login,
publicação, recebimento ou atendimento. mcp-versus já existe no Codex e respondeu
autenticado nesta conversa; tools de Status e Deploy estão ausentes. Não criar outro.

Revisão independente em 07/10/2026: health público confirmou Streamable HTTP
stateless (SSE não suportado); metadata anuncia access/user/analytics/finance,
mas não admin; GET sem autenticação permaneceu 401. MCP confirmou AA, ID 9,
e Marketing Digital ID 187, código AA.J.26. Corrigido localmente o importador
que confundia ID 187 com code_sequence; agora exige empresa, ID e sequência 26.
Os hashes locais das 12 artes conferem; isso não comprova presença no servidor.
Checklist único permanece na SPEC; nenhum card de Status foi identificado nas
26 atividades consultadas do projeto 187. Criação operacional exige autorização.

O cliente hoje pede mcp:access, mcp:user, mcp:analytics. Após o release, precisa
consentir também mcp:admin, previamente habilitado no client/IdP pela operação
autorizada. Publicação efetiva exige grant AA com teto explícito
contendo somente whatsapp_status.read/publish/schedule/review e perfil admin.
Grant não concede poderes superiores aos do APP32. **Não sobrescrever grant
amplo já usado por outras integrações sem aprovação de impacto.** Não copiar
token para TOML, plugin ou chat. Autenticar pelo OAuth/PKCE existente.

Número, referência da integração Z-API e solicitação anterior ainda precisam
de consulta autenticada. A tool setup consulta apenas metadados de solicitações
existentes; esta entrega não cria uma nova solicitação automaticamente.

## Plano de release a aprovar (nenhuma ação Git/produção autorizada ainda)

- Branch proposta: codex/whatsapp-status-versus; SHA será conhecido após commit
  isolado aprovado. Não incluir alterações anteriores de outras entregas.
- Escopo: modelos/migration 20261007_1000; services whatsapp_status_*;
  mcp_whatsapp_status_tools; pequenos hooks em config/models/catalog/registry/
  capabilities/tenant_rbac/HTTP metadata/scheduler; contratos admin; testes;
  documentos desta entrega; manifesto e 12 PNG privadas em seeds.
- Arquivos compartilhados têm mudanças prévias: revisar e separar **hunks**,
  validando dependências de runtime/surfaces antes de formar o SHA de release.
- Modo: full; restart_mcp=true; reiniciar/verificar scheduler dedicado pelo
  fluxo oficial. WHATSAPP_STATUS_ENABLED continua false até homologação.
- Migração: nova revisão depende de 20261002_1000. Checkout já tinha heads de
  Google Calendar/knowledge. O executor existente usa upgrade(revision='heads');
  consultar versões reais e aprovar o grafo exato do SHA, sem incluir migrações
  alheias inadvertidamente. Rollback de ledger não destrói evidências.
- Executor: MCP de Deploy autenticado → deployment_id → aprovação humana →
  GitHub Actions. Sem esse controle, parar; não usar chave/SSH de produção ou
  sessão humana para disparar como agente. Falha/retry exige nova aprovação.

### Preflight local consolidado — 07/10/2026

- Base local consultada: 971fb4a6b2510863446accbbb1fac14d588f99b8, na branch
  codex/reparo-referencias-conciliacao-inter. Essa branch NÃO é a branch de release
  proposta; esse SHA não foi confirmado como SHA saudável de produção.
- Grafo analisado por AST, sem carregar Flask/.env nem conectar banco operacional:
  base HEAD tem apenas 20261002_1000; base + migration Status tem apenas
  20261007_1000; checkout completo tem 20260924_1500 e 20261007_1000. Nenhum
  parent ausente. Revisões 20260924_1300/1400/1500 pertencem a Deploy/knowledge;
  não podem entrar inadvertidamente em upgrade('heads') desta entrega.
- Hunks exclusivos conferidos: config (4 linhas), scheduler (20 linhas), anúncio
  admin na metadata, domínio Status em permission_matrix/profiles/playbooks.
  models/__init__, tool_catalog, capabilities e surface_registry misturam Status
  com Deploy/diagnóstico financeiro: NÃO copiar esses arquivos inteiros.
- Dependência obrigatória de segurança: _resolve_mcp_permission_ceiling e sua
  propagação/interseção em mcp_runtime, mais enforcement em tenant_rbac. Esses
  arquivos também contêm outras mudanças; delimitar e testar os hunks necessários.
  Não omitir hardening para reduzir artificialmente o escopo.
- Nova rodada no checkout atual: 191 passed, 1 warning, incluindo PostgreSQL
  descartável real, concorrência e restart. Isto NÃO valida um SHA isolado ainda
  inexistente. Reexecutar no candidato de release antes da aprovação de produção.
- Catálogo autenticado consultado novamente: domínio whatsapp_status tem zero
  capabilities. MCP de Deploy também não está exposto nesta conversa. A operação
  autorizada precisa disponibilizar o plano de controle antes de qualquer pedido
  de deploy; não tentar bootstrap dele pela mesma sessão sem esse controle.

## Gate adicional de reversão (pendente de aprovação e ensaio)

### Candidato isolado preparado após autorização de preparação

- Exportado o baseline 971fb4a6b2510863446accbbb1fac14d588f99b8 para
  `C:\GestaoVersus\app32\tmp\whatsapp_status_release_candidate`, sem criar
  branch, commit, alterar índice ou incorporar alterações alheias do checkout.
- Payload de revisão: `C:\GestaoVersus\app32\output\whatsapp_status_release\candidate-files.zip`;
  patch textual e manifesto SHA-256 por arquivo no mesmo diretório. São 46 arquivos,
  incluindo as 12 PNG. ZIP não é um mecanismo alternativo de deploy.
- Arquivos mistos foram reconstruídos por hunks: excluídos control plane Deploy,
  diagnóstico financeiro, company_ref e overlay de reparo. Incluídos somente Status
  e dependências de segurança: teto estrito/interseção de grants, identidade/contexto
  da requisição HTTP corrente e preservação de validação Annotated no SDK MCP.
  O escopo de aprovação do release deve incluir explicitamente essas dependências.
- Candidato: **234 passed, 1 warning in 32.77s**, onze suítes, PostgreSQL descartável
  real. A primeira exportação omitiu módulos de baseline; corrigida. A primeira
  suíte completa detectou ausência do hunk de interseção wildcard; incluído e
  reexecutada integralmente. Nenhuma mudança financeira entrou para resolver o teste.
- Branch permanece apenas proposta; SHA de commit do candidato ainda inexistente.
  Após aprovação específica de Git, aplicar somente payload/hunks, revalidar e
  publicar o SHA. Não confundir SHA do baseline com SHA do release.
- MCP de Deploy não consta das ferramentas disponíveis nesta conversa na verificação
  desta preparação. Não existe deployment_id; produção não foi disparada por agente.
  Operação autorizada precisa disponibilizar o control plane autenticado ou executar
  o fluxo oficial como operador, com gate humano. Sem SSH/browser como contorno.
- Rollback em HML, SHA saudável de produção, versões Alembic reais, aprovação de
  release, auth positiva e homologação da conta/atendimento permanecem pendentes.

- Registrar SHA saudável anterior, deployment_id, snapshot verificado e versões
  reais de Alembic antes do release. O plano deve enumerar os heads do SHA isolado.
- Contenção: manter/desligar WHATSAPP_STATUS_ENABLED e pausar agendas pela
  superfície autorizada. Envio em voo pode terminar; Status já enviado não é
  desfeito. Nunca limpar ledger ou repetir publicação incerta.
- Reversão de runtime: release oficial do SHA saudável anterior, com aprovação
  própria, restart MCP e validação do scheduler/health/atendimento. Manter as
  tabelas e evidências de Status; a migration bloqueia downgrade destrutivo.
- Ensaiar compatibilidade do runtime anterior com o schema aditivo em HML,
  incluindo scheduler e atendimento. Sem essa evidência, rollback permanece
  apenas um plano; não declarar release pronto.

## Checklist de homologação após release

1. Confirmar health, schema, worker MCP e scheduler; tools/list deve mostrar
   somente capabilities autorizadas. Negativas: sem auth, sem mcp:admin,
   grant revogado, tenant errado e URL/ID arbitrário. Reautenticar o mcp-versus
   existente uma vez. OAuth/PKCE permanece na infraestrutura já existente.
2. Executar get_whatsapp_status_setup para AA. Confirmar/reutilizar solicitação
   anterior e integração existente. configure_whatsapp_status_account recebe
   somente referência da integração e número esperado, nunca tokens. Global
   legado só pode ser explicitamente vinculado à AA; outros tenants não o usam.
3. verify_whatsapp_status_account lê apenas /status e /device, compara número
   esperado, retorna sufixo. Não há reconexão ou mudança de webhook/dispositivo.
4. register_whatsapp_status_approved_bundle importa 12 arquivos/hash e cria a
   agenda Versus semanal **desativada**. Originais de seeds são copiados para
   instance/whatsapp_status/<company_id>; jamais configurar root sob uploads/static.
   Depois habilitar feature flag aprovada; a agenda permanece pausada. A mudança
   da flag precisa chegar ao runtime MCP/aplicação; reiniciar/verificar também
   o scheduler dedicado pelo fluxo autorizado, pois o job só é registrado na
   inicialização quando WHATSAPP_STATUS_ENABLED=true. Conferir job/heartbeat;
   presença de agenda no banco não comprova worker ativo.
5. Preparar Versus 01 versão 1 para publicação REAL com chave única; pedir ao
   usuário que tenha o celular disponível; obter o gate persistido e executar
   publish_whatsapp_status_test uma vez. accepted não prova o celular. Se unknown,
   não reenviar. Conferência humana registrada por confirm_whatsapp_status_mobile.
6. Usuário envia uma mensagem de teste ao atendimento existente e confirma
   recebimento/resposta no APP32, sem conceder leitura de conversas ao conector
   Status. Registrar apenas evidência sanitizada. Só depois aprovar a retomada.

## Operação permanente

- Agenda 08:30 Bahia conforme mapa semanal aprovado; domingo sem itens.
- Persistência PostgreSQL, lock por empresa, envio serial, hash/dia e chave
  de comando. Resultado incerto/crash pausa agenda e não retenta.
- Janela de cinco minutos; sem catch-up de dias anteriores. Ocorrência claimed
  antes da rede não é regenerada após crash; revisão humana é necessária.
- Pausa impede próximos itens; chamada em voo não pode ser desfeita.
- Alteração pausa a agenda. Revisão calendar-month obrigatória; vencimento
  bloqueia execução até revisão/retomada confirmadas. Revogação é revalidada.
- Consultar results e ledger sem URL/token/corpo cru de erro. Logs urllib3
  redigem /token/... inclusive no nível DEBUG.

Fonte OAuth: https://developers.openai.com/plugins/build/auth
Evidência: [Harness](../harnesses/harness_whatsapp_status_mcp_v1.md).
