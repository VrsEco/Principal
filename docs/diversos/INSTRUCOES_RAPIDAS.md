# 🚀 Instruções Rápidas - Corrigir Erro de Investimento

## ⚡ Solução em 3 Passos

### 1️⃣ Execute o Script de Correção
```bash
CORRIGIR_ERRO_INVESTIMENTO.bat
```

### 2️⃣ Reinicie o Servidor
```bash
python app_pev.py
```

### 3️⃣ Teste
Acesse: http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=8

Clique em **"+ Adicionar Aporte"** e salve um investimento.

---

## ✅ O Que Foi Corrigido

**Problema:** As tabelas de investimentos não existiam no banco de dados.

**Solução:** Adicionadas 4 tabelas no `database/postgresql_db.py`:
- `plan_finance_investment_categories`
- `plan_finance_investment_items`
- `plan_finance_investment_contributions`
- `plan_finance_funding_sources`

---

## 📝 Detalhes Completos

Veja `SOLUCAO_ERRO_INVESTIMENTO.md` para:
- Diagnóstico detalhado
- Código das correções
- Comandos de verificação SQL
- Troubleshooting

---

**Status:** ✅ Pronto para aplicar  
**Tempo Estimado:** < 2 minutos

