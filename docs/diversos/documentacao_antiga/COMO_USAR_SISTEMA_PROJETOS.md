# 🎯 COMO USAR - Sistema de Projetos GRV

**Guia Rápido e Prático**

---

## 📍 ACESSO PRINCIPAL

**URL:** http://127.0.0.1:5002/grv/company/5/projects/projects

---

## 🚀 PASSO A PASSO COMPLETO

### 1️⃣ CRIAR UM PROJETO

**Onde:** Lista de Projetos

1. Clique **"➕ Novo Projeto"**
2. Preencha:
   - **Título:** Ex: "Implantação OKR 2025"
   - **Portfólio:** Escolha "GRV - Portfolio Teste" ou "PEV - Planejamento..."
   - **Responsável:** Selecione um colaborador
   - **OKR:** Selecione um OKR (opcional)
   - **Datas:** Início e Previsão de Término
3. Clique **"Salvar Projeto"**

**Resultado:**
- ✅ Código gerado: `AA.J.15`
- ✅ Card aparece na lista

---

### 2️⃣ GERENCIAR ATIVIDADES DO PROJETO

**Onde:** Card do Projeto

1. Clique **"📋 Gerenciar"** no card
2. Página Kanban abre com 6 colunas

---

### 3️⃣ CRIAR ATIVIDADE

**Onde:** Página Kanban

1. Clique **"➕ Nova Atividade"**
2. Preencha:
   - **O quê?:** Ex: "Definir escopo" (obrigatório)
   - **Quem?:** Ex: "João Silva"
   - **Quando?:** Selecione prazo
   - **Como?:** Descreva o método
   - **Orçamento:** Ex: 5000
3. Clique **"Salvar Atividade"**

**Resultado:**
- ✅ Código gerado: `AA.J.15.01`
- ✅ Card aparece em "📥 Caixa de Entrada"

---

### 4️⃣ ORGANIZAR ATIVIDADES

**Onde:** Kanban

**Arrastar e Soltar:**
1. **Clique e segure** em um card
2. **Arraste** até a coluna desejada
3. **Solte** o card

**Resultado:**
- ✅ Card move para nova coluna
- ✅ Sistema salva automaticamente
- ✅ Notificação aparece

**Colunas Disponíveis:**
- 📥 Caixa de Entrada - Novas atividades
- ⏳ Aguardando - Aguardando dependências
- ⚡ Executando - Trabalho ativo
- ⚠️ Pendências - Bloqueios
- ⏸️ Suspensos - Pausadas
- ✅ Concluídos - Finalizadas

---

### 5️⃣ ADICIONAR REGISTRO DE DIÁRIO

**Onde:** Modal de Edição

1. Clique **"Editar"** em um card
2. Role até **"📝 Registro de Diário"**
3. Clique **"➕ Adicionar Registro"**
4. Digite: Ex: "Reunião de alinhamento realizada"
5. Clique **"Adicionar"**

**Resultado:**
- ✅ Data/hora capturada automaticamente
- ✅ Log aparece no histórico
- ✅ Formato: `📝 Registro  11/10/2025 14:30`

---

### 6️⃣ CONCLUIR ATIVIDADE

**Onde:** Kanban

1. **Arraste** card para **"✅ Concluídos"**
2. ✨ **Popup abre automaticamente**
3. **Data de Conclusão:** 2025-10-11 (editável)
4. **Observação:** Ex: "Concluído com sucesso"
5. Clique **"Confirmar Conclusão"**

**Resultado:**
- ✅ Card em "Concluídos"
- ✅ Log verde criado: `✅ Conclusão  11/10/2025 16:45`
- ✅ Status do projeto atualiza

**Cancelar:**
- Clique **"Cancelar"** no popup
- ✅ Card volta para coluna original

---

### 7️⃣ REABRIR ATIVIDADE CONCLUÍDA

**Onde:** Kanban

1. **Arraste** card **DE** "✅ Concluídos"
2. **Solte** em outra coluna (ex: "Executando")
3. ✨ **Popup de cancelamento abre**
4. **Data do Cancelamento:** 2025-10-11
5. **Motivo:** Ex: "Necessário revisar escopo"
6. Clique **"Confirmar Cancelamento"**

