# Deterministic Routing Checklist

## Quando ler
Consulte esta referencia ao criar ou revisar fluxos do Sapiens para WhatsApp, web chat ou qualquer canal conversacional operacional.

## Checklist
1. A frase identifica claramente:
   - intencao
   - entidade
   - escopo
   - periodo/status
   - empresa explicita
2. Existe workflow deterministico para o caso?
3. O payload aproveita:
   - usuario da sessao
   - empresa ativa ou empresa citada
   - thread/canal
   - defaults de periodo/status
4. O fluxo evita perguntar o que ja e conhecido?
5. A permissao foi validada antes da execucao?
6. O canal externo funciona sem sessao web autenticada?
7. A resposta final e curta e operacional?
8. O caso so cai em LLM se:
   - nao houver workflow conhecido
   - houver ambiguidade real persistente
   - a tarefa exigir sintese aberta

## Defaults recomendados
### Consulta pessoal de atividades
- usuario: sessao atual
- status default: abertas
- periodo default: inferido da frase
- empresa: explicita > sessao > selecao

### Criacao de atividade
- empresa: explicita > sessao > selecao
- responsavel: usuario atual, salvo pedido contrario
- perguntar apenas projeto, titulo, prazo e obrigatorios reais

### Conclusao de atividade
- exigir identificador claro ou selecao assistida
- confirmar quando a acao for irreversivel ou em lote

## Anti-padroes
- usar LLM para consultas repetitivas
- abrir wizard executivo para pergunta operacional simples
- misturar empresa da sessao com empresa citada pelo usuario
- depender de `current_user` em webhook ou job
- pedir menu/livre quando o usuario ja fez um pedido claro
