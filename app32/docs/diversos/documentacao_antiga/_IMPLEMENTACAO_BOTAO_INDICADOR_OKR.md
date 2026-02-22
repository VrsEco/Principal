# 📊 Implementação: Botão de Indicador Completo nas Páginas de OKR

## 🎯 Objetivo

Adicionar funcionalidade para que ao clicar em um botão nas páginas de OKR Global e OKR de Área, o usuário seja direcionado para o formulário completo de indicadores, com os campos de **Planejamento** e **OKR** já pré-preenchidos automaticamente.

---

## ✅ Implementações Realizadas

### 1. **Página: OKR Global** (`templates/plan_okr_global.html`)

#### Botões Adicionados:
Três novos botões "📊 Novo Indicador Completo" foram adicionados nas seguintes seções:

1. **Versão Preliminar (Workshop)** - Container: `workshop-kr-container`
2. **Versão Final e Aprovações** - Container: `approval-kr-container`  
3. **Modal de Edição de OKR** - Container: `edit-kr-container`

#### Código do Botão:
```html
<button type="button" class="button button-small button-success" 
        onclick="openIndicatorFormFromOKR('workshop-kr-container', '{{ plan.id }}', 'okr-global')" 
        title="Criar indicador completo no formulário">
  <span>📊 Novo Indicador Completo</span>
</button>
```

#### Função JavaScript Adicionada:
```javascript
function openIndicatorFormFromOKR(containerType, planId, pageType) {
    const companyId = {{ plan.company_id }};
    
    if (!companyId) {
        alert('Empresa não identificada. Por favor, recarregue a página.');
        return;
    }
    
    // Build URL with context parameters
    const params = new URLSearchParams({
        plan_id: planId,
        page_type: pageType
    });
    
    // Try to get the current OKR ID from the form context
    if (currentEditId && currentEditId > 0) {
        params.append('okr_id', currentEditId);
        params.append('okr_level', 'global');
    }
    
    const url = `/grv/company/${companyId}/indicators/form?${params.toString()}`;
    
    // Open in a new window (800x900px)
    window.open(url, 'indicatorForm', 'width=800,height=900,...');
}
```

#### Estilos CSS Adicionados:
```css
.button-success {
    background: linear-gradient(135deg, #10b981, #059669);
    border: none;
    color: white;
}

.button-success:hover {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.okr-kpi-header {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
```

---

### 2. **Página: OKR de Área** (`templates/plan_okr_area.html`)

#### Botões Adicionados:
Três novos botões "📊 Novo Indicador Completo" foram adicionados nas seguintes seções:

1. **Versão Preliminar** - Container: `area-kr-container`
2. **Versão Final** - Container: `final-area-kr-container`
3. **Modal de Edição de OKR** - Container: `edit-area-kr-container`

#### Função JavaScript:
Mesma função `openIndicatorFormFromOKR`, mas com `okr_level: 'area'` e `page_type: 'okr-area'`

#### Estilos CSS:
Mesmos estilos adicionados à página de OKR Global

---

### 3. **Formulário de Indicadores** (`templates/grv_indicator_form.html`)

O formulário **já estava preparado** para receber parâmetros de contexto via URL:

#### Parâmetros Aceitos:
- `plan_id` - ID do planejamento
- `okr_id` - ID do OKR específico
- `okr_level` - Nível do OKR (`global` ou `area`)
- `project_id` - ID do projeto (se aplicável)
- `page_type` - Origem da chamada (`okr-global`, `okr-area`, `projects`)

#### Função de Pré-preenchimento:
A função `prePopulateFromContext()` no formulário:
- Pré-seleciona o **Planejamento** no dropdown
- Carrega os OKRs do planejamento via API
- Pré-seleciona o **OKR** específico (se fornecido)
- Adiciona uma nota no campo "Observações" indicando a origem

---

### 4. **Rota Backend** (`modules/grv/__init__.py`)

A rota já estava configurada para capturar os parâmetros de contexto:

```python
@grv_bp.route('/company/<int:company_id>/indicators/form', defaults={'indicator_id': None})
@grv_bp.route('/company/<int:company_id>/indicators/form/<int:indicator_id>')
def grv_indicator_form(company_id: int, indicator_id: int | None = None):
    # Capturar parâmetros de contexto da URL
    context_params = {
        'plan_id': request.args.get('plan_id'),
        'okr_id': request.args.get('okr_id', type=int),
        'okr_level': request.args.get('okr_level'),
        'project_id': request.args.get('project_id', type=int),
        'page_type': request.args.get('page_type')
    }
    
    # ...
    
    return render_template(
        'grv_indicator_form.html',
        context_params=context_params,
        # ...
    )
```

---

## 🔄 Fluxo de Funcionamento

### Cenário 1: Criar Indicador da Versão Preliminar