**Resultado:**
- ✅ Card move para nova coluna
- ✅ Log vermelho criado: `↩️ Cancelamento  11/10/2025 17:00`
- ✅ Data de conclusão removida

**Voltar:**
- Clique **"Voltar"** no popup
- ✅ Card permanece em "Concluídos"

---

## 💡 DICAS PRÁTICAS

### ✅ Organize por Fluxo:
1. **Caixa de Entrada** → Triagem inicial
2. **Aguardando** → Dependências externas
3. **Executando** → Trabalho ativo do dia
4. **Pendências** → Bloqueios a resolver
5. **Suspensos** → Pausadas temporariamente
6. **Concluídos** → Arquivo de finalizadas

### ✅ Use Códigos como Referência:
- Em reuniões: "Vamos discutir a `AA.J.15.03`"
- Em emails: "Conforme atividade `AA.J.15.01`"
- Em docs: Referência única e imutável

### ✅ Registre Frequentemente:
- Adicione log após reuniões importantes
- Registre decisões tomadas
- Documente problemas encontrados
- Crie histórico rico para auditoria

### ✅ Preencha Todos os Campos:
- **Quem?** → Responsabilidade clara
- **Quando?** → Gestão de prazos
- **Como?** → Padronização de métodos
- **Orçamento** → Controle financeiro

---

## 🎨 ATALHOS E TRUQUES

### Navegação Rápida:
```
Lista de Projetos → Clicar "Gerenciar" → Kanban abre
Kanban → Clicar "← Voltar" → Lista de Projetos
```

### Edição Rápida:
```
Card no Kanban → Clicar "Editar" → Modal abre
Modal → Editar campos → "Salvar" → Kanban atualiza
```

### Movimentação Eficiente:
```
Múltiplas atividades → Arrastar uma a uma
Ou: Editar e mudar status manualmente
```

---

## ⚠️ ATENÇÕES IMPORTANTES

### ❗ Sempre Confirme Conclusões:
- Popup garante que conclusão não é acidental
- Permite documentar motivo da conclusão
- Registra data exata

### ❗ Documente Reaberturas:
- Popup de cancelamento evita retrabalho silencioso
- Força registro do motivo
- Cria auditoria completa

### ❗ Códigos São Imutáveis:
- Uma vez gerados, não mudam
- Use como referência permanente
- Sequencial por empresa

### ❗ Logs São Cronológicos:
- Exibidos do mais recente para o mais antigo
- Timestamp preserva ordem exata
- Não podem ser editados após criação

---

## 🧪 TESTE RÁPIDO (5 Minutos)

### Passo 1: (1 min)
```
Acesse: http://127.0.0.1:5002/grv/company/5/projects/projects
Clique: "➕ Novo Projeto"
Preencha: Título = "Teste Rápido"
Salve
```

### Passo 2: (1 min)
```
Clique: "📋 Gerenciar" no projeto criado
Veja: 6 colunas vazias do Kanban
```

### Passo 3: (1 min)
```
Clique: "➕ Nova Atividade"
Preencha: O quê? = "Teste Atividade 1"
Salve
Veja: Card em "Caixa de Entrada" com código AA.J.X.01
```

### Passo 4: (1 min)
```
Arraste: Card para "Executando"
Veja: Card move, notificação aparece
```

### Passo 5: (1 min)
```
Arraste: Card para "Concluídos"
Popup: Aparece pedindo confirmação
Confirme: Com data de hoje
Veja: Card em "Concluídos" com log verde
```

**🎉 Teste completo em 5 minutos!**

---

## 📞 SUPORTE

### Documentação Técnica:
- `SISTEMA_ATIVIDADES_KANBAN.md`
- `SISTEMA_LOG_DIARIO_ATIVIDADES.md`
- `RESUMO_IMPLEMENTACAO_PROJETOS_GRV.md`

### Guias de Uso:
- `GUIA_RAPIDO_ATIVIDADES_KANBAN.md`
- `COMO_USAR_SISTEMA_PROJETOS.md` (este arquivo)

### Resumo da Sessão:
- `RESUMO_FINAL_SESSAO_PROJETOS.md`

---

**Versão:** 1.0  
**Data:** 11/10/2025  
**Status:** ✅ Produção  
**Pronto para uso!** 🚀

