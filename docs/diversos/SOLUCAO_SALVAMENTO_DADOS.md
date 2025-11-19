# ✅ SOLUÇÃO: Onde Salvar Cada Tipo de Dado

**Data:** 20/10/2025  
**Problema:** Dados não estavam sendo salvos em `/plans/6/company`

---

## 🎯 PROBLEMA IDENTIFICADO

Os dados da empresa foram **REORGANIZADOS** em duas páginas diferentes:

### 1. Cadastro Centralizado (`/companies/<id>`)
**Para:** Dados básicos e permanentes da empresa
- ✅ Nome fantasia / Razão social
- ✅ CNPJ, Cidade, Estado
- ✅ **Cobertura Regional** (física e online) ← AQUI!
- ✅ CNAEs / Atividades
- ✅ Experiência total/segmento
- ✅ Missão, Visão, Valores
- ✅ Headcount (estratégico, tático, operacional)
- ✅ Estrutura organizacional

### 2. Dados do Plano (`/plans/<id>/company`)
**Para:** Dados financeiros específicos do plano
- ✅ Faturamento/Margem por produto
- ✅ Outras informações do plano

---

## 🔍 O Que Aconteceu com Você

Você tentou editar **Cobertura Regional** em `/plans/6/company`, mas essa página **não salva mais** esses dados!

A página **mostra** os dados (para referência) mas os inputs foram **removidos**.

Para editar Cobertura Regional, você deve:
1. Acessar `/companies/25` (Cadastro Centralizado)
2. Editar lá os dados da empresa
3. Salvar

---

## ✅ SOLUÇÃO: Como Editar Cobertura Regional

### Método 1: Pelo Botão na Página

1. Acesse `/plans/6/company`
2. Procure o aviso azul "ℹ️ Dados da Empresa - Cadastro Centralizado"
3. Clique em: **"⚙️ Acessar Cadastro Centralizado da Empresa"**
4. Você será levado para `/companies/25`
5. Edite os dados lá
6. Salve

### Método 2: Direto pela URL

Acesse diretamente:
```
http://localhost:5003/companies/25
```

Ou através do menu:
```
Menu → Empresas → Eua - Moveis Planejados → Editar
```

---

## 📊 Tabela de Onde Editar Cada Dado

| Dado | Onde Editar | URL |
|------|-------------|-----|
| **Cobertura Regional** | Cadastro Centralizado | `/companies/25` |
| **CNAEs** | Cadastro Centralizado | `/companies/25` |
| **CNPJ** | Cadastro Centralizado | `/companies/25` |
| **Missão/Visão/Valores** | Cadastro Centralizado | `/companies/25` |
| **Experiência** | Cadastro Centralizado | `/companies/25` |
| **Headcount** | Cadastro Centralizado | `/companies/25` |
| **Funções/Colaboradores** | Cadastro Centralizado | `/companies/25` |
| **Faturamento/Margem** | Dados do Plano | `/plans/6/company` |
| **Outras informações** | Dados do Plano | `/plans/6/company` |

---

## 🎨 Como a Tela Atual Funciona

### Tela `/plans/6/company`:

```
┌─────────────────────────────────────────────────────┐
│  📊 Dados da Empresa                                │
│                                                     │
│  ℹ️ AVISO: Dados movidos para Cadastro Centralizado│
│     ⚙️ [Botão] Acessar Cadastro Centralizado       │
│                                                     │
│  ────────────────────────────────────────────────  │
│                                                     │
│  📈 Faturamento / Margem por produto (EDITAR AQUI) │
│     Linha   | Faturamento | Margem                 │
│     [input] | [input]     | [input]                │
│                                                     │
│  📝 Outras informações (EDITAR AQUI)                │
│     [textarea]                                      │
│                                                     │
│  [💾 Salvar]  [🗑️ Descartar]                        │
│                                                     │
│  ────────────────────────────────────────────────  │
│                                                     │
│  📋 Resumo (APENAS VISUALIZAÇÃO)                    │
│     Cobertura: Nacional                             │
│     Online: Nacional                                │
│     CNPJ: xxx.xxx.xxx/xxxx-xx                       │
└─────────────────────────────────────────────────────┘
```

