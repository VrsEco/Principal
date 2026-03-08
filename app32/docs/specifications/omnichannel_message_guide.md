# Guia de Mensagens Omnichannel — Sapiens IA

## Objetivo
Garantir consistência de experiência entre Web, WhatsApp, Telegram e Instagram, mantendo o mesmo fluxo conversacional e variando apenas a apresentação final por canal.

## Princípios
1. **Mesmo fluxo, múltiplos canais** — descoberta, coleta, confirmação e execução devem ser iguais.
2. **Mensagem curta e operacional** — cada bloco deve conduzir a uma ação.
3. **Um próximo passo explícito** — sempre orientar o usuário sobre como responder.
4. **Legibilidade de chat** — listas, subtítulos, CTAs e espaçamento previsível.
5. **Segurança operacional** — confirmação clara antes de executar ações sensíveis.

## Família Chat
Aplica-se a:
- WhatsApp
- Telegram
- Instagram

### Regras
- Heading forte no topo.
- Callout com contexto (info, warning, success, danger).
- Lista numerada para escolhas.
- Bloco `Proximo passo:` antes da ação esperada.
- Instrução curta com exemplo de resposta.

## Diferenças por canal
### WhatsApp / Instagram
- Heading em `*negrito*`.
- Bullets compactos com `•`, `◦` e `▪`.
- CTA sempre em linguagem curta.

### Telegram
- Heading em HTML (`<b>...</b>`).
- Bullets compactos iguais à família chat.
- Sanitização HTML obrigatória.

## Tipos de mensagem
### Confirmação
- Cabeçalho: `Confirme a operacao`
- Resumo do fluxo selecionado
- Dados consolidados
- Bloco `Proximo passo:` com `sim` / `nao`

### Coleta de campos
- Explicar o que falta
- Mostrar somente dados pendentes
- Exemplo de preenchimento
- Bloco `Proximo passo:`

### Seleção assistida
- Explicar o contexto da escolha
- Mostrar opções em formato numerado
- Exemplo de resposta simples

### Erros e fallback
- Mensagem objetiva
- Sem texto excessivo
- Indicar alternativa segura

## Observações da auditoria inicial
- Telegram estava sem heading forte no parse mode HTML.
- Família chat tinha diferenças excessivas entre prompts de confirmação e coleta.
- Instagram usa a mesma família visual de WhatsApp, mas ainda precisa convergir melhor no runtime operacional.
