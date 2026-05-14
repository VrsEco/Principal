# Runbook de Instalação e Ativação do Sapiens Cliente no CLI v1

Status: oficial  
Escopo: instalação guiada e ativação do `Sapiens Cliente` em clientes CLI / MCP compatíveis

## 1. Objetivo

Descrever o passo a passo oficial para instalar e ativar o `Sapiens Cliente` em um cliente compatível com MCP, usando:
- token MCP pessoal
- configuração guiada
- `surface user`
- `Squad Cliente` como família canônica
- `harness_coordenador_cliente_v1` como ponto inicial de entrada

Este runbook foi feito para:
- usuário final não técnico
- implantação assistida
- suporte operacional
- validação de que a conexão ficou correta

---

## 2. Resultado esperado

Ao final deste runbook, o usuário deve ter:
- uma conexão MCP ativa apontando para o APP32
- a experiência visível chamada `Sapiens Cliente`
- acesso ao `Squad Cliente`
- entrada inicial pelo `Harness Coordenador do Squad Cliente`
- possibilidade de chamar o ambiente por:
  - `sapiens cliente on`
  - ou pela entrada criada no cliente compatível

---

## 3. Pré-requisitos

Antes de instalar, confirme:

1. o usuário possui conta ativa no APP32
2. o usuário possui acesso à empresa correta
3. o usuário está autorizado ao `Squad Cliente`
4. o usuário consegue acessar a tela `/profile` em produção
5. o cliente MCP desejado está entre os cenários suportados:
   - Claude
   - Codex
   - Antigravity
   - outro cliente MCP compatível

---

## 4. Parâmetros canônicos da instalação

Para o `Sapiens Cliente`, os parâmetros oficiais são:

- experiência visível: `Sapiens Cliente`
- família canônica: `Squad Cliente`
- profile: `squad_cliente`
- surface: `user`
- harness inicial: `harness_coordenador_cliente_v1`
- label do harness inicial: `Harness Coordenador do Squad Cliente`

### URL base
- `https://app.gestaoversus.com.br/mcp/user/`

### Comando canônico sugerido
- `sapiens cliente on`

---

## 5. Fluxo oficial de instalação

## 5.1 Abrir a tela de perfil

O usuário deve acessar:
- `/profile`

Na interface, deve entrar na aba:
- `Instalar Squad`

---

## 5.2 Escolher o cliente

Na tela, o usuário deve selecionar o cliente alvo:
- Claude
- Codex
- Antigravity
- Outro cliente MCP

### Regra
Se houver dúvida, usar o cliente real em que o usuário vai operar no dia a dia.

---

## 5.3 Confirmar o squad

Para usuário cliente, operador ou colaborador comum, a opção visível deve ser:
- `Sapiens Cliente`

### Regra
O usuário final do cliente não deve instalar:
- `Sapiens Consultor`
- `Sapiens Engenharia`

Essas opções pertencem a outros perfis de acesso.

---

## 5.4 Escolher a empresa padrão

Se o usuário tiver mais de uma empresa acessível, ele deve selecionar a empresa correta.

### Regra
A empresa escolhida determina o `company_id` padrão da conexão.

---

## 5.5 Gerar o token MCP pessoal

Na parte final da página, o usuário deve:
1. gerar ou renovar o token
2. copiar o token no pop-up
3. guardar o token antes de fechar a janela

### Aviso oficial
O token:
- não deve ser exposto em canais inseguros
- não será mostrado novamente após o fechamento do pop-up
- será solicitado durante a instalação

---

## 5.6 Gerar o código para IA

Depois do token, o usuário deve usar:
- `Gerar código para IA`

Esse conteúdo é o prompt guiado para o cliente escolhido configurar a conexão MCP com:
- nome da experiência
- URL
- profile
- surface
- harness inicial
- Bearer token
- bootstrap operacional resumido do Squad Cliente

### Opções auxiliares
Também podem existir:
- `Copiar`
- `Modo avançado`

---

## 6. Fluxo guiado no cliente MCP

## 6.1 Colar o código para IA

No cliente MCP escolhido, o usuário deve colar o código gerado.

### O que a IA cliente deve fazer
Ela deve:
1. verificar se suporta MCP
2. verificar se suporta configuração automática
3. criar a conexão
4. criar a entrada visível `Sapiens Cliente`, quando suportado
5. configurar o alias:
   - `sapiens cliente on`
6. ativar a conexão

---

## 6.2 Se o cliente pedir o token

Quando solicitado:
- colar o token MCP pessoal gerado na tela `/profile`

