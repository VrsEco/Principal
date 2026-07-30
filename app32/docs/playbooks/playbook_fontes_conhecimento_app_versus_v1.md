# Playbook — Inclusão de Fontes de Conhecimento do APP Versus v1

**Classe documental:** Playbook
**Status:** canônico
**Data:** 2026-07-30
**Domínio:** `knowledge`

## Quando usar

Ao incluir ou alterar uma família de fontes da Camada de Conhecimento.

## Decisão

1. identificar proprietário funcional;
2. classificar `knowledge_scope`;
3. resolver `company_id` quando `company`;
4. declarar status elegíveis, autoridade e vigência;
5. declarar grants e campos sensíveis;
6. criar adapter no registry;
7. definir chunking e relações;
8. implementar checksum, exclusão e reconciliação;
9. criar testes de contrato e cross-tenant;
10. ativar por feature flag e monitorar.

## Regra específica de `product_help`

- um artigo por JSON em `knowledge/product_help`;
- somente `status=published`;
- `product_version`, `route_key`, `module_key` e `canonical_uri` obrigatórios;
- capabilities declaradas;
- tour usa `data-help-id`;
- mudança de conteúdo altera checksum;
- remoção do arquivo deativa a projeção na próxima sincronização.

## Gate

Não registrar adapter se tenant, ACL, vigência, exclusão ou rollback forem ambíguos.

## Gate para habilitar uma fonte na busca

1. confirmar que o adapter resolve `knowledge_scope` e `company_id`;
2. validar status, vigência e exclusão antes do ranking;
3. executar cenário positivo no tenant proprietário;
4. executar cenário negativo em outro tenant;
5. confirmar que a resposta contém citação e URI registrada;
6. confirmar abstenção quando a evidência não existe;
7. somente então incluir o `source_type` na jornada do Sapiens.

## Regra específica de `process_publication`

- indexar somente `status=published`;
- manter apenas a maior versão publicada por processo;
- projetar `company`, `user` e `employee`;
- nunca converter grant `process` ou `activity` em acesso de empresa;
- ignorar conteúdo visual/binário, preservando apenas texto operacional;
- apontar a citação para o processo publicado, não para a projeção.

## Regra específica de `meeting`

- indexar somente reunião concluída (`completed` ou legado `done`);
- projetar ata, discussões, atividades e pauta;
- autorizar apenas participantes e convidados internos ativos e identificáveis;
- sem identificador interno, manter a fonte irrecuperável;
- apontar a citação para o relatório oficial da reunião.
