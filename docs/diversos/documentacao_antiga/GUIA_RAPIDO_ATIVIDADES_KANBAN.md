# 🚀 Guia Rápido - Sistema de Atividades com Kanban

## 📍 Acesso Rápido

### Passo 1: Lista de Projetos
**URL:** http://127.0.0.1:5002/grv/company/5/projects/projects

### Passo 2: Gerenciar Projeto
**Ação:** Clique no botão **"📋 Gerenciar"** em qualquer card de projeto

### Passo 3: Kanban de Atividades
**URL:** http://127.0.0.1:5002/grv/company/5/projects/{project_id}/manage

---

## ⚡ Ações Rápidas

### ➕ Criar Atividade

1. Clique em **"➕ Nova Atividade"**
2. Preencha:
   - **O quê?** (obrigatório) - Ex: "Definir escopo"
   - **Quem?** - Ex: "João Silva"
   - **Quando?** - Selecione data
   - **Como?** - Descreva o método
   - **Orçamento** - Ex: 5000
   - **Observações** - Informações extras
3. Clique **"Salvar Atividade"**

**Resultado:**
- ✅ Código gerado: `AA.J.12.01`
- ✅ Card aparece em "Caixa de Entrada"

---

### 🔄 Mover Atividade

**Método 1 - Drag and Drop:**
1. **Clique e segure** no card
2. **Arraste** até a coluna desejada
3. **Solte** o card

**Resultado:**
- ✅ Card move para nova coluna
- ✅ Notificação aparece
- ✅ Contador atualiza

**Colunas Disponíveis:**
- 📥 Caixa de Entrada
- ⏳ Aguardando
- ⚡ Executando
- ⚠️ Pendências
- ⏸️ Suspensos
- ✅ Concluídos

---

### ✏️ Editar Atividade

1. Clique em **"Editar"** no card
2. Modifique os campos
3. Clique **"Salvar Atividade"**

**Resultado:**
- ✅ Dados atualizados
- ✅ Card permanece na mesma coluna
- ✅ Código não muda

---

### 🗑️ Excluir Atividade

1. Clique em **"Excluir"** no card
2. Confirme a exclusão

**Resultado:**
- ✅ Card removido
- ✅ Contador atualizado
- ✅ Notificação de sucesso

---

## 🎯 Exemplo Prático

### Cenário: Projeto "Implantação OKR"

**Código do Projeto:** `AA.J.15`

#### Atividades Criadas:

| Código | O quê? | Quem? | Quando? | Orçamento | Coluna |
|--------|--------|-------|---------|-----------|--------|
| `AA.J.15.01` | Definir escopo | Ana Silva | 15/11/2025 | R$ 5.000 | Executando |
| `AA.J.15.02` | Mapear processos | João Costa | 30/11/2025 | R$ 8.000 | Aguardando |
| `AA.J.15.03` | Treinar equipe | Maria Santos | 15/12/2025 | R$ 12.000 | Caixa de Entrada |
| `AA.J.15.04` | Implantar sistema | Pedro Alves | 31/12/2025 | R$ 25.000 | Pendências |

#### Cálculos no Card do Projeto:

- **Orçamento Total:** R$ 50.000,00 (soma de todas)
- **Prazo Previsto:** 31/12/2025 (maior data)
- **Status:** Em andamento (nenhuma concluída ainda)
- **Atividades:** 4 total, 0 concluídas, 0 atrasadas

---

## 📋 Estrutura do Código

### Hierarquia:
```
Empresa: AA
  └─ Projeto: J.15
      ├─ Atividade: 01  → Código completo: AA.J.15.01
      ├─ Atividade: 02  → Código completo: AA.J.15.02
      ├─ Atividade: 03  → Código completo: AA.J.15.03
      └─ Atividade: 04  → Código completo: AA.J.15.04
```

### Formato:
```
{CLIENT_CODE}.J.{PROJECT_SEQ}.{ACTIVITY_SEQ:02d}
     AA      . J .    15     .       01

Onde:
- AA = Código da empresa
- J = Tipo (Projeto)
- 15 = Número do projeto
- 01 = Número da atividade (2 dígitos)
```

---

## 💡 Dicas de Uso

### ✅ Boas Práticas:

1. **Organize pelo Fluxo:**
   - Caixa de Entrada → Atividades recém-cadastradas
   - Aguardando → Aguardando recursos/aprovações
   - Executando → Trabalho ativo
   - Pendências → Bloqueios a resolver
   - Suspensos → Pausadas temporariamente
   - Concluídos → Finalizadas

2. **Use Códigos como Referência:**
   - Em reuniões: "Vamos discutir a AA.J.15.03"
   - Em documentos: "Conforme atividade AA.J.15.01"

3. **Preencha Todos os Campos:**
   - Quem? → Responsabilidade clara
   - Quando? → Gestão de prazos
   - Orçamento → Controle financeiro

4. **Mova Regularmente:**
   - Mantenha o Kanban atualizado
   - Reflita o status real do trabalho

---

## 🔄 Atalhos de Teclado (Futuro)

Planejado para futuras versões:
- `N` - Nova atividade
- `E` - Editar atividade selecionada
- `Del` - Excluir atividade selecionada
- `→` - Mover para próxima coluna
- `←` - Mover para coluna anterior

---

## 📊 Relatórios (Futuro)

### Métricas Planejadas:

1. **Tempo Médio por Coluna:**
   - Quanto tempo as atividades ficam em cada estágio

2. **Taxa de Conclusão:**
   - % de atividades concluídas vs total

3. **Distribuição de Orçamento:**
   - Quanto está em cada coluna

4. **Atividades Atrasadas:**
   - Lista de atividades com prazo vencido

5. **Responsável mais Ativo:**
   - Quem tem mais atividades

---

## ❓ Solução de Problemas

### Atividade não aparece após criar
- ✅ Verifique a coluna "Caixa de Entrada"
- ✅ Atualize a página (F5)

### Não consigo arrastar o card
- ✅ Certifique-se de clicar no card (não nos botões)
- ✅ Use navegador moderno (Chrome, Edge, Firefox)

### Card volta para coluna original após arrastar
- ✅ Erro ao atualizar servidor
- ✅ Verifique console do navegador (F12)
- ✅ Tente novamente

### Código da atividade aparece como "null"
- ✅ Projeto precisa ter código válido
- ✅ Verifique se empresa tem `client_code`

---

**Versão:** 1.0  
**Data:** 11/10/2025  
**Suporte:** Sistema de Gestão de Projetos GRV

