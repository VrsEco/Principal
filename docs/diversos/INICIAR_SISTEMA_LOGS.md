# 🚀 GUIA RÁPIDO - Sistema de Logs Automáticos

## ⚡ Início Rápido (5 minutos)

### 1️⃣ Iniciar a Aplicação

```bash
python app_pev.py
```

### 2️⃣ Fazer Login

**URL:** http://localhost:5002/auth/login

**Credenciais:**
- **Email:** `admin@versus.com.br`
- **Senha:** `123456`

### 3️⃣ Acessar Dashboard de Auditoria

**URL:** http://localhost:5002/route-audit/

Aqui você verá:
- ✅ Total de rotas na aplicação
- ✅ Rotas com logging configurado
- ✅ Rotas sem logging (críticas)
- ✅ Cobertura percentual
- ✅ Lista completa de rotas

### 4️⃣ Acessar Logs de Usuários

**URL:** http://localhost:5002/logs/

Aqui você pode:
- ✅ Ver todos os logs registrados
- ✅ Filtrar por usuário, entidade, ação
- ✅ Exportar para CSV
- ✅ Ver estatísticas

---

## 🎯 Como Adicionar Logs em uma Nova Rota

### Passo 1: Adicionar o Import

No topo do seu arquivo (exemplo: `modules/grv/__init__.py`):

```python
from middleware.auto_log_decorator import auto_log_crud
```

### Passo 2: Adicionar o Decorador

Antes da sua rota CRUD:

```python
@grv_bp.route('/api/company/<int:company_id>/projects', methods=['POST'])
@auto_log_crud('project')  # ← Adicione esta linha!
def create_project(company_id):
    # Seu código aqui
    return jsonify(result)
```

### Passo 3: Pronto! 🎉

O sistema **automaticamente** irá:
- ✅ Detectar a operação (CREATE, UPDATE, DELETE)
- ✅ Capturar dados do usuário
- ✅ Registrar valores antigos e novos
- ✅ Salvar no banco de dados
- ✅ Mostrar no dashboard de logs

---

## 🔍 Como Auditar Rotas Sem Logs

### Método 1: Via Interface Web (Recomendado)

1. Acesse: http://localhost:5002/route-audit/
2. No filtro, selecione: **"Sem Logging (Crítico)"**
3. Veja a lista de rotas que precisam de logs
4. Clique em **"Incluir Log"** para ver o guia de implementação
5. Copie e cole o código fornecido

### Método 2: Via API

```bash
# Ver resumo da auditoria
curl http://localhost:5002/route-audit/api/summary

# Ver rotas sem logging
curl http://localhost:5002/route-audit/api/routes/without-logging

# Exportar relatório
curl http://localhost:5002/route-audit/api/export-report
```

---

## 📊 Tipos de Entidades Suportados

O sistema detecta automaticamente estes tipos de entidade:

- `company` - Empresas
- `plan` - Planos
- `participant` - Participantes
- `project` - Projetos
- `indicator` - Indicadores
- `indicator_group` - Grupos de indicadores
- `indicator_goal` - Metas de indicadores
- `indicator_data` - Dados de indicadores
- `okr` - OKRs
- `meeting` - Reuniões
- `process` - Processos
- `employee` - Colaboradores
- `department` - Departamentos
- `portfolio` - Portfólios
- `driver` - Direcionadores
- `routine` - Rotinas
- `routine_task` - Tarefas de rotina
- `process_instance` - Instâncias de processo
- `process_activity` - Atividades de processo

**Adicionar novo tipo?** Edite `middleware/auto_log_decorator.py`:

```python
ENTITY_TYPE_PATTERNS = {
    r'/my-entity/(\d+)': 'my_entity',  # ← Adicione aqui
}
```

---

## 🎓 Exemplos Práticos

### Exemplo 1: Criar Indicador com Log

