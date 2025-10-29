# Correção do Erro: "Item não encontrado"

## 🔴 Problema

Ao clicar em "Adicionar Valores", o erro aparece:
```
Item não encontrado. Por favor, recarregue a página.
```

**Causa:** As tabelas de investimento existem, mas não têm dados (categorias e itens).

---

## ✅ Solução

### Para Windows (local):

Execute o script:
```bash
APLICAR_INVESTIMENTOS_ATUALIZACAO.bat
```

### Para Docker/Linux:

1. Torne o script executável:
```bash
chmod +x docker_aplicar_investimentos.sh
```

2. Execute:
```bash
./docker_aplicar_investimentos.sh
```

### Ou manualmente via Docker:

```bash
# 1. Criar tabelas
docker exec -i app31 python -c "
from config_database import get_db
db = get_db()
conn = db._get_connection()
cur = conn.cursor()
with open('migrations/create_investment_contributions.sql', 'r', encoding='utf-8') as f:
    cur.execute(f.read())
conn.commit()
conn.close()
"

# 2. Aplicar migration
docker exec -i app31 python -c "
from config_database import get_db
db = get_db()
conn = db._get_connection()
cur = conn.cursor()
with open('migrations/20251028_update_investment_contributions.sql', 'r', encoding='utf-8') as f:
    cur.execute(f.read())
conn.commit()
conn.close()
"

# 3. Popular dados
docker exec -i app31 python scripts/seed_investment_items.py

# 4. Reiniciar container
docker-compose restart
```

---

## 🔍 Verificação

Após executar, verifique no console do navegador (F12):
```
✅ Categories loaded: Array [ {…}, {…} ]
```

Deve aparecer 2 categorias:
- Capital de Giro (com 3 itens: Caixa, Recebíveis, Estoques)
- Imobilizado (com 3 itens: Instalações, Máquinas, Outros)

---

## 🐛 Debug Manual

Se ainda houver erro, verifique via psql:

```bash
# Entrar no container
docker exec -it app31 bash

# Conectar ao PostgreSQL
psql -U [usuario] -d [banco]

# Verificar tabelas
\dt plan_finance_investment*

# Verificar dados
SELECT * FROM plan_finance_investment_categories;
SELECT * FROM plan_finance_investment_items;
```

Deve retornar:
- **2 categorias por plan_id** (Capital de Giro + Imobilizado)
- **6 itens** (3 de cada categoria)

Se estiver vazio, execute o seed novamente.

---

## 📝 Notas

- ✅ PostgreSQL suportado
- ✅ Docker suportado
- ⚠️ Execute o seed apenas uma vez por plan (script já verifica duplicatas)
- 🔄 Se criar novos plans, execute o seed novamente

---

**Última atualização:** 28/10/2025