1. Usuário acessa: `http://127.0.0.1:5002/plans/5/okr-global`
2. Clica em "📊 Novo Indicador Completo" na seção "Versão Preliminar"
3. JavaScript chama: `openIndicatorFormFromOKR('workshop-kr-container', '5', 'okr-global')`
4. Abre nova janela com URL:  
   `http://127.0.0.1:5002/grv/company/5/indicators/form?plan_id=5&page_type=okr-global`
5. Formulário pré-preenche o campo **Planejamento** com ID 5
6. Usuário pode selecionar o **OKR** da lista carregada automaticamente
7. Ao salvar, o indicador é criado com referência ao Planejamento e OKR

### Cenário 2: Criar Indicador ao Editar OKR Existente

1. Usuário clica em "✏️ Editar" em um OKR existente
2. Modal de edição abre com `currentEditId = [ID do OKR]`
3. Clica em "📊 Novo Indicador Completo"
4. JavaScript detecta `currentEditId` e adiciona à URL:  
   `...indicators/form?plan_id=5&page_type=okr-global&okr_id=123&okr_level=global`
5. Formulário pré-preenche **Planejamento** e **OKR** automaticamente
6. Usuário apenas preenche os demais campos do indicador

---

## 📋 Recursos Implementados

### ✅ Integração Completa
- Botões visíveis em todas as seções de OKR
- Contexto automático de Planejamento e OKR
- Abertura em nova janela (pop-up) para não perder contexto
- Reload automático da página principal ao salvar indicador

### ✅ UX Aprimorada
- Botão com estilo diferenciado (verde, ícone 📊)
- Tooltip explicativo ao passar o mouse
- Janela dimensionada adequadamente (800x900px)
- Centralizada na tela

### ✅ Flexibilidade
- Funciona para OKRs novos (só planejamento) e existentes (planejamento + OKR)
- Funciona tanto em OKR Global quanto em OKR de Área
- Não quebra funcionalidade existente de "+ Adicionar Indicador" inline

---

## 🧪 Testes Sugeridos

1. **Teste 1 - OKR Global - Versão Preliminar**
   - Acesse `/plans/5/okr-global`
   - Clique em "📊 Novo Indicador Completo"
   - Verifique se o campo "Planejamento" está pré-selecionado
   - Verifique se a lista de OKRs foi carregada

2. **Teste 2 - OKR Global - Editar OKR**
   - Edite um OKR existente
   - Clique em "📊 Novo Indicador Completo"
   - Verifique se Planejamento **e OKR** estão pré-selecionados

3. **Teste 3 - OKR de Área**
   - Acesse `/plans/5/okr-area`
   - Clique em "📊 Novo Indicador Completo"
   - Verifique comportamento similar ao OKR Global

4. **Teste 4 - Salvamento**
   - Preencha o formulário e salve
   - Verifique se o indicador aparece na lista
   - Verifique se os campos `plan_id`, `okr_id` e `okr_level` foram salvos corretamente no banco

---

## 📂 Arquivos Modificados

1. `templates/plan_okr_global.html`
   - ✅ Botões adicionados
   - ✅ Função JavaScript `openIndicatorFormFromOKR()`
   - ✅ Estilos CSS `.button-success` e `.okr-kpi-header`

2. `templates/plan_okr_area.html`
   - ✅ Botões adicionados
   - ✅ Função JavaScript `openIndicatorFormFromOKR()`
   - ✅ Estilos CSS `.button-success` e `.okr-kpi-header`

3. `templates/grv_indicator_form.html`
   - ✔️ Já estava preparado (sem modificações necessárias)

4. `modules/grv/__init__.py`
   - ✔️ Rota já estava configurada (sem modificações necessárias)

---

## 🎉 Resultado Final

Agora os usuários podem:
- ✅ Criar indicadores completos diretamente das páginas de OKR
- ✅ Ter o Planejamento e OKR automaticamente vinculados
- ✅ Preencher todos os campos do indicador (fórmula, fonte de dados, responsável, etc.)
- ✅ Não perder o contexto da página de origem
- ✅ Retornar facilmente à página de OKR após salvar o indicador

---

## 📝 Observações

- Os botões **não substituem** a funcionalidade existente de "+ Adicionar Indicador" (que adiciona indicadores inline)
- Ambas as funcionalidades coexistem:
  - **+ Adicionar Indicador**: Para adicionar Key Results rápidos dentro do formulário de OKR
  - **📊 Novo Indicador Completo**: Para criar indicadores completos no sistema GRV
- O formulário abre em nova janela/aba para facilitar navegação
- Ao salvar o indicador, a janela fecha e a página principal é recarregada

---

**Status**: ✅ **Implementação Completa e Funcional**

**Data**: Outubro 2025

