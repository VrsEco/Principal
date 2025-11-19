# 🎨 Sistema de Logos das Empresas

**Implementado:** 10/10/2025  
**Status:** ✅ Completo e Funcionando

---

## 📋 O QUE FOI IMPLEMENTADO

### 1. **Banco de Dados**
✅ Adicionadas 4 colunas na tabela `companies`:
- `logo_square` - Logo quadrada (400x400px)
- `logo_vertical` - Logo vertical (300x600px)
- `logo_horizontal` - Logo horizontal (800x400px)
- `logo_banner` - Logo banner (1200x300px)

### 2. **Sistema de Upload**
✅ Interface completa de gerenciamento de logos
✅ Upload com validação de formato
✅ Redimensionamento automático
✅ Preview em tempo real

### 3. **Processamento de Imagens**
✅ Redimensionamento automático para tamanho ideal
✅ Otimização de qualidade
✅ Suporte a PNG, JPG, WEBP
✅ Conversão automática RGBA → RGB para JPG

### 4. **Interface de Usuário**
✅ Página dedicada para gerenciar logos
✅ 4 cards, um para cada tipo de logo
✅ Indicação de tamanho ideal antes do upload
✅ Preview da logo ou placeholder
✅ Botões de upload e remoção

---

## 🚀 COMO USAR

### Acessar Gerenciador de Logos:

```
http://127.0.0.1:5002/companies/{company_id}/logos

Exemplos:
http://127.0.0.1:5002/companies/1/logos
http://127.0.0.1:5002/companies/4/logos
```

### Fazer Upload:

1. Acesse a página de logos da empresa
2. Escolha o tipo de logo (quadrada, vertical, horizontal, banner)
3. Clique em "Fazer Upload"
4. Selecione a imagem
5. **Sistema redimensiona automaticamente**
6. Logo salva e pronta para usar

---

## 📐 TAMANHOS RECOMENDADOS

### Logo Quadrada (1:1)
- **Tamanho ideal:** 400 x 400 pixels
- **Uso:** Ícones, perfis, redes sociais
- **Formato:** PNG (com transparência) ou JPG

### Logo Retangular Vertical (1:2)
- **Tamanho ideal:** 300 x 600 pixels
- **Uso:** Documentos em formato retrato
- **Formato:** PNG (com transparência) ou JPG

### Logo Retangular Horizontal (2:1)
- **Tamanho ideal:** 800 x 400 pixels
- **Uso:** Cabeçalhos, assinaturas de e-mail
- **Formato:** PNG (com transparência) ou JPG

### Logo Banner (4:1)
- **Tamanho ideal:** 1200 x 300 pixels
- **Uso:** Topo de documentos, apresentações
- **Formato:** PNG (com transparência) ou JPG

---

## 🔧 PROCESSAMENTO AUTOMÁTICO

### O que o sistema faz:

1. **Validação:**
   - Verifica formato (PNG, JPG, WEBP)
   - Verifica tamanho do arquivo

2. **Redimensionamento:**
   - Mantém proporções da imagem original
   - Ajusta para tamanho ideal
   - Centraliza na área de destino

3. **Otimização:**
   - Compressão otimizada
   - Qualidade 90% (balanço qualidade/tamanho)
   - Conversão automática RGBA → RGB para JPG

4. **Salvamento:**
   - Arquivo salvo em `uploads/logos/`
   - Nome padronizado: `company_{id}_{tipo}.{ext}`
   - Caminho salvo no banco de dados

---

## 📄 USO NOS DOCUMENTOS

### POP (Procedimento Operacional Padrão):

Atualizar o template `grv_process_detail.html` para usar logo:

```html
{% if company.logo_horizontal %}
  <img src="/{{ company.logo_horizontal }}" alt="{{ company.name }}" style="max-width: 200px;">
{% else %}
  <div class="logo-placeholder">
    ⚠️ Incluir imagem tipo horizontal
  </div>
{% endif %}
```

### Relatórios PDF:

```python
# Usar logo banner no topo
if company.get('logo_banner'):
    logo_url = company['logo_banner']
else:
    # Placeholder ou logo padrão
    logo_url = 'static/img/logo-default.png'
```

---

## 🎨 PLACEHOLDERS

### Quando NÃO houver logo:

```html
<div class="logo-placeholder">
  <div class="logo-placeholder-icon">🖼️</div>
  <div class="logo-placeholder-text">
    Incluir imagem tipo {quadrada|vertical|horizontal|banner}
  </div>
</div>
```

