# Guia rápido — conectar o Gestão Versus ao Claude (mcp-versus)

Para o usuário do cliente. Leva cerca de cinco minutos. Você não instala o código do APP32.

## 1. Conectar
1. Cadastre o servidor MCP `mcp-versus` com a URL `https://app.gestaoversus.com.br/mcp/pilot/`.
2. Ao conectar, o navegador abre a tela de login do Gestão Versus. Entre com o seu usuário e clique em **Autorizar** uma única vez.
3. Volte ao Claude e digite `/mcp`. O `mcp-versus` deve aparecer com o sinal ✓ e ferramentas listadas.

## 2. Ativar o atendimento
Numa conversa nova, digite: **Squad cliente on**.

O Claude responde com "🦅 Squad Cliente ON", identifica a sua empresa e pergunta a tarefa. As permissões são as do seu usuário no Gestão Versus e da empresa autorizada. O Claude não faz alterações sensíveis sem a sua autorização.

## 3. Se algo não funcionar
| O que você vê | O que significa | O que fazer |
|---|---|---|
| `mcp-versus` conectando ("pending") | O servidor ainda está conectando | Aguarde alguns segundos e tente de novo |
| `mcp-versus` ✓ mas **0 ferramentas** | Login não concluído ou vencido | `/mcp`, abra o `mcp-versus` e autentique; se continuar, abra uma conversa nova |
| Erro **502** ou **503** | Serviço do Gestão Versus indisponível no momento | Não é falha sua. Tente em alguns minutos; se persistir, avise a Versus |
| "company_id obrigatório" | A empresa não foi informada | Diga o nome ou prefixo da empresa; o Claude passa a usá-la |
| Login: "Cookie de reinício de login não encontrado" | A tela de autorização expirou ou foi aberta em outro navegador | Volte ao Claude e conecte de novo, no mesmo navegador, sem clicar duas vezes |
| O Claude diz que não conhece "Squad cliente on" | Conector não autenticado | Refaça o passo 1 e abra uma conversa nova |

## Para a Versus (suporte)
- `connected` com 0 ferramentas é falta de login OAuth, não defeito do servidor; sem token o endpoint responde 401.
- As instruções do Squad Cliente chegam pelo `initialize` do servidor, só depois de autenticar.
- Referências: `.ai/claude-squad-cliente.md`, `docs/playbooks/playbook_onboarding_oauth_controlado_clientes_mcp_v1.md`.
