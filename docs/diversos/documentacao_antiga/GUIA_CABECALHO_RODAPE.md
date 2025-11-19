# 📝 Guia: Cabeçalho e Rodapé Personalizados

## 🎯 O que é?

Os campos **"Conteúdo (markdown leve)"** nos cabeçalhos e rodapés permitem criar textos personalizados que aparecerão em todos os relatórios gerados com esse modelo.

## ✨ Funcionalidades

### 📋 **Markdown Leve Suportado:**
- `**texto**` ou `__texto__` → **texto em negrito**
- `*texto*` ou `_texto_` → *texto em itálico*
- `## Título` → Título grande
- `### Subtítulo` → Subtítulo menor
- `[texto](url)` → Link clicável

### 🔧 **Variáveis Disponíveis:**
- `{{ company.name }}` → Nome da empresa
- `{{ report.title }}` → Título do relatório
- `{{ date }}` → Data atual (DD/MM/AAAA)
- `{{ datetime }}` → Data e hora (DD/MM/AAAA HH:MM)
- `{{ time }}` → Hora atual (HH:MM)
- `{{ year }}` → Ano atual
- `{{ system }}` → "Sistema PEVAPP22"
- `{{ page }}` → Número da página atual
- `{{ pages }}` → Total de páginas

## 💡 **Exemplos Práticos**

### Cabeçalho Empresarial:
```
## {{ company.name }} | **{{ report.title }}**
*Documento Confidencial* | {{ date }}
```

**Resultado:**
# TechnoSolutions Ltda | **Relatório Executivo**
*Documento Confidencial* | 12/10/2025

### Cabeçalho Simples:
```
**{{ company.name }}** - {{ report.title }} | {{ date }}
```

**Resultado:**
**TechnoSolutions Ltda** - Relatório Executivo | 12/10/2025

### Rodapé Corporativo:
```
© {{ year }} **{{ system }}** | Página {{ page }} de {{ pages }}
[www.empresa.com.br](http://www.empresa.com.br)
```

**Resultado:**
© 2025 **Sistema PEVAPP22** | Página 1 de 5
[www.empresa.com.br](http://www.empresa.com.br)

### Rodapé Simples:
```
{{ company.name }} | {{ datetime }} | Página {{ page }}
```

**Resultado:**
TechnoSolutions Ltda | 12/10/2025 14:30 | Página 1

## 🎨 **Como Usar**

1. **Configure o modelo** na página `/settings/reports`
2. **Digite o conteúdo** nos campos "Conteúdo (markdown leve)"
3. **Use variáveis** com a sintaxe `{{ variavel }}`
4. **Aplique formatação** com markdown leve
5. **Teste** usando os botões "Visualizar impressão"
6. **Salve o modelo** para reutilizar

## ⚠️ **Dicas Importantes**

- **Quebras de linha** são convertidas automaticamente
- **Variáveis inválidas** são mantidas como texto
- **HTML** pode ser misturado com markdown
- **Links externos** funcionam normalmente
- **Formatação** é preservada na impressão

## 🔍 **Onde Aparece**

- ✅ **Preview** na tela
- ✅ **Impressão** do navegador  
- ✅ **Arquivos PDF** gerados
- ✅ **Relatórios exportados**

---

*Esta funcionalidade permite criar relatórios completamente personalizados com a identidade visual da sua empresa!*
