# SPEC — Presença Operacional de Usuários v1

## Decisão oficial

O APP32 registra presença web transitória por sessão autenticada para apoiar observabilidade operacional. O recurso não substitui autenticação, autorização, auditoria de ações ou controle de acesso.

## Contrato

- toda sessão pertence simultaneamente a `user_id` e `company_id`;
- consulta administrativa exige empresa explícita e autorização no tenant;
- o identificador da sessão e o endereço IP são persistidos somente como HMAC-SHA256;
- o user-agent completo não é armazenado; apenas tipo de dispositivo e navegador normalizados;
- `online`: atividade nos últimos 180 segundos;
- `idle`: atividade acima de 180 e até 900 segundos;
- `offline`: logout, expiração ou ausência de heartbeat;
- registros com última atividade superior a 24 horas são eliminados na consulta administrativa do tenant.

## Segurança e privacidade

- proibida consulta agregada entre empresas pela API operacional;
- administrador de plataforma deve selecionar uma empresa antes da leitura;
- falha no heartbeat não pode impedir a navegação;
- presença não autoriza ação, não comprova produtividade e não deve ser usada isoladamente para avaliação de desempenho.

## Interfaces

- `POST /api/presence/heartbeat`;
- `GET /api/configs/system/presence?company_id=<id>`;
- `GET /configs/system/presence?company_id=<id>`.

