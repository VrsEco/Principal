# ⚡ AÇÃO RÁPIDA - Sistema de Relatórios

## 🎯 OBJETIVO

Entender o que está funcionando e o que precisa ser ajustado no sistema de relatórios.

---

## 📝 ROTEIRO DE TESTES (5 minutos)

### **TESTE 1: Modelos de Página** ✅

#### **Passo a passo:**
```
1. Abra o navegador
2. Acesse: http://127.0.0.1:5002/settings/reports
3. Configure:
   - Margens: deixe os padrões
   - Cabeçalho: digite "{{ company.name }} - Teste"
   - Rodapé: digite "Página {{ page }}"
4. Nome do modelo: "Teste Rápido"
5. Clique "Salvar modelo"
```

#### **Resultado esperado:**
- ✅ Modelo aparece na lista abaixo
- ✅ Tem botões "Aplicar" e "Editar"

#### **Se funcionou:**
```
✅ PARTE 1 DO SISTEMA ESTÁ OK!
   (Criação de modelos funciona)
```

#### **Se NÃO funcionou:**
```
❌ Anote o erro que apareceu
```

---

### **TESTE 2: Geração de Relatório de Processo** ❓

#### **Passo a passo:**
```
1. Acesse: http://127.0.0.1:5002/companies/6
2. No menu lateral, clique em algum Processo
   (ou acesse diretamente: /companies/6/processes/X)
3. Procure um botão "Gerar Relatório" ou "📄 Relatório"
4. Clique no botão
```

#### **Anote o que acontece:**

**Opção A:** Modal abre ✅
```
□ Tem checkboxes de seções (Fluxo, POP, etc)?
□ Tem dropdown para escolher modelo?
□ Ao marcar seções e clicar "Gerar", o que acontece?
```

**Opção B:** Abre nova página com relatório ✅
```
□ O relatório aparece formatado?
□ Tem cabeçalho e rodapé?
□ As seções correspondem ao que você marcou?
```

**Opção C:** Erro ❌
```
□ Qual mensagem de erro aparece?
```

**Opção D:** Nada acontece ❌
```
□ O botão existe mas não faz nada?
```

**Opção E:** Botão não existe ❌
```
□ Não tem botão de "Gerar Relatório" na página?
```

---

## 📊 INTERPRETAÇÃO DOS RESULTADOS

### **Cenário 1: Tudo Funciona** ✅✅
```
✅ TESTE 1: Modelo salva
✅ TESTE 2: Modal abre
✅ TESTE 2: Tem seletor de modelo
✅ TESTE 2: Gera relatório usando o modelo

CONCLUSÃO: Sistema completo! 🎉
AÇÃO: Nenhuma, está tudo certo.
```

---

### **Cenário 2: Modal sem Seletor de Modelo** ⚠️
```
✅ TESTE 1: Modelo salva
✅ TESTE 2: Modal abre
❌ TESTE 2: NÃO tem seletor de modelo
✅ TESTE 2: Gera relatório (mas sem usar modelo)

CONCLUSÃO: Falta conexão entre partes
AÇÃO: Adicionar seletor de modelo no modal
```

#### **Solução:**
```html
<!-- Adicionar em: templates/grv_process_detail.html -->
<!-- Dentro do modal de relatório (linha ~1680) -->

<div class="form-group">
  <label>Modelo de Página</label>
  <select id="report-model-selector" class="form-control">
    <option value="">Configuração Padrão</option>
    {% for model in report_models %}
      <option value="{{ model.id }}">{{ model.name }}</option>
    {% endfor %}
  </select>
  <small>Selecione um modelo salvo ou use a configuração padrão</small>
</div>
```

---

### **Cenário 3: Botão Não Faz Nada** ⚠️
```
✅ TESTE 1: Modelo salva
❌ TESTE 2: Botão existe mas não funciona

CONCLUSÃO: JavaScript está quebrado
AÇÃO: Verificar console do navegador
```

#### **Solução:**
```
1. Abra DevTools (F12)
2. Vá na aba "Console"
3. Clique no botão novamente
4. Anote os erros em vermelho
```

Possíveis erros:
- `Uncaught ReferenceError: X is not defined` → Variável faltando
- `404 Not Found` → Endpoint não existe
- `500 Internal Server Error` → Erro no backend

---

### **Cenário 4: Botão Não Existe** ❌
```
✅ TESTE 1: Modelo salva
❌ TESTE 2: Não tem botão de gerar relatório

CONCLUSÃO: Botão não foi criado ainda
AÇÃO: Adicionar botão na página
```

