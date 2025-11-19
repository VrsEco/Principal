# 🚀 COMO USAR O PADRÃO PFPN

**Padrão:** PFPN (Padrão de Formulário com Pilares de Negócio)  
**Status:** ✅ Salvo e Documentado  
**Tempo de Aplicação:** ~10 minutos

---

## 📚 **DOCUMENTAÇÃO DISPONÍVEL**

### **1. Guia Rápido (Recomendado para começar)**
```
docs/patterns/PFPN_QUICK_START.md
```
- ⚡ Implementação rápida
- ✅ Copy & paste direto
- ✅ 3 passos simples

### **2. Documentação Completa**
```
docs/patterns/PFPN_PADRAO_FORMULARIO.md
```
- 📖 Explicação detalhada
- 📦 Todos os componentes
- 🎨 Variações possíveis
- 📋 Checklist completo

### **3. Exemplo Real**
```
templates/implantacao/alinhamento_canvas_expectativas.html
```
- 💡 Implementação de referência
- ✅ Código funcionando
- 🎯 Boas práticas aplicadas

---

## ⚡ **APLICAÇÃO RÁPIDA (3 PASSOS)**

### **Passo 1: Copiar CSS**

Abra `docs/patterns/PFPN_QUICK_START.md` e copie o CSS para seu template.

### **Passo 2: Copiar HTML**

Copie o HTML e substitua pelos seus campos.

### **Passo 3: Copiar JavaScript**

Copie o JavaScript e personalize:
- Array `camposFormulario`
- Endpoint da API
- Título do formulário

---

## 🎯 **CARACTERÍSTICAS DO PFPN**

### **Modo Visualização (Padrão):**
- ✅ Campos com fundo **cinza** (#f1f5f9)
- ✅ Campos **readonly** (não editáveis)
- ✅ Botão **"✏️ Editar"** visível
- ✅ Botão **"🗑️ Excluir"** visível
- ✅ Botão **"Salvar"** oculto

### **Modo Edição:**
- ✅ Campos com fundo **branco**
- ✅ Campos **editáveis**
- ✅ Botão **"Cancelar"** visível
- ✅ Botão **"Salvar"** visível
- ✅ Botões "Editar" e "Excluir" ocultos

### **Funcionalidades:**
- ✅ **Editar:** Entra no modo edição
- ✅ **Cancelar:** Restaura valores originais
- ✅ **Salvar:** Salva no banco + volta ao modo visualização
- ✅ **Excluir:** Limpa dados (com confirmação)
- ✅ **Notificações:** Sucesso (verde) / Erro (vermelho)

---

## 🔍 **QUANDO USAR O PFPN**

Use o padrão PFPN quando criar:

- ✅ Formulários de configuração
- ✅ Painéis de informação editáveis
- ✅ Páginas de dados estruturados
- ✅ Formulários de perfil/ajustes
- ✅ Qualquer form que precise de modo visualização/edição

**Não use quando:**
- ❌ Formulário é sempre editável (sem visualização)
- ❌ Form muito simples (1-2 campos)
- ❌ Modal de criação (sem dados existentes)

---

## 📋 **CHECKLIST DE APLICAÇÃO**

Ao aplicar o PFPN em um novo formulário:

- [ ] Abrir `docs/patterns/PFPN_QUICK_START.md`
- [ ] Copiar CSS para o template
- [ ] Copiar HTML e ajustar campos
- [ ] Copiar JavaScript
- [ ] Atualizar array `camposFormulario` com IDs dos seus campos
- [ ] Atualizar endpoint da API
- [ ] Testar modo visualização (campos cinza)
- [ ] Testar modo edição (campos brancos)
- [ ] Testar salvamento com notificação
- [ ] Testar cancelamento (restaura valores)
- [ ] Testar exclusão com confirmação

---

## 💡 **EXEMPLO DE USO**

### **Cenário:** Criar formulário de "Dados da Empresa"

1. **Abrir:** `docs/patterns/PFPN_QUICK_START.md`

2. **Definir campos:**
   ```javascript
   const camposFormulario = ['nome_empresa', 'cnpj', 'descricao'];
   ```

3. **Criar HTML:**
   ```html
   <textarea id="nome_empresa" class="readonly-field" readonly>{{ empresa.nome }}</textarea>
   <input type="text" id="cnpj" class="readonly-field" readonly value="{{ empresa.cnpj }}">
   <textarea id="descricao" class="readonly-field" readonly>{{ empresa.descricao }}</textarea>
   ```

4. **Atualizar endpoint:**
   ```javascript
   fetch('/api/empresa/' + empresaId, { ... })
   ```

5. **Pronto!** Formulário com modo visualização/edição em ~10 minutos!

---

## 🎨 **IMPLEMENTADO EM**

O padrão PFPN foi implementado primeiro em:

- **Página:** Canvas de Expectativas dos Sócios
- **URL:** `/pev/implantacao/alinhamento/canvas-expectativas`
- **Campos:** Visão Compartilhada, Metas Financeiras, Critérios de Decisão
- **Resultado:** ⭐⭐⭐⭐⭐ Interface profissional

---

## 📞 **PRECISA DE AJUDA?**

### **Comando rápido:**
```bash
# Abre o guia rápido
APLICAR_PFPN.bat
```

### **Ou navegue para:**
1. `docs/patterns/PFPN_QUICK_START.md` - Se quer aplicar rápido
2. `docs/patterns/PFPN_PADRAO_FORMULARIO.md` - Se quer entender tudo
3. `templates/implantacao/alinhamento_canvas_expectativas.html` - Se quer ver exemplo

---

## 🎉 **RESULTADO**

**Padrão PFPN salvo e documentado!**

Agora você pode aplicar rapidamente em qualquer formulário do sistema, garantindo:
- ✅ UX consistente
- ✅ Código padronizado
- ✅ Implementação rápida (~10 min)
- ✅ Qualidade profissional

---

**Para aplicar: Execute `APLICAR_PFPN.bat` ou abra `docs/patterns/PFPN_QUICK_START.md`** 🚀

