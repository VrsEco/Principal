# 🧪 Guia de Teste: Botão Nova Atividade

**Data:** 24/10/2025

---

## ✅ CHECKLIST DE TESTES

### 1. **Teste de Visibilidade do Botão**

| Página | URL Exemplo | Botão Visível? |
|--------|-------------|----------------|
| Dashboard Principal | `/main` | ☐ Sim |
| PEV Dashboard | `/pev/dashboard` | ☐ Sim |
| GRV Dashboard | `/grv/dashboard` | ☐ Sim |
| Planejamento Novo Negócio | `/plans/{plan_id}?company_id=25` | ☐ Sim |
| Planejamento Clássico | `/plans/{plan_id}/dashboard` | ☐ Sim |
| GRV - Portfólios | `/company/25/portfolios` | ☐ Sim |
| GRV - Projetos | `/company/25/projects/42/manage` | ☐ Sim |
| Gestão de Reuniões | `/meetings/company/25` | ☐ Sim |
| Minhas Atividades | `/my-work/` | ☐ Sim |
| Configurações | `/system/configs` | ☐ Sim |

**Como testar:**
1. Acesse cada página listada acima
2. Verifique se o botão "+ Nova Atividade" está visível no cabeçalho
3. O botão deve estar ao lado dos links PEV/GRV/etc

---

### 2. **Teste de Detecção Automática de Projeto**

#### Teste 2.1: PEV - Planejamento com Projeto Vinculado

**Pré-requisito:** Ter um planejamento PEV criado com projeto vinculado

**Passos:**
1. Acesse a página do planejamento (ex: `/plans/expansao-2025?company_id=25`)
2. Clique no botão "+ Nova Atividade"
3. Observe o campo "📁 Projeto"

**Resultado esperado:**
- ✅ Select deve estar preenchido com o projeto vinculado ao plano
- ✅ Badge "✓ Detectado" deve estar visível (verde)
- ✅ Mensagem: "✓ Projeto detectado automaticamente da página atual. Você pode alterá-lo se necessário." (verde)

#### Teste 2.2: GRV - Projeto Específico

**Pré-requisito:** Ter um projeto GRV criado

**Passos:**
1. Acesse a página de gerenciamento do projeto (ex: `/company/25/projects/42/manage`)
2. Clique no botão "+ Nova Atividade"
3. Observe o campo "📁 Projeto"

**Resultado esperado:**
- ✅ Select deve estar preenchido com o projeto atual
- ✅ Badge "✓ Detectado" deve estar visível
- ✅ Label do projeto deve mostrar: "Nome do Projeto (Tipo: Planejamento)"

#### Teste 2.3: Reuniões - Sem Projeto Específico

**Passos:**
1. Acesse a página de reuniões (ex: `/meetings/company/25`)
2. Clique no botão "+ Nova Atividade"
3. Observe o campo "📁 Projeto"

**Resultado esperado:**
- ✅ Select deve listar TODOS os projetos da empresa
- ⚠️ Badge "✓ Detectado" NÃO deve estar visível
- ✅ Mensagem: "Selecione o projeto para vincular esta atividade." (cinza)
- ✅ Opção padrão: "Selecione um projeto..."

#### Teste 2.4: Página sem Company ID

**Passos:**
1. Acesse uma página que não tenha company_id (se existir)
2. Clique no botão "+ Nova Atividade"
3. Observe o campo "📁 Projeto"

**Resultado esperado:**
- ⚠️ Select deve mostrar: "⚠️ Empresa não detectada - acesse via página do planejamento"

---

### 3. **Teste de Alteração de Projeto**

**Passos:**
1. Acesse uma página com projeto detectado automaticamente
2. Clique no botão "+ Nova Atividade"
3. Verifique que o projeto está pré-selecionado
4. Clique no select e escolha OUTRO projeto
5. Preencha os campos obrigatórios (O que fazer?)
6. Clique em "Adicionar Atividade"

**Resultado esperado:**
- ✅ A atividade deve ser criada no projeto ALTERADO (não no detectado)
- ✅ Mensagem de sucesso: "✅ Atividade adicionada ao projeto com sucesso!"

---

### 4. **Teste de Validação**

#### Teste 4.1: Projeto não selecionado

**Passos:**
1. Abra o modal de Nova Atividade
2. Deixe o campo "Projeto" vazio (ou selecione "Selecione um projeto...")
3. Preencha "O que fazer?"
4. Clique em "Adicionar Atividade"

