# 🚀 Guia Rápido de Uso - Sistema de Gestão de Empresas

## 📍 Acesso Rápido

**URL Principal:** `http://127.0.0.1:5002/companies/<id>`

**Exemplo:** `http://127.0.0.1:5002/companies/6`

---

## 🎯 5 Abas Disponíveis

### 1️⃣ **📋 Dados Básicos**
**O que cadastrar:**
- Código do Cliente (1-3 caracteres)
- Nome Fantasia
- Razão Social
- Setor/Indústria
- Porte (MEI, **Micro**, Pequena, Média, Grande)
- Descrição

**Como salvar:** Clique em "💾 Salvar Alterações"

---

### 2️⃣ **🎯 Missão/Visão/Valores**
**O que cadastrar:**
- Missão da organização
- Visão de futuro
- Valores e princípios

**Como salvar:** Clique em "💾 Salvar MVV"

**✅ Corrigido:** Agora salva e recupera corretamente!

---

### 3️⃣ **👔 Funções/Cargos**
**O que cadastrar:**
- Nome da Função (Ex: "Gerente Comercial")
- **Subordinado a** ← Novo! Para hierarquia
- Departamento
- Observações

**Como usar:**
1. Clique "➕ Nova Função"
2. Preencha o formulário
3. Selecione função superior (opcional)
4. Salve

**Recursos:**
- ✅ Hierarquia visual
- ✅ Subordinação configurável
- ✅ Organização automática

---

### 4️⃣ **👥 Colaboradores**
**O que cadastrar:**
- Nome Completo
- E-mail, Telefone
- **Função/Cargo** (vincula à hierarquia)
- Departamento
- Data de Admissão
- Status (Ativo/Inativo)
- Observações

**Como usar:**
1. Clique "➕ Novo Colaborador"
2. Preencha os dados
3. Selecione a função no dropdown
4. Salve

**Recursos:**
- ✅ Vinculação automática com funções
- ✅ Status visual (verde/vermelho)
- ✅ Listagem organizada

---

### 5️⃣ **💰 Cadastro Econômico** ← NOVO!
**O que cadastrar:**

**Identificação:**
- CNPJ
- Cidade
- Estado (UF)
- CNAEs

**Cobertura:**
- Cobertura Física (Micro → Internacional)
- Cobertura Online (Sem presença → Internacional)

**Experiência:**
- Experiência Total (Ex: "15 anos")
- Experiência no Segmento (Ex: "10 anos")

**Headcount:**
- Headcount Estratégico
- Headcount Tático
- Headcount Operacional

**Financeiro:**
- Receita Total (Ex: "R$ 5.000.000")
- Margem Total (%) (Ex: "20%")

**Como salvar:** Clique em "💾 Salvar Dados Econômicos"

---

## 🔗 Atalhos de Navegação

### **Abrir aba específica via URL:**
- Dados Básicos: `/companies/6?tab=basic`
- MVV: `/companies/6?tab=mvv`
- Funções: `/companies/6?tab=roles`
- Colaboradores: `/companies/6?tab=employees`
- **Econômico:** `/companies/6?tab=economic` ← **NOVO!**

### **Acessar pelo GRV:**
- MVV: `/grv/company/5/identity/mvv` → Redireciona para cadastro centralizado
- Funções: `/grv/company/5/identity/roles` → Redireciona para cadastro centralizado

---

## 💡 Dicas de Uso

### **Fluxo Recomendado:**
1. **Primeiro:** Preencher Dados Básicos
2. **Segundo:** Cadastrar MVV
3. **Terceiro:** Cadastrar Funções (do topo da hierarquia para baixo)
4. **Quarto:** Cadastrar Colaboradores (vinculando às funções)
5. **Quinto:** Completar Cadastro Econômico

### **Hierarquia de Funções:**
- Comece pelas funções de topo (Diretor, CEO)
- Depois crie funções subordinadas (Gerentes)
- Por último, cargos operacionais
- Use o campo "Subordinado a" para definir a hierarquia

### **Colaboradores:**
- Cadastre as funções primeiro
- Depois vincule colaboradores às funções
- Isso facilita análises e relatórios

---

## 🎨 Interface Visual

**Labels:**
- ✅ Preto puro (#000000)
- ✅ Negrito (font-weight: 700)
- ✅ Máximo contraste para fácil leitura

**Modais:**
- Design limpo e moderno
- Fácil fechamento (× ou clicar fora)
- Formulários organizados

**Listas:**
- Tabelas responsivas
- Botões de ação visíveis
- Hierarquia visual clara

---

## 🐛 Problemas Resolvidos

✅ Funções salvam e aparecem na lista  
✅ Porte completo (MEI, Micro, Pequena, Média, Grande)  
✅ Labels em preto com máximo contraste  
✅ Abas respondem corretamente  
✅ **MVV persiste ao recarregar** ← Corrigido!  
✅ Salvamento funcionando em todas as abas  

---

## 📊 Resumo Rápido

**Página:** `/companies/<id>`

**5 Abas:**
1. 📋 Básicos
2. 🎯 MVV
3. 👔 Funções
4. 👥 Colaboradores
5. 💰 Econômico

**APIs:**
- GET/POST/PUT/DELETE employees
- GET/POST/PUT/DELETE roles
- GET/POST companies
- POST mvv
- **POST economic** ← NOVO!

**Tudo funcionando perfeitamente!** ✅

---

## 📞 Suporte

**Documentação completa em:**
- `RESUMO_FINAL_SESSAO.md` - Visão geral completa
- `ABA_CADASTRO_ECONOMICO.md` - Detalhes da aba econômica
- `IMPLEMENTACAO_COLABORADORES.md` - Sistema de colaboradores
- `HIERARQUIA_CARGOS_IMPLEMENTADA.md` - Hierarquia de funções

**Sistema pronto para uso!** 🚀
