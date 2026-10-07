# Harness — Aceite de Status WhatsApp MCP

## Laboratório executado

PostgreSQL 14 descartável, localhost:55439/whatsapp_status_test, independente do
APP32 operacional. DDL da migration real; modelos SQLAlchemy reais; fornecedor
e lookups de identidade são doubles explícitos. Nenhum envio real ao fornecedor.

Suítes: test_whatsapp_status_contracts.py, test_whatsapp_status_postgres.py,
test_whatsapp_status_security.py, test_core_mcp_surface_registry.py,
test_core_mcp_http_server.py, test_mcp_explicit_permission_ceiling.py,
test_whatsapp_webhook_payload.py, test_scheduler_runtime_management_scripts.py,
test_knowledge_scheduler_contract.py.

Cobertura: imagem inválida/hash adulterado/kit incompleto; origem fixa de 12
artes; versão/idempotência/agenda desativada; FK cross-tenant; lock e requisições
simultâneas reais; erro/timeout; crash após aceite antes de commit; restart com
nova sessão; pausa durante requisição em voo; revisão mensal; janela Bahia e
domingo; conta errada; gate de homologação; feature flag; grant/teto/scope/role
revogados ou inválidos; schema MCP sem URL livre; redaction de token em DEBUG;
regressão de webhook/HTTP/scheduler existentes.

Rodada final: **189 passed, 1 warning in 32.57s** (depreciação Starlette/httpx).
Schemas MCP reais também rejeitaram coerção de booleanos/strings para IDs e de
número para command_key após StrictInt/StrictBool/StrictStr. diff --check não
apontou erros. O cluster descartável foi desligado após os testes; dados de
laboratório permanecem apenas em tmp para reprodução.

## Limites e aceite ainda obrigatório

### Preparação autorizada — candidato isolado

- Baseline exportado: 971fb4a6b2510863446accbbb1fac14d588f99b8. Hunks Status
  e hardening delimitados, sem alterações pendentes de Deploy/financeiro/company_ref.
  Nenhum commit/branch/push/produção executado. Manifesto do payload contém 46
  arquivos com SHA-256; 12 são as artes aprovadas. Não é SHA de release commitado.
- Exportação inicial incompleta: cinco erros de collection por ausência de utils.
  Completados exclusivamente módulos do baseline. Primeira rodada completa:
  233 passed, 1 failed; extração omitira o hunk wildcard da interseção do teto.
  Corrigida seleção e reexecutado tudo: **234 passed, 1 warning in 32.77s**.
- Onze suítes: as nove anteriores, mais test_mcp_http_auth_request_freshness_isolated.py
  e test_core_mcp_runtime_http_context.py. PostgreSQL descartável real; chamadas
  de fornecedor e lookup de identidade são doubles. Cluster desligado no finally.
- Metadados/schemas/freshness/teto testados localmente não provam OAuth real,
  worker em produção, capacidade de Status da conta ou atendimento no celular.
  Reversão com runtime anterior em HML não ensaiada. MCP Deploy ausente nesta
  conversa; sem deployment_id. Agenda segue sem ativação e nenhum Status enviado.

### Revalidação independente — 07/10/2026

- 12/12 arquivos locais presentes e SHA-256 iguais ao manifesto.
- Consulta MCP autenticada: AA company_id=9; Marketing Digital id=187,
  code_sequence=26, código AA.J.26. Importador corrigido localmente; dois casos
  novos verificam resolução tenant-safe e recusa quando o projeto não existe.
- Execução isolada inicial: 38 passed, 12 errors. O fixture de segurança dependia
  de import prévio de runtime_identity e falhava ao substituir models por double.
  Corrigido somente o fixture, com double explícito do lookup de identidade.
- Nova rodada: **175 passed, 1 warning in 16.37s**; contratos, segurança, registry,
  HTTP, teto de permissões, webhook e gestão de scheduler/knowledge. Runtime:
  .venv Python 3.11.7; pytest da raiz, sem cache. Depreciação Starlette/httpx;
  também houve aviso do requests sobre charset detector ausente no startup.
- PostgreSQL/concorrência/restart não reexecutados nesta revisão: cluster de
  laboratório desligado naquela rodada de 175. Reexecução posterior abaixo.
  Os 189 testes anteriores são evidência histórica, não evidência de produção.
- GET públicos: health 200, streamable-http stateless/SSE false; metadata 200
  sem mcp:admin; endpoint sem autenticação 401. Catálogo autenticado atual sem
  Status/Deploy. Nenhum envio, agenda ou alteração de credenciais em produção.

### Continuação autorizada — revalidação PostgreSQL, 07/10/2026

- Reutilizado somente tmp/whatsapp_status_pg_lab, PostgreSQL 14.20, loopback
  127.0.0.1:55439, banco whatsapp_status_test. Duas tentativas de bootstrap com
  roles padrão falharam antes da suíte; diagnóstico single-user consultou apenas
  nomes de roles e identificou status_test. Sem ler credenciais de produção.
- Suíte completa de nove arquivos citados acima: **191 passed, 1 warning in
  23.14s**, .venv Python 3.11.7. Fornecedor/identidade permanecem doubles; locks,
  DDL, constraints, concorrência e restart usam PostgreSQL real descartável.
- Cluster desligado no finally; pg_ctl status confirmou no server running.
- Grafo AST: HEAD local 20261002_1000; candidato teórico somente Status
  20261007_1000; checkout completo 20260924_1500 + 20261007_1000; sem parents
  ausentes. Não consultadas versões Alembic de produção.
- Tests foram executados no checkout com outras alterações pendentes. Não existe
  ainda SHA isolado testado, deployment_id, ensaio de rollback do runtime anterior
  ou homologação real da conta/Status/atendimento. Não promover o resultado local
  a aceite de produção.

- OAuth real e grant AA restrito ainda não exercitados.
- Conta/número e solicitação existente ainda não consultados em produção.
- Não houve deploy, Status ou ativação de agenda em produção.
- Webhook testado em laboratório não prova atendimento real; exige teste humano.
- Status accepted simulado não prova presença no celular; homologação real
  coordenada pelo [Runbook](../runbooks/runbook_whatsapp_status_mcp_v1.md).