### Regra oficial
O token deve ser solicitado pelo instalador somente no momento correto da configuração, de forma interativa e segura, sem exigir que o usuário o coloque antecipadamente em linha de comando.

---

## 6.3 Se o cliente não suportar automação total

Se o cliente suportar MCP, mas não suportar criação automática de entrada/atalho:
- manter a conexão ativa
- usar o `Modo avançado`
- copiar a configuração técnica manual

Se o cliente não suportar MCP:
- a instalação guiada deve ser interrompida
- o usuário deve ser informado de que aquele cliente não suporta o `Sapiens Cliente` automaticamente

---

## 7. Configuração técnica de referência

O formato canônico esperado é:

```json
{
  "name": "Sapiens Cliente",
  "transport": "http",
  "url": "https://app.gestaoversus.com.br/mcp/user/?company_id=ID_DA_EMPRESA",
  "metadata": {
    "profile": "squad_cliente",
    "profile_label": "Squad Cliente",
    "experience_label": "Sapiens Cliente",
    "surface": "user",
    "harness_key": "harness_coordenador_cliente_v1",
    "harness_label": "Harness Coordenador do Squad Cliente"
  },
  "headers": {
    "Authorization": "Bearer TOKEN_MCP_PESSOAL"
  }
}
```

### Observação
O `company_id` pode aparecer na URL quando houver empresa padrão definida.

---

## 8. Ativação esperada após conectar

Uma vez ativa, a experiência deve iniciar no:
- `Squad Cliente`
- com entrada pelo `Harness Coordenador do Squad Cliente`

### Sequência inicial esperada
As primeiras tools esperadas são:
- `describe_app32_squad_runtime_tool`
- `list_user_app32_capabilities`
- `describe_app32_profile_contracts_tool`
- `describe_app32_surface_playbooks_tool`

### Leitura do bootstrap
Logo após conectar, o cliente deve usar `describe_app32_squad_runtime_tool` para ler:
- agente de entrada
- especialistas oficiais da fase 1
- ordem de roteamento
- regra de economia de tokens
- regra de escalonamento

---

## 9. Critérios de validação

Considere a instalação bem-sucedida quando:

1. a conexão MCP responder sem erro
2. a surface usada for `user`
3. o profile reportado for `squad_cliente`
4. o harness inicial for `harness_coordenador_cliente_v1`
5. a empresa padrão estiver correta
6. as tools de startup responderem
7. o usuário conseguir chamar o ambiente como `Sapiens Cliente`

---

## 10. Erros comuns e tratamento

## 10.1 Token inválido

Sinais:
- autenticação falha
- resposta 401

Ação:
1. voltar ao `/profile`
2. renovar token
3. copiar o novo token
4. atualizar a conexão no cliente MCP

---

## 10.2 Empresa errada

Sinais:
- contexto não corresponde à empresa desejada
- dados aparentam “sumidos”

Ação:
1. revisar a empresa padrão selecionada
2. regenerar o código para IA com a empresa correta
3. atualizar a conexão

---

## 10.3 Cliente não suporta automação

Sinais:
- a IA do cliente informa que não consegue configurar automaticamente

Ação:
1. abrir o `Modo avançado`
2. copiar a configuração técnica
3. configurar manualmente, se o cliente suportar MCP

---

## 10.4 Perfil errado

Sinais:
- o usuário vê squad incorreto
- o cliente tenta instalar `Sapiens Consultor` ou `Sapiens Engenharia`

Ação:
1. revisar o perfil do usuário
2. confirmar a lista de squads permitidos
3. reinstalar com `Sapiens Cliente`

---

## 11. Regras de segurança

Durante a instalação:
- não compartilhar token em canal inseguro
- não reutilizar token antigo depois de renovação
- não instalar o `Squad Cliente` em cliente de terceiro sem autorização
- não trocar o profile manualmente para outro squad fora do perfil permitido

---

## 12. Regra de economia de operação

Este runbook deve preservar a filosofia oficial do `Squad Cliente`:
- experiência simples
- instalação guiada
- menor atrito possível
- custo cognitivo baixo

### Regra curta
O processo de instalação do `Sapiens Cliente` deve ser simples como a experiência que ele promete entregar.

---

## 13. Referências canônicas

Este runbook foi consolidado a partir de:
- `C:\GestaoVersus\app32\app32\services\user_mcp_token_service.py`
- `C:\GestaoVersus\app32\app32\services\mcp_connection_snippet_service.py`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\arquitetura_oficial_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\agentes_oficiais_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\harnesses_oficiais_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\matriz_autonomia_agentes_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\playbooks\squad_cliente\playbook_handoff_escalonamento_squad_cliente_v1.md`