### Tela `/companies/25`:

```
┌─────────────────────────────────────────────────────┐
│  🏢 Cadastro da Empresa                             │
│                                                     │
│  📝 Dados Básicos                                   │
│     Nome fantasia: [input]                          │
│     Razão social: [input]                           │
│                                                     │
│  📍 Dados Econômicos                                │
│     CNPJ: [input]                                   │
│     Cidade: [input]                                 │
│     Estado: [input]                                 │
│                                                     │
│  🌎 Cobertura Regional (EDITAR AQUI!)               │
│     Física: [select] ← AQUI!                        │
│     Online: [select] ← AQUI!                        │
│                                                     │
│  🎯 MVV                                              │
│     Missão: [textarea]                              │
│     Visão: [textarea]                               │
│     Valores: [textarea]                             │
│                                                     │
│  [💾 Salvar]                                         │
└─────────────────────────────────────────────────────┘
```

---

## ✅ TESTE: Confirme Que Funciona

### Passo a Passo:

1. **Acesse o Cadastro Centralizado**
   ```
   http://localhost:5003/companies/25
   ```

2. **Edite a Cobertura Regional**
   - Cobertura Física: Selecione "Nacional" (ou outra)
   - Cobertura Online: Selecione "Internet Nacional" (ou outra)

3. **Salve**
   - Clique em "Salvar"
   - Aguarde redirect

4. **Verifique**
   - Volte para `/plans/6/company`
   - Os dados devem aparecer no resumo

---

## 🔍 Por Que Essa Mudança?

### Antes (Problema):
- Cada plano tinha seus próprios dados da empresa
- Mesma empresa em múltiplos planos = dados duplicados
- Atualizar CNPJ em um plano não atualizava em outros
- Inconsistência e confusão

### Depois (Solução):
- **Um** cadastro centralizado por empresa
- Dados compartilhados entre todos os planos
- Atualizar uma vez = atualiza em todos os lugares
- Consistência e organização

---

## 📊 Dados Verificados no Banco

```sql
-- Empresa 25 (Eua - Moveis Planejados)
SELECT id, name, coverage_physical, coverage_online 
FROM companies 
WHERE id = 25;

 id |          name           | coverage_physical | coverage_online 
----+-------------------------+-------------------+-----------------
 25 | Eua - Moveis Planejados |                   |                 
```

**Status:** Campos vazios (por isso você não vê os dados)

**Solução:** Editar em `/companies/25`

---

## 🎓 Resumo

### ❌ NÃO FUNCIONA:
```
/plans/6/company → Editar Cobertura → Salvar → ❌ Não salva
```

### ✅ FUNCIONA:
```
/companies/25 → Editar Cobertura → Salvar → ✅ Salva!
```

---

## 🆘 Se Ainda Não Funcionar

Se você for em `/companies/25` e ainda não conseguir salvar:

1. **Verifique se há mensagem de erro**
   - Erro vermelho na tela
   - Console do navegador (F12)

2. **Verifique logs**
   ```bash
   docker logs -f gestaoversus_app_dev
   ```

3. **Me avise com:**
   - Screenshot da tela
   - Mensagem de erro
   - O que tentou fazer

---

## ✅ Checklist Final

Para editar dados da empresa:

- [ ] Identifique qual dado quer editar
- [ ] Consulte tabela "Onde Editar Cada Dado"
- [ ] Acesse a URL correta
- [ ] Edite os dados
- [ ] Salve
- [ ] Verifique se aparece no resumo

**Dados básicos da empresa = `/companies/<id>`**  
**Dados financeiros do plano = `/plans/<id>/company`**

---

**Problema:** Editando na página errada  
**Solução:** Usar Cadastro Centralizado  
**Status:** ✅ Identificado e documentado

