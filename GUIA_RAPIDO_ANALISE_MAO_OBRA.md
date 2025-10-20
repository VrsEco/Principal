# 🚀 GUIA RÁPIDO - Análise da Mão de Obra

**⏱️ Tempo estimado**: 10 minutos  
**📋 Pré-requisito**: Colaboradores e rotinas já cadastrados

---

## 📝 PASSO A PASSO

### 1️⃣ Atualizar Carga Horária dos Colaboradores

```
1. Acesse: http://127.0.0.1:5002/companies
2. Clique em "⚙️ Gerenciar" na empresa desejada
3. Clique na aba "Colaboradores"
4. Para cada colaborador:
   a. Clique em ✏️ Editar
   b. Preencha "Carga Horária Semanal" (ex: 40, 44, 30)
   c. Clique em 💾 Salvar
```

**⏱️ 2-3 minutos**

---

### 2️⃣ Verificar Associação de Rotinas

```
1. Acesse: http://127.0.0.1:5002/companies/{id}/routines
2. Para cada rotina, clique no ícone 👥
3. Verifique se há colaboradores associados
4. Se não houver:
   a. Clique em "➕ Adicionar Colaborador"
   b. Selecione o colaborador
   c. Defina as horas utilizadas (ex: 2.5)
   d. Adicione observações (opcional)
   e. Clique em 💾 Salvar
```

**⏱️ 5-7 minutos** (dependendo do número de rotinas)

---

### 3️⃣ Visualizar Análise

```
1. Acesse: http://127.0.0.1:5002/grv/company/{id}
2. Menu lateral → "Gestão de Processos" → "Análises"
3. Verifique os cards de resumo no topo
4. Role a página para ver cada colaborador
5. Clique em "📋 Ver Rotinas" para expandir detalhes
```

**⏱️ 1 minuto**

---

## 🎯 O QUE OBSERVAR

### ✅ Indicadores Saudáveis:
- Utilização entre 60-80%
- Horas disponíveis positivas
- Barra de utilização verde ou amarela

### ⚠️ Sinais de Atenção:
- Utilização acima de 90% (vermelho)
- Horas disponíveis muito baixas
- Concentração de rotinas em poucos colaboradores

### 💡 Oportunidades:
- Utilização abaixo de 40% (ociosos)
- Colaboradores sem rotinas associadas
- Desbalanceamento entre equipes

---

## 📊 EXEMPLO PRÁTICO

### Cenário:

**Empresa**: TechStart  
**Colaboradores**: 3

| Colaborador | Carga Horária | Rotinas | Horas/Semana | Utilização |
|-------------|---------------|---------|--------------|------------|
| Ana Silva | 40h | 5 | 35h | 87.5% 🟡 |
| Carlos Souza | 40h | 2 | 15h | 37.5% 🟢 |
| Maria Santos | 30h | 4 | 28h | 93.3% 🔴 |

### Análise:
- ✅ Carlos: Ótima oportunidade para alocar mais tarefas
- ⚠️ Ana: Atenção, próxima da sobrecarga
- 🚨 Maria: **SOBRECARGA** - Redistribuir rotinas urgente

### Ações Recomendadas:
1. Transferir 2 rotinas de Maria para Carlos
2. Monitorar Ana nas próximas semanas
3. Avaliar contratação se toda equipe estiver acima de 85%

---

## 🔧 COMANDOS ÚTEIS

### Verificar Banco de Dados (SQLite):
```bash
sqlite3 instance/pevapp22.db "SELECT name, weekly_hours FROM employees WHERE company_id = 1"
```

### Testar API:
```bash
curl http://127.0.0.1:5002/api/companies/1/workforce-analysis | json_pp
```

### Verificar Rotinas de um Colaborador:
```bash
sqlite3 instance/pevapp22.db "SELECT r.name, rc.hours_used FROM routine_collaborators rc JOIN routines r ON rc.routine_id = r.id WHERE rc.employee_id = 1"
```

---

## 🐛 RESOLUÇÃO RÁPIDA DE PROBLEMAS

### Problema: "Nenhum colaborador encontrado"
**Solução**: 
- Verifique se há colaboradores cadastrados
- Verifique se o status está "active"

### Problema: "Todos com 0 horas"
**Solução**:
- Associe colaboradores às rotinas
- Defina horas_used > 0 em cada associação

### Problema: "Carga horária não aparece"
**Solução**:
- Edite o colaborador
- Preencha o campo "Carga Horária Semanal"
- Se o campo não aparecer, atualize o banco:
  ```sql
  ALTER TABLE employees ADD COLUMN weekly_hours REAL DEFAULT 40;
  UPDATE employees SET weekly_hours = 40;
  ```

### Problema: "API retorna erro 500"
**Solução**:
1. Verifique os logs do servidor
2. Teste a API diretamente
3. Verifique se o banco está acessível

---

## 📚 DOCUMENTAÇÃO COMPLETA

Para mais detalhes, consulte:
- **`ANALISE_MAO_DE_OBRA.md`** - Documentação técnica completa
- **`RESUMO_ANALISE_MAO_OBRA.md`** - Resumo da implementação

---

## 💡 DICAS PRO

1. **Atualize semanalmente**: Revise a análise toda segunda-feira
2. **Defina metas**: Estabeleça faixas ideais de utilização (ex: 70-85%)
3. **Use para 1:1**: Mostre os dados nas conversas individuais
4. **Planeje com antecedência**: Use para decidir férias e licenças
5. **Documente mudanças**: Anote quando redistribuir rotinas

---

## ✅ CHECKLIST FINAL

Antes de considerar pronto:

- [ ] Todos os colaboradores têm carga horária definida
- [ ] Todas as rotinas têm pelo menos 1 colaborador
- [ ] Horas_used estão preenchidas corretamente
- [ ] Análise carrega sem erros
- [ ] Cards de resumo mostram dados corretos
- [ ] Você consegue expandir/colapsar as rotinas

---

## 🎉 PRONTO!

Agora você tem uma visão completa da utilização da sua equipe!

**Use para**:
- ✅ Identificar sobrecargas
- ✅ Otimizar alocação
- ✅ Planejar contratações
- ✅ Melhorar processos
- ✅ Tomar decisões data-driven

---

**Dúvidas?** Consulte `ANALISE_MAO_DE_OBRA.md` para documentação completa.

**Versão**: 1.0  
**Data**: 11/10/2025