**Resultado esperado:**
- ❌ Erro: "❌ Por favor, selecione um projeto para a atividade."
- ✅ Foco deve voltar para o campo Projeto

#### Teste 4.2: Descrição vazia

**Passos:**
1. Abra o modal de Nova Atividade
2. Selecione um projeto
3. Deixe "O que fazer?" VAZIO
4. Clique em "Adicionar Atividade"

**Resultado esperado:**
- ❌ Validação HTML5 deve impedir o envio (campo é required)

---

### 5. **Teste de Criação de Atividade**

**Pré-requisito:** Ter pelo menos 1 projeto criado na empresa

**Passos:**
1. Acesse qualquer página do sistema
2. Clique em "+ Nova Atividade"
3. Selecione um projeto
4. Preencha:
   - **O que fazer?** "Testar botão nova atividade"
   - **Quem?** "Equipe de Testes"
   - **Quando?** 30/10/2025
   - **Como?** "Seguir checklist de testes"
   - **Observações** "Teste realizado em 24/10/2025"
5. Clique em "Adicionar Atividade"

**Resultado esperado:**
- ✅ Mensagem: "✅ Atividade adicionada ao projeto com sucesso!"
- ✅ Modal deve fechar automaticamente
- ✅ Se estiver na página do projeto (Kanban), a página deve recarregar

**Validar no Banco:**
1. Acesse a página do projeto onde adicionou a atividade
2. Verifique se a atividade aparece no Kanban/Lista
3. Confirme que todos os campos foram salvos corretamente

---

### 6. **Teste de Lista de Projetos**

**Pré-requisito:** Ter múltiplos projetos (PEV e GRV) na empresa

**Passos:**
1. Abra o modal de Nova Atividade em qualquer página
2. Clique no select "📁 Projeto"
3. Observe a lista de projetos

**Resultado esperado:**
- ✅ Deve listar TODOS os projetos da empresa
- ✅ Formato esperado: "Nome do Projeto (Tipo: Nome do Planejamento)"
  - Exemplo: "Expansão 2025 (PEV: Planejamento Estratégico)"
  - Exemplo: "Implantação ERP (GRV: Portfolio Tecnologia)"
- ✅ Projetos devem estar ordenados alfabeticamente
- ✅ Opção vazia no topo: "Selecione um projeto..."

---

## 🔍 CENÁRIOS ESPECIAIS

### Cenário 1: Empresa sem Projetos

**Passos:**
1. Acesse uma empresa que NÃO tem projetos cadastrados
2. Clique em "+ Nova Atividade"

**Resultado esperado:**
- ⚠️ Select deve mostrar: "Nenhum projeto disponível"
- ✅ Não deve permitir criar atividade sem projeto

### Cenário 2: Múltiplos Projetos do Mesmo Planejamento

**Pré-requisito:** Ter 2+ projetos vinculados ao mesmo planejamento

**Passos:**
1. Acesse a página do planejamento
2. Clique em "+ Nova Atividade"
3. Verifique o select de projetos

**Resultado esperado:**
- ✅ Deve pré-selecionar o PRIMEIRO projeto encontrado vinculado ao plano
- ✅ Todos os outros projetos devem estar disponíveis para seleção

### Cenário 3: Navegação entre Páginas

**Passos:**
1. Abra o modal em uma página (ex: Planejamento A)
2. Observe o projeto detectado
3. Feche o modal
4. Navegue para outra página (ex: Planejamento B)
5. Abra o modal novamente

**Resultado esperado:**
- ✅ Deve detectar o projeto da NOVA página (Planejamento B)
- ✅ Não deve "lembrar" o projeto da página anterior

---

## 📊 RESULTADO ESPERADO GERAL

Após todos os testes:
- ✅ Botão sempre visível em TODAS as páginas
- ✅ Detecção automática funciona em PEV e GRV
- ✅ Usuário pode alterar o projeto sugerido
- ✅ Validação impede criação sem projeto
- ✅ Atividades são criadas no projeto correto
- ✅ Feedback visual claro (badge, mensagens)

---

## 🐛 REPORTAR PROBLEMAS

Se encontrar problemas durante os testes, anote:

| Problema | Página | Passos para Reproduzir | Resultado Esperado | Resultado Obtido |
|----------|--------|------------------------|-------------------|------------------|
| Exemplo: Botão não aparece | /configs | 1. Acessar configurações | Botão visível | Botão não aparece |

---

**Testado por:** _____________________  
**Data do Teste:** _____________________  
**Status:** ☐ Aprovado  ☐ Com ressalvas  ☐ Reprovado

