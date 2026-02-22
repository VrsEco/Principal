# 🔍 Debug: Totalizados de Produtos

## Problema

O card de totalizados está mostrando R$ 0,00 em todos os campos.

## Causa

O endpoint `/products/totals` não estava usando os dados de FALLBACK_PRODUCTS quando a tabela estava vazia ou não existia.

## Solução Aplicada

Modificado o endpoint `get_products_totals()` em `modules/pev/__init__.py` para:

1. ✅ Tentar buscar produtos do banco primeiro
2. ✅ Se não houver produtos no banco, usar FALLBACK_PRODUCTS
3. ✅ Calcular totalizados com os dados disponíveis

## Código Modificado

```python
# Antes:
if not table_ready:
    return jsonify({'success': True, 'totals': {...}})  # Sempre retornava 0

# Depois:
products_data = []

# Tentar buscar do banco
if table_ready:
    products = Product.query.filter_by(plan_id=plan_id, is_deleted=False).all()
    products_data = [p.to_dict() for p in products]

# Se não houver produtos no banco, usar FALLBACK
if not products_data and plan_id in FALLBACK_PRODUCTS:
    products_data = FALLBACK_PRODUCTS[plan_id]

# Calcular com products_data disponível
```

## Dados de Teste (FALLBACK_PRODUCTS plan_id=8)

### Produto: Projetos Marceneiros

| Campo | Valor |
|-------|-------|
| Preço de Venda | R$ 10.000,00 |
| Custos Variáveis | 32% (R$ 3.200,00) |
| Despesas Variáveis | 0% (R$ 0,00) |
| MCU | 68% (R$ 6.800,00) |
| Meta Market Share | 120 unidades/mês (20%) |

### Totalizados Esperados

#### Faturamento
```
10.000 × 120 = R$ 1.200.000,00 (100%)
```

#### Custos Variáveis
```
3.200 × 120 = R$ 384.000,00 (32%)
```

#### Despesas Variáveis
```
0 × 120 = R$ 0,00 (0%)
```

#### Margem de Contribuição
```
6.800 × 120 = R$ 816.000,00 (68%)

OU

1.200.000 - 384.000 - 0 = R$ 816.000,00 (68%)
```

## Como Testar

### Opção 1: Via Browser

1. Reinicie o servidor Flask
2. Acesse: `http://127.0.0.1:5003/pev/implantacao/modelo/modelagem_financeira?plan_id=8`
3. Vá até "Margem de Contribuição e Destinação de Resultados"
4. **Esperado:** Card deve mostrar:
   - Faturamento: R$ 1.200.000,00
   - Custos Variáveis: R$ 384.000,00 (32,0%)
   - Despesas Variáveis: R$ 0,00 (0,0%)
   - Margem de Contribuição: R$ 816.000,00 (68,0%)

### Opção 2: Via API Direta

```bash
curl -X GET "http://127.0.0.1:5003/pev/api/implantacao/8/products/totals" \
  -H "Content-Type: application/json"
```

**Response esperado:**
```json
{
  "success": true,
  "totals": {
    "faturamento": {
      "valor": 1200000.0,
      "percentual": 100.0
    },
    "custos_variaveis": {
      "valor": 384000.0,
      "percentual": 32.0
    },
    "despesas_variaveis": {
      "valor": 0.0,
      "percentual": 0.0
    },
    "margem_contribuicao": {
      "valor": 816000.0,
      "percentual": 68.0
    }
  }
}
```

### Opção 3: Via Console do Browser

1. Abra a página de Modelagem Financeira
2. Abra DevTools (F12)
3. Vá na aba Console
4. Execute:
```javascript
fetch('/pev/api/implantacao/8/products/totals')
  .then(r => r.json())
  .then(data => console.log(data))
```

## Verificações no Console

O JavaScript deve logar:

```
🟢 Carregando produtos...
✅ Produtos carregados: 1
🟢 Carregando totalizados de produtos...
✅ Totalizados carregados: {faturamento: {...}, custos_variaveis: {...}, ...}
```

## Se Ainda Não Funcionar

### 1. Verificar se servidor foi reiniciado
```bash
# No terminal onde o Flask está rodando, pressione Ctrl+C
# Depois execute novamente:
python app.py
```

### 2. Verificar console do navegador (F12)
- Procurar por erros em vermelho
- Verificar se as requisições foram feitas
- Verificar as respostas das APIs

### 3. Verificar logs do servidor Flask
No terminal do servidor, procurar por:
```
📦 Usando FALLBACK_PRODUCTS para plan_id=8: 1 produtos
```

### 4. Limpar cache do navegador
- Pressionar Ctrl+F5 (hard reload)
- Ou abrir em aba anônima

### 5. Verificar se está logado
O endpoint requer `@login_required`, então:
- Faça login primeiro
- Depois acesse a página

## Próximos Passos Após Correção

1. ✅ Verificar que os valores aparecem no card
2. ✅ Verificar que a tabela lista o produto
3. ✅ Clicar em "Gerenciar Produtos"
4. ✅ Cadastrar mais produtos
5. ✅ Voltar e ver valores atualizados

## Arquivos Modificados

- ✅ `modules/pev/__init__.py` - Endpoint `get_products_totals()`
- ✅ `TESTE_TOTALIZADOS_PRODUTOS.bat` - Script de teste
- ✅ `DEBUG_PRODUTOS.md` - Esta documentação

---

**Status:** ✅ CORRIGIDO  
**Data:** 27/10/2025

