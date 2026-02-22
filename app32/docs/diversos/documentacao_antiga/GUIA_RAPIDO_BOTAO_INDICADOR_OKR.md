# 📖 Guia Rápido - Criar Indicadores a partir de OKRs

## ⚠️ IMPORTANTE: OKR Precisa Estar Salvo

Antes de criar indicadores, **o OKR precisa estar salvo no sistema**.

- ✅ Se você está **editando um OKR existente**, pode criar indicadores diretamente
- ⚠️ Se você está **criando um novo OKR**, o sistema irá pedir para salvá-lo primeiro

Não se preocupe! O processo é automático e intuitivo. Continue lendo para entender como funciona.

---

## 🎯 Como Usar

### 1. **Acessar Página de OKR Global**

Navegue até: `http://127.0.0.1:5002/plans/5/okr-global`

*(Substitua `5` pelo ID do seu planejamento)*

---

### 2. **Localizar o Botão**

Você encontrará o botão **"📊 Novo Indicador Completo"** em três lugares:

#### **Opção A: Na Seção "Versão Preliminar"**
- Abra a seção **"Versão Preliminar"** (Workshop)
- Role até a área de **"Indicadores"**
- Você verá dois botões:
  - `+ Adicionar Indicador` (botão azul - adiciona inline)
  - `📊 Novo Indicador Completo` (botão verde - abre formulário completo)

#### **Opção B: Na Seção "Versão Final e Aprovações"**
- Abra a seção **"Versão Final e Aprovações"**
- Role até a área de **"Indicadores"**
- Mesmos dois botões disponíveis

#### **Opção C: Ao Editar um OKR Existente**
- Clique em **✏️ Editar** em qualquer OKR da lista
- No modal de edição, role até a área de **"Indicadores"**
- Mesmos dois botões disponíveis
- **Vantagem**: Neste caso, o OKR específico já será pré-selecionado no formulário!

---

### 3. **Clicar no Botão Verde**

Clique em **"📊 Novo Indicador Completo"**

#### **Cenário A: OKR Já Salvo (Editando OKR Existente)**
✅ Uma nova janela pop-up será aberta **diretamente** com o formulário completo de indicadores.

#### **Cenário B: OKR Novo (Ainda Não Salvo)**
⚠️ Um modal aparecerá:

```
┌─────────────────────────────────────────┐
│  ⚠️ Salvar OKR Primeiro                 │
├─────────────────────────────────────────┤
│  Para adicionar ou associar um          │
│  indicador, é necessário salvar o       │
│  OKR primeiro.                           │
│                                          │
│  O sistema irá validar os campos        │
│  obrigatórios, salvar o OKR e então     │
│  abrir o formulário de indicadores.     │
├─────────────────────────────────────────┤
│           [Cancelar] [💾 Salvar e       │
│                      Continuar]          │
└─────────────────────────────────────────┘
```

**Opções:**
- **Cancelar**: Fecha o modal e você continua editando o OKR
- **💾 Salvar e Continuar**: Valida, salva o OKR e abre o formulário de indicadores

---

### 4. **Validação Automática (Se OKR Não Estava Salvo)**

Ao clicar em "💾 Salvar e Continuar", o sistema verifica se todos os campos obrigatórios estão preenchidos:

**Para OKR Global:**
- ✅ Objetivo do OKR
- ✅ Tipo (Estruturante/Aceleração)
- ✅ Direcionador Base

**Para OKR de Área:**
- ✅ Objetivo do OKR
- ✅ Tipo (Estruturante/Aceleração)
- ✅ Área/Departamento
- ✅ OKR Global Base

**Se algum campo estiver faltando:**
```
⚠️ Por favor, preencha os seguintes 
campos obrigatórios antes de continuar:

• Objetivo do OKR
• Tipo
• Direcionador Base
```

O modal fecha e você pode preencher os campos faltantes antes de tentar novamente.

**Se todos os campos estiverem preenchidos:**
1. Botão muda para "⏳ Salvando..."
2. OKR é salvo no banco de dados
3. Página recarrega automaticamente
4. Mensagem: "✅ OKR salvo com sucesso! Abrindo formulário de indicadores..."
5. Formulário de indicadores abre **automaticamente** em nova janela