```python
from middleware.auto_log_decorator import auto_log_crud

@grv_bp.route('/api/company/<int:company_id>/indicators', methods=['POST'])
@auto_log_crud('indicator')
def api_create_indicator(company_id: int):
    data = request.json
    
    # Seu código de criação aqui
    indicator = create_indicator_logic(company_id, data)
    
    return jsonify({'success': True, 'data': indicator})
    # O decorador registrará automaticamente o log!
```

**Resultado no Log:**
- ✅ **Ação:** CREATE
- ✅ **Entidade:** indicator
- ✅ **Usuário:** admin@versus.com.br
- ✅ **Valores Novos:** {name: "...", code: "..."}
- ✅ **Company ID:** 1
- ✅ **Data/Hora:** 2025-10-18 14:30:00

### Exemplo 2: Atualizar com Log

```python
@grv_bp.route('/api/company/<int:company_id>/indicators/<int:indicator_id>', methods=['PUT'])
@auto_log_crud('indicator')
def api_update_indicator(company_id: int, indicator_id: int):
    data = request.json
    
    # O decorador capturará os valores ANTES da atualização
    indicator = update_indicator_logic(indicator_id, data)
    
    return jsonify({'success': True, 'data': indicator})
    # Log registrará valores antigos E novos!
```

### Exemplo 3: Deletar com Log

```python
@grv_bp.route('/api/company/<int:company_id>/indicators/<int:indicator_id>', methods=['DELETE'])
@auto_log_crud('indicator')
def api_delete_indicator(company_id: int, indicator_id: int):
    # O decorador capturará os dados ANTES da exclusão
    delete_indicator_logic(indicator_id)
    
    return jsonify({'success': True})
    # Log registrará todos os dados deletados!
```

---

## 🔧 Troubleshooting Rápido

### Problema: "Acesso negado"
**Solução:** Faça login como admin (`admin@versus.com.br` / `123456`)

### Problema: Logs não aparecem
**Solução:**
1. Verifique se está logado
2. Verifique se o decorador está ANTES da função
3. Verifique se retorna JSON com `success` e `data`

### Problema: Erro ao acessar /route-audit/
**Solução:**
1. Reinicie a aplicação
2. Verifique se o blueprint foi registrado
3. Veja o console para erros

### Problema: Rota não detectada na auditoria
**Solução:**
1. Verifique se o método é POST, PUT, PATCH ou DELETE
2. Verifique se o blueprint está registrado
3. Atualize a página (F5)

---

## 📖 Documentação Completa

Para documentação detalhada, veja:
- **`SISTEMA_LOGS_AUTOMATICOS_COMPLETO.md`** - Documentação completa
- **`SISTEMA_LOGS_USUARIOS_IMPLEMENTADO.md`** - Sistema base de logs

---

## ✅ Checklist de Verificação

### Antes de Começar
- [ ] Aplicação rodando (`python app_pev.py`)
- [ ] Login funcionando
- [ ] Banco de dados acessível

### Testar Sistema
- [ ] Acessar `/route-audit/` e ver dashboard
- [ ] Acessar `/logs/` e ver logs existentes
- [ ] Criar um indicador e verificar log
- [ ] Atualizar um indicador e verificar log
- [ ] Exportar relatório de auditoria

### Adicionar em Nova Rota
- [ ] Import do decorador adicionado
- [ ] Decorador `@auto_log_crud(tipo)` antes da rota
- [ ] Testar CREATE
- [ ] Testar UPDATE
- [ ] Testar DELETE
- [ ] Verificar logs no dashboard

---

## 🎉 Pronto!

Seu sistema de logs automáticos está **100% funcional**!

### Próximos Passos

1. ✅ Revisar rotas sem logging no dashboard
2. ✅ Adicionar decoradores nas rotas críticas
3. ✅ Treinar equipe no uso do sistema
4. ✅ Estabelecer política de retenção de logs

---

**Dúvidas?** Consulte a documentação completa em `SISTEMA_LOGS_AUTOMATICOS_COMPLETO.md`

🚀 **Bom trabalho!**

