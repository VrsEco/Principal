# SPEC — Observabilidade de Uso e Presença v1

## Decisão

O APP32 disponibilará métricas de uso por empresa e pessoa sem expor conteúdo
sensível, tokens ou dados de autenticação. A leitura operacional é sempre
`company_id`-scoped; a visão global é exclusiva do administrador da plataforma.

## Fontes existentes e limites

- `user_presence_sessions` é presença transitória. Seu expurgo impede usá-la
  como fonte histórica de horas conectadas.
- `user_logs` é auditoria e não pode ser reconsultado integralmente pela UI.
- auditorias IA/MCP são fonte de classificação de uso, nunca de prompt,
  resposta, segredo ou token.

## Modelo alvo

`usage_telemetry_hourly` é uma tabela agregada por:
`bucket_started_at`, `company_id`, `user_id`, `channel` e `usage_kind`.

Campos mínimos: sessões iniciadas, segundos ativos estimados, requisições,
requisições IA, requisições MCP, erros e latência acumulada. Não armazena URL
com parâmetros, IP, user-agent, payload, credencial, token ou conteúdo IA.

Uma job idempotente agrega somente buckets fechados. Leituras de 7, 30 e 90
dias consultam essa tabela indexada; período customizado começa limitado a 90
dias. Eventos brutos têm retenção curta; agregados têm retenção longa.

## Semântica

- **online** é estado de presença atual, não prova trabalho produtivo;
- **tempo ativo estimado** é calculado por janelas de heartbeat, limitado por
  timeout de inatividade;
- **requisição IA/MCP** é classificada no produtor do evento, não por texto da
  URL no dashboard;
- CPU e memória são métricas do host. Não serão apresentadas como consumo
  exato de um usuário em worker compartilhado.

## RBAC

| Perfil | Escopo |
| --- | --- |
| Plataforma | global, infraestrutura e auditoria autorizada |
| Admin da empresa | somente agregados do próprio `company_id` |
| Gestor | agregados de equipe autorizada |
| Colaborador | somente suas próprias métricas |

O domínio alvo é `operations.monitoring`; a Central Pessoas mostra apenas
resumos autorizados. MCP tokens continuam no domínio `integrations` e jamais
integram payloads ou respostas de telemetria.

## Orçamento operacional

- heartbeat apenas quando aba está visível;
- gravação de evento mínima e sem consulta adicional por request;
- agregação via scheduler, fora do request web;
- dashboard usa agregados e paginação;
- índices obrigatórios: `(company_id, bucket_started_at)`,
  `(user_id, bucket_started_at)` e chave única do bucket.

## Ativação controlada

`USAGE_TELEMETRY_ENABLED` inicia desligada. Nenhum produtor de evento pode ser
ativado até validar Redis/queue, migration aplicada, retenção e carga em
homologação. O limite padrão para período customizado é 90 dias e a retenção
de eventos brutos é 14 dias; ambos são configuráveis por ambiente.

## Critério de aceite v1

1. nenhuma consulta de dashboard lê logs brutos sem limite;
2. nenhuma resposta contém token, IP, prompt ou resposta IA;
3. filtros 7/30/custom respeitam tenant e RBAC;
4. presença em tempo real permanece com o mesmo contrato atual;
5. job é idempotente e observável.