---

### 5. **Verificar Campos Pré-preenchidos**

No formulário, você verá que os seguintes campos já estão automaticamente preenchidos:

✅ **Planejamento** → Já selecionado com o planejamento atual  
✅ **OKR Associado** → Dropdown carregado com os OKRs do planejamento  
✅ **OKR Específico** → Já pré-selecionado com o OKR que você estava criando/editando! ⭐

---

### 6. **Preencher os Demais Campos**

Complete o formulário com as informações do indicador:

#### **Campos Obrigatórios:**
- **Nome** ✱ - Nome do indicador

#### **Campos Opcionais:**
- **Grupo de Indicadores** - Vincular a um grupo existente
- **Unidade de Medida** - Ex: %, R$, unidades, etc.
- **Polaridade** - Quanto maior melhor / Quanto menor melhor
- **Processo associado** - Vincular a um processo da empresa
- **Projeto associado** - Vincular a um projeto
- **Planejamento** - Já preenchido ✅
- **OKR Associado** - Já carregado ✅
- **Fórmula do Indicador** - Como é calculado
- **Fonte de Dados** - De onde vêm os dados
- **Responsável** - Quem é responsável pelo indicador
- **Observações** - Notas adicionais

---

### 7. **Salvar o Indicador**

Clique em **"Salvar Indicador"**

✅ O indicador será criado no sistema  
✅ A janela pop-up fechará automaticamente  
✅ A página principal será recarregada  
✅ O novo indicador aparecerá na lista de indicadores

---

## 📊 Exemplos de Uso Completo

### **Exemplo 1: OKR Já Existente (Mais Simples)**

**Cenário**: Criar indicador "Taxa de Conversão" para o OKR existente "Aumentar vendas online"

1. **Acesse**: `/plans/5/okr-global`
2. **Encontre o OKR** "Aumentar vendas online" na lista
3. **Clique em** ✏️ **Editar** neste OKR
4. **No modal de edição**, clique em **"📊 Novo Indicador Completo"**
5. ✅ **Formulário abre DIRETAMENTE** (sem modal intermediário)
6. **No formulário que abrir**, preencha:
   - **Nome**: Taxa de Conversão
   - **Unidade de Medida**: %
   - **Polaridade**: Quanto maior melhor
   - **Planejamento**: ✅ Já está selecionado (Planejamento 2025)
   - **OKR Associado**: ✅ Já está selecionado (Aumentar vendas online)
   - **Fórmula**: (Vendas realizadas / Visitas ao site) * 100
   - **Fonte de Dados**: Google Analytics
   - **Responsável**: João Silva
7. **Clique em** "Salvar Indicador"
8. **Pronto!** O indicador foi criado e vinculado ao OKR "Aumentar vendas online"

---

### **Exemplo 2: OKR Novo (Processo Completo)**

**Cenário**: Criar novo OKR "Reduzir custos operacionais" e depois criar indicador "Taxa de Redução de Custos"

1. **Acesse**: `/plans/5/okr-global`
2. **Abra** a seção "Versão Preliminar"
3. **Preencha** o formulário de novo OKR:
   - **Direcionador Base**: Eficiência Operacional
   - **Objetivo**: Reduzir custos operacionais em 15%
   - **Tipo**: Estruturante
   - **Responsável**: Maria Santos
   - **Prazo**: 31/12/2025
4. **NÃO clique** em "Salvar OKR Preliminar" ainda
5. **Clique em** **"📊 Novo Indicador Completo"** (botão verde)
6. ⚠️ **Modal aparece**: "Salvar OKR Primeiro"
7. **Clique em** "💾 Salvar e Continuar"
8. ✅ Sistema valida: Todos os campos OK!
9. **Aguarde**:
   - Botão mostra "⏳ Salvando..."
   - OKR é salvo
   - Página recarrega
10. **Mensagem**: "✅ OKR salvo com sucesso! Abrindo formulário de indicadores..."
11. ✅ **Formulário abre AUTOMATICAMENTE** com:
    - **Planejamento**: Já selecionado
    - **OKR**: "Reduzir custos operacionais em 15%" já selecionado!