Estilos:
- Fundo cinza claro (#f8fafc)
- Borda tracejada (#cbd5e1)
- Ícone semitransparente
- Texto descritivo

---

## 🔗 ROTAS CRIADAS

### Página de Gerenciamento:
```
GET /companies/<company_id>/logos
```

### API - Upload:
```
POST /api/companies/<company_id>/logos
Form Data:
  - logo: arquivo de imagem
  - logo_type: 'square' | 'vertical' | 'horizontal' | 'banner'
```

### API - Remover:
```
DELETE /api/companies/<company_id>/logos/<logo_type>
```

---

## 📁 ESTRUTURA DE ARQUIVOS

```
app26/
├── utils/
│   ├── __init__.py
│   └── logo_processor.py          # Processamento de logos
│
├── uploads/
│   └── logos/                      # Logos das empresas
│       ├── company_1_square.png
│       ├── company_1_horizontal.png
│       └── ...
│
├── templates/
│   └── company_logos_manager.html  # Interface de gerenciamento
│
└── migrations/
    └── add_company_logos.sql      # SQL de migração
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [x] Colunas adicionadas na tabela companies
- [x] Pasta `utils/` criada
- [x] Pasta `uploads/logos/` criada
- [x] `logo_processor.py` implementado
- [x] Template `company_logos_manager.html` criado
- [x] Rotas adicionadas no `app_pev.py`
- [x] Redimensionamento automático funcionando
- [x] Upload e remoção funcionando
- [x] Placeholders implementados
- [ ] Integração com POP (próximo passo)
- [ ] Integração com relatórios (próximo passo)

---

## 🚀 PRÓXIMOS PASSOS

### 1. Integrar com POP
Atualizar template do POP para mostrar logo da empresa

### 2. Integrar com Relatórios
Usar logos nos relatórios PDF

### 3. Adicionar Link no Menu
Adicionar opção "Gerenciar Logos" no dashboard da empresa

### 4. Validação de Tamanho
Avisar se imagem está muito diferente do recomendado

---

## 💡 COMO FUNCIONA

### Fluxo de Upload:

1. Usuário acessa `/companies/{id}/logos`
2. Seleciona arquivo e tipo de logo
3. JavaScript envia para `/api/companies/{id}/logos`
4. Backend valida formato e tamanho
5. **`logo_processor.py` redimensiona** automaticamente
6. Salva em `uploads/logos/`
7. Atualiza banco de dados
8. Retorna sucesso
9. Página recarrega mostrando logo

### Fluxo de Remoção:

1. Usuário clica em "Remover Logo"
2. JavaScript confirma ação
3. Envia DELETE para `/api/companies/{id}/logos/{tipo}`
4. Backend deleta arquivo físico
5. Atualiza banco (NULL)
6. Retorna sucesso
7. Página recarrega mostrando placeholder

---

## 🛡️ SEGURANÇA

### Validações:
- ✅ Formatos permitidos: PNG, JPG, JPEG, WEBP, SVG
- ✅ Tamanho máximo: 2-3 MB dependendo do tipo
- ✅ Filename sanitizado (secure_filename)
- ✅ Pasta dedicada (uploads/logos/)

### Boas Práticas:
- ✅ Não sobrescreve arquivos de outras empresas
- ✅ Nome único por empresa e tipo
- ✅ Validação de permissões
- ✅ Tratamento de erros

---

## 📝 EXEMPLO DE USO NO POP

```html
<!-- No template do POP -->
<div class="pop-header">
  {% if company.logo_horizontal %}
    <img src="/{{ company.logo_horizontal }}" 
         alt="Logo {{ company.name }}"
         style="max-width: 200px; height: auto;">
  {% else %}
    <div class="logo-warning" style="padding: 12px; background: #fef3c7; border: 2px dashed #f59e0b; border-radius: 8px; text-align: center; color: #92400e;">
      ⚠️ Incluir imagem tipo horizontal
      <br>
      <small>Acesse: Gerenciar Logos</small>
    </div>
  {% endif %}
</div>
```

---

## 🎉 RESULTADO

Agora cada empresa pode ter:
- ✅ 4 versões diferentes de logo
- ✅ Upload simples e rápido
- ✅ Redimensionamento automático
- ✅ Uso em documentos
- ✅ Placeholders quando não houver

**Sistema profissional de gestão de identidade visual!** 🎨

---

**Criado em:** 10/10/2025  
**Arquivos:**
- `utils/logo_processor.py`
- `templates/company_logos_manager.html`
- `app_pev.py` (rotas adicionadas)
- `migrations/add_company_logos.sql`




