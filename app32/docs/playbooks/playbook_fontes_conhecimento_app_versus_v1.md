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

## Regra específica da Árvore Estratégica

A Árvore Estratégica pertence ao domínio `knowledge`, mas não é um adapter de fonte canônica:

- contribuição bruta é preservada em `strategic_tree_contributions`;
- classificação e síntese não sobrescrevem a fala original;
- toda escrita exige `company_id`, ator autenticado, auditoria e idempotência;
- contribuição MCP exige confirmação humana explícita;
- conteúdo confidencial respeita policy antes da serialização;
- a árvore não alimenta automaticamente `knowledge_sources`;
- promoção para estratégia, processos, projetos ou outro domínio canônico permanece fora do P0.

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

## Playbook de curadoria do Sapiens

Use quando usuários marcarem respostas como `Parcial` ou `Errado`, ou quando a
tela `/sapiens/training` indicar lacuna.

Fluxo:

1. abrir `/sapiens/training`;
2. revisar `Feedbacks negativos` e `Perguntas sem boa resposta`;
3. rodar o `Robô Treinador` para consolidar padrões;
4. aprovar ou rejeitar propostas;
5. quando aprovada, transformar a proposta em uma das ações oficiais:
   - ajustar artigo `product_help`;
   - criar novo playbook de uso;
   - corrigir ranking/fonte;
   - adicionar alias de intenção;
   - melhorar pergunta de esclarecimento;
6. testar a pergunta original e uma variação equivalente;
7. só então publicar/deployar a melhoria.

Regras:

- a proposta aprovada não altera comportamento automaticamente;
- não registrar solução baseada apenas em uma resposta técnica interna;
- sempre preferir linguagem simples para usuário final;
- nunca usar feedback de uma empresa para revelar fonte de outra empresa;
- toda melhoria em fonte tenant-owned preserva `company_id` e grants.