12. **Preencha** os demais campos do indicador:
    - **Nome**: Taxa de Redução de Custos
    - **Unidade**: %
    - **Fórmula**: ((Custo Anterior - Custo Atual) / Custo Anterior) * 100
    - **Fonte**: ERP Financeiro
13. **Clique em** "Salvar Indicador"
14. **Pronto!** OKR e Indicador criados e vinculados automaticamente!

---

### **Exemplo 3: OKR Novo com Campos Faltando**

**Cenário**: Usuário esquece de preencher campos obrigatórios

1. **Acesse**: `/plans/5/okr-global`
2. **Abra** a seção "Versão Preliminar"
3. **Preencha** apenas:
   - **Objetivo**: Melhorar atendimento ao cliente
4. **Clique em** "📊 Novo Indicador Completo"
5. ⚠️ **Modal aparece**: "Salvar OKR Primeiro"
6. **Clique em** "💾 Salvar e Continuar"
7. ⚠️ **Alerta aparece**:
   ```
   ⚠️ Por favor, preencha os seguintes 
   campos obrigatórios antes de continuar:
   
   • Tipo
   • Direcionador Base
   ```
8. **Modal fecha**, formulário permanece aberto
9. **Preencha** os campos faltantes:
   - **Tipo**: Aceleração
   - **Direcionador Base**: Excelência no Atendimento
10. **Clique em** "📊 Novo Indicador Completo" novamente
11. ✅ Agora funciona! Sistema salva e abre formulário automaticamente

---

## 🔄 Diferenças entre os Dois Botões

### **+ Adicionar Indicador** (Azul)
- ✅ Adiciona Key Result diretamente no formulário de OKR
- ✅ Rápido e prático para indicadores simples
- ✅ Fica dentro do próprio formulário
- ❌ Campos limitados (nome, meta, prazo, responsável)

### **📊 Novo Indicador Completo** (Verde) ⭐
- ✅ Abre formulário completo em nova janela
- ✅ Todos os campos disponíveis (fórmula, fonte, processo, etc.)
- ✅ Cria indicador no sistema GRV completo
- ✅ Planejamento e OKR já pré-preenchidos
- ✅ Pode ser vinculado a processos, projetos, etc.

---

## 💡 Dicas

### **Dica 1: Use o Botão Verde para Indicadores Importantes**
Se você precisa documentar bem o indicador (fórmula, fonte de dados, responsável), use o botão verde.

### **Dica 2: Editando OKR = OKR Pré-selecionado**
Ao clicar em "Editar OKR" e depois em "📊 Novo Indicador Completo", o OKR específico já virá selecionado automaticamente!

### **Dica 3: Funciona Também em OKRs de Área**
A mesma funcionalidade está disponível em:
- `/plans/5/okr-area`

---

## ❓ Perguntas Frequentes

### **P: Posso criar indicadores sem OKR?**
R: Sim! O campo "OKR Associado" é opcional. Você pode criar indicadores independentes.

### **P: O indicador fica vinculado ao OKR automaticamente?**
R: Sim, se você clicar no botão ao editar um OKR específico, o indicador já virá com o OKR pré-selecionado.

### **P: Posso mudar o OKR depois de criar o indicador?**
R: Sim! Você pode editar o indicador posteriormente e alterar o OKR associado.

### **P: A janela pop-up não abre. O que fazer?**
R: Verifique se o navegador não está bloqueando pop-ups. Autorize pop-ups para este site.

### **P: Os indicadores aparecem onde?**
R: Os indicadores criados aparecem em:
- Lista de Indicadores GRV: `/grv/company/5/indicators/list`
- Gestão de Metas: `/grv/company/5/indicators/goals`
- Análise de Indicadores: `/grv/company/5/indicators/analysis`

---

## 🎉 Pronto!

Agora você sabe como criar indicadores completos diretamente das páginas de OKR, com Planejamento e OKR já pré-preenchidos automaticamente!

---

**Precisa de ajuda?** Consulte a documentação completa em `_IMPLEMENTACAO_BOTAO_INDICADOR_OKR.md`

