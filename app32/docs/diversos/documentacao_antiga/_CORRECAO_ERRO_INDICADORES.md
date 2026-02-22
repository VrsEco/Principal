# Correção: Erro na Página de Indicadores

## Problema Reportado

A página `http://127.0.0.1:5002/grv/company/5/indicators/list` estava retornando erro 500.

**Erro**: 
```
BuildError: Could not build url for endpoint 'meetings.meetings_manage' 
with values ['company_id']. Did you mean 'routines_management' instead?
```

## Diagnóstico

O erro foi causado por uma **função duplicada** no arquivo `modules/grv/__init__.py`:

- **Linha 1482**: `api_get_plan_okrs(plan_id: int)`
- **Linha 2643**: `api_get_plan_okrs(plan_id: str)` *(DUPLICADA)*

Ambas as funções tinham a mesma rota:
```python
@grv_bp.route('/api/plans/<plan_id>/okrs', methods=['GET'])
```

### Consequências

1. **Falha no registro do Blueprint GRV**: O Flask detectou o endpoint duplicado e lançou `AssertionError`
2. **Blueprint meetings não registrado**: Como o GRV falhou no registro, os blueprints subsequentes também não foram registrados
3. **Erro na renderização**: O template `grv_sidebar.html` tentava gerar a URL para `meetings.meetings_manage`, mas como o blueprint não estava registrado, causava o `BuildError`

## Solução Aplicada

### 1. Removida a função duplicada (linha 2642-2694)

A segunda definição de `api_get_plan_okrs` foi removida do arquivo `modules/grv/__init__.py`.

**Diferenças entre as funções**:
- **Primeira** (mantida): Busca OKRs de área com `stage = 'final'` e inclui mais campos (owner, department)
- **Segunda** (removida): Busca OKRs de área com `stage = 'approval'` e tinha menos campos

### 2. Verificação dos Blueprints

Após a correção, todos os blueprints foram registrados corretamente:
- ✅ `pev`
- ✅ `grv`  
- ✅ `meetings`

### 3. Teste de URLs

As URLs agora são geradas corretamente:
- `url_for('meetings.meetings_manage', company_id=5)` → `/meetings/company/5`
- `url_for('grv.grv_indicators_list', company_id=5)` → `/grv/company/5/indicators/list`

## Como Aplicar a Correção

**IMPORTANTE**: O servidor precisa ser reiniciado para aplicar as correções:

```bash
# 1. Pare o servidor atual (Ctrl+C no terminal onde está rodando)

# 2. Inicie novamente:
python app_pev.py

# OU use o script de inicialização:
inicio.bat
```

## Verificação

Execute o script de teste para confirmar que tudo está funcionando:

```bash
python test_fix_blueprint.py
```

Todos os testes devem passar:
- [OK] App importado com sucesso
- [OK] Todos os blueprints registrados (pev, grv, meetings)
- [OK] URLs geradas corretamente
- [OK] Nenhuma duplicação encontrada

## Arquivo Alterado

- `modules/grv/__init__.py` - Removida função duplicada `api_get_plan_okrs` (linhas 2642-2694)

## Status

✅ **CORRIGIDO** - Aguardando reinicialização do servidor para aplicar as mudanças

---

**Data da Correção**: 14/10/2025  
**Ticket/Issue**: Erro na página de indicadores