#### **Solução:**
```html
<!-- Adicionar em: templates/grv_process_detail.html -->
<!-- Na seção de ações (linha ~200-300) -->

<button type="button" 
        class="btn btn-primary" 
        data-report-modal-trigger>
  📄 Gerar Relatório
</button>
```

---

### **Cenário 5: Endpoint Não Existe** ❌
```
✅ TESTE 1: Modelo salva
✅ TESTE 2: Modal funciona
❌ TESTE 2: Ao gerar, erro 404

CONCLUSÃO: Falta criar rota no backend
AÇÃO: Adicionar endpoint em app_pev.py
```

#### **Solução:**
```python
# Adicionar em: app_pev.py

@app.route('/api/companies/<int:company_id>/processes/<int:process_id>/report')
def generate_process_report(company_id, process_id):
    """Gera relatório de processo"""
    
    # 1. Captura parâmetros
    model_id = request.args.get('model_id', type=int)
    sections = request.args.getlist('sections')
    
    # 2. Busca dados
    # TODO: Implementar busca de dados do processo
    
    # 3. Carrega modelo
    if model_id:
        from modules.report_models import ReportModelsManager
        manager = ReportModelsManager()
        model = manager.get_model(model_id)
    else:
        model = None
    
    # 4. Gera relatório
    # TODO: Implementar geração com seções selecionadas
    
    # 5. Retorna HTML
    return render_template(
        'reports/process_documentation.html',
        # ... dados ...
    )
```

---

## 🔧 FERRAMENTAS DE DIAGNÓSTICO

### **1. Ver erros do JavaScript:**
```
F12 → Console
(mostra erros em vermelho)
```

### **2. Ver requisições HTTP:**
```
F12 → Network
(mostra se endpoint foi chamado)
```

### **3. Ver erros do Python:**
```
Terminal onde o servidor está rodando
(mostra erros do Flask)
```

---

## 📝 TEMPLATE DE RESPOSTA

Para facilitar, copie e preencha:

```
===== RESULTADOS DOS TESTES =====

TESTE 1 - Modelos:
[ ] ✅ Funcionou perfeitamente
[ ] ❌ Erro: _______________________

TESTE 2 - Geração de Relatório:
Passo 1 - Botão existe?
[ ] Sim  [ ] Não

Passo 2 - Modal abre?
[ ] Sim  [ ] Não

Passo 3 - Tem seletor de modelo?
[ ] Sim  [ ] Não

Passo 4 - Ao clicar "Gerar":
[ ] Abre relatório
[ ] Erro 404
[ ] Erro 500
[ ] Nada acontece
[ ] Outro: _______________________

Passo 5 - Relatório gerado:
[ ] Usa o modelo selecionado
[ ] Usa layout padrão
[ ] Mostra só seções marcadas
[ ] Mostra todas as seções

ERROS DO CONSOLE (se houver):
_________________________________
_________________________________

OBSERVAÇÕES:
_________________________________
_________________________________
```

---

## 🚀 PRÓXIMOS PASSOS

Baseado nos seus resultados:

### **Se tudo funciona:**
```
🎉 Sistema está completo!
→ Pode usar normalmente
→ Criar mais modelos
→ Gerar relatórios
```

### **Se algo não funciona:**
```
📝 Anote os resultados
→ Cole o template preenchido
→ Vou criar a solução específica
→ Implementamos juntos
```

---

## ⏱️ TEMPO ESTIMADO

```
Teste 1: 2 minutos
Teste 2: 3 minutos
Total:   5 minutos
```

---

## 💬 EXEMPLO DE RESPOSTA

```
TESTE 1: ✅ Funcionou! Modelo salvou e apareceu na lista.

TESTE 2:
- Botão existe: SIM
- Modal abre: SIM
- Seletor de modelo: NÃO ← PROBLEMA AQUI!
- Gera relatório: SIM (mas usa layout padrão)
- Seções: Mostra todas (ignora as que desmarquei)

ERROS: Nenhum erro no console

OBSERVAÇÃO: O modal só tem checkboxes, falta o dropdown
para escolher qual modelo usar.
```

**Com essa resposta, eu sei exatamente o que implementar! 🎯**

---

## 📞 ESTÁ PRONTO?

1. ✅ Execute os 2 testes (5 minutos)
2. ✅ Anote os resultados
3. ✅ Cole aqui a resposta
4. ✅ Vamos implementar a solução

**Vamos lá! 🚀**

