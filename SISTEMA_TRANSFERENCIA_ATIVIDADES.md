# 🔄 Sistema de Transferência de Atividades entre Projetos

## 📋 Visão Geral

Foi implementada uma funcionalidade completa para transferir atividades de um projeto para outro no sistema GRV. Esta funcionalidade permite reorganizar atividades entre projetos de forma segura e mantém a integridade dos dados.

---

## ✨ Funcionalidades Implementadas

### 1. **API de Transferência**
- **Endpoint:** `POST /api/companies/<id>/projects/<id>/activities/<id>/transfer`
- **Funcionalidade:** Transfere uma atividade de um projeto para outro
- **Validações:**
  - Verifica se o projeto de destino existe
  - Impede transferência para o mesmo projeto
  - Gera novo código automático para a atividade no projeto de destino
  - Reseta o estágio para "Caixa de Entrada" no projeto de destino

### 2. **API de Listagem de Projetos**
- **Endpoint:** `GET /api/companies/<id>/projects`
- **Funcionalidade:** Lista todos os projetos disponíveis para transferência
- **Retorna:** ID, nome, código, portfólio e responsável de cada projeto

### 3. **API de Informações do Projeto**
- **Endpoint:** `GET /api/companies/<id>/projects/<id>/info`
- **Funcionalidade:** Busca informações básicas de um projeto específico
- **Usado para:** Exibir nomes dos projetos no histórico de transferências

### 4. **Interface de Transferência**
- **Botão "Transferir"** em cada card de atividade
- **Modal de Transferência** com:
  - Informações da atividade selecionada
  - Dropdown com projetos disponíveis
  - Campo para observação opcional
  - Validação de campos obrigatórios
  - **Histórico de Transferências** com barra de rolagem

### 5. **Histórico de Transferências**
- **Registro automático** de todas as transferências
- **Exibição no modal** com informações completas:
  - Data e hora da transferência
  - Códigos antigo e novo
  - Nomes dos projetos de origem e destino
  - Observação/motivo da transferência
- **Barra de rolagem** para histórico extenso
- **Registro como diário** - cada transferência é salva como log na atividade

### 6. **Registro Diário de Transferências**
- **Log automático** adicionado aos logs da atividade
- **Tipo:** `transfer` para identificar transferências
- **Informações:** Projetos de origem e destino, códigos, observação
- **Visível** na seção de logs/diário da atividade

---

## 🎯 Como Usar

### Passo 1: Acessar o Kanban
1. Vá para **GRV > Projetos > [Seu Projeto] > Gerenciar**
2. Visualize as atividades no Kanban

### Passo 2: Transferir Atividade
1. **Clique no botão "Transferir"** no card da atividade desejada
2. **Selecione o projeto de destino** no dropdown
3. **Adicione uma observação** (opcional) explicando o motivo da transferência
4. **Clique em "Transferir Atividade"**

### Passo 3: Confirmação
- A atividade será removida do projeto atual
- Será adicionada ao projeto de destino com novo código
- O estágio será resetado para "Caixa de Entrada"
- Uma notificação confirmará o sucesso da operação

---

## 🔧 Detalhes Técnicos

### Código Automático
- **Formato:** `{EMPRESA}.J.{PROJETO}.{SEQUENCIA}`
- **Exemplo:** `AA.J.15.03` → `AA.J.20.01`
- A sequência é recalculada automaticamente no projeto de destino

### Reset de Status
Ao transferir uma atividade:
- **Estágio:** Resetado para `inbox` (Caixa de Entrada)
- **Status:** Resetado para `pending`
- **Data de Conclusão:** Limpa (se existia)
- **Código:** Regenerado automaticamente

### Validações de Segurança
- ✅ Verifica existência do projeto de origem
- ✅ Verifica existência do projeto de destino
- ✅ Impede transferência para o mesmo projeto
- ✅ Valida campos obrigatórios
- ✅ Tratamento de erros com rollback

---

## 📊 Estrutura de Dados

### Request de Transferência
```json
{
  "target_project_id": 123,
  "note": "Motivo da transferência"
}
```

### Response de Sucesso
```json
{
  "success": true,
  "message": "Atividade transferida com sucesso para o projeto de destino.",
  "new_code": "AA.J.20.01"
}
```

---

## 🎨 Interface Visual

### Botão de Transferir
- **Cor:** Roxo (`#8b5cf6`)
- **Posição:** Entre "Editar" e "Excluir"
- **Ícone:** 🔄 Transferir

### Modal de Transferência
- **Título:** "🔄 Transferir Atividade"
- **Campos:**
  - Informações da atividade (somente leitura)
  - Dropdown de projetos de destino
  - Campo de observação opcional
  - **Histórico de Transferências** (com barra de rolagem)
- **Botões:** Cancelar | Transferir Atividade
- **Cores:** Texto em preto para melhor legibilidade

---

## 🚀 Casos de Uso

### Caso 1: Reorganização de Projetos
- **Situação:** Projeto foi dividido em dois
- **Ação:** Transferir atividades relacionadas para o novo projeto
- **Resultado:** Atividades organizadas corretamente

### Caso 2: Mudança de Prioridades
- **Situação:** Atividade mudou de prioridade
- **Ação:** Transferir para projeto com maior prioridade
- **Resultado:** Atividade aparece na caixa de entrada do novo projeto

### Caso 3: Correção de Erro
- **Situação:** Atividade foi criada no projeto errado
- **Ação:** Transferir para o projeto correto
- **Resultado:** Atividade movida sem perda de dados

---

## ⚠️ Considerações Importantes

### Limitações
- ❌ Não é possível transferir atividades concluídas (recomendação)
- ❌ Não é possível transferir para projetos de outras empresas
- ❌ Não é possível transferir múltiplas atividades simultaneamente

### Recomendações
- ✅ Sempre adicione uma observação explicando o motivo
- ✅ Verifique se o projeto de destino está ativo
- ✅ Confirme que a atividade faz sentido no novo projeto
- ✅ Notifique o responsável da atividade sobre a transferência

---

## 🔍 Monitoramento

### Logs de Transferência
- Todas as transferências são registradas no banco de dados
- Timestamp automático de quando a transferência foi realizada
- Possibilidade de rastrear histórico de movimentações

### Notificações
- ✅ Sucesso: "Atividade transferida com sucesso"
- ❌ Erro: Mensagem específica do problema
- ℹ️ Info: Novo código gerado para a atividade

---

## 📝 Exemplo Prático

**Situação:** Transferir atividade "Definir escopo" do Projeto A para Projeto B

1. **Acessar:** GRV > Projetos > Projeto A > Gerenciar
2. **Clicar:** Botão "Transferir" na atividade "Definir escopo"
3. **Selecionar:** "Projeto B (AA.J.20)" no dropdown
4. **Observação:** "Transferindo para melhor organização do escopo"
5. **Confirmar:** Clicar em "Transferir Atividade"

**Resultado:**
- ✅ Atividade removida do Projeto A
- ✅ Atividade adicionada ao Projeto B com código `AA.J.20.01`
- ✅ Estágio resetado para "Caixa de Entrada"
- ✅ Notificação de sucesso exibida

---

## 🎉 Conclusão

A funcionalidade de transferência de atividades está completamente implementada e pronta para uso. Ela oferece uma forma segura e intuitiva de reorganizar atividades entre projetos, mantendo a integridade dos dados e fornecendo feedback claro ao usuário.

**Status:** ✅ **IMPLEMENTADO E FUNCIONAL**
