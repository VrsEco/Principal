# ⚠️ ERRO 404 - Blueprint não carregado

## Problema

Você está recebendo erro **404** ao acessar `/route-audit/` porque o servidor está rodando a **versão antiga** do código.

---

## ✅ Solução Rápida

### **Windows - Use o Script Automático:**

```bash
reiniciar_servidor.bat
```

Este script irá:
1. ✓ Parar processos Python antigos
2. ✓ Limpar cache
3. ✓ Reiniciar o servidor com o novo código

---

### **Solução Manual:**

#### Passo 1: Parar o Servidor

**Opção A - Via Terminal:**
```bash
# Ver processos Python
tasklist | findstr python

# Matar processo (substitua XXXX pelo PID)
taskkill /F /PID XXXX
```

**Opção B - Via Ctrl+C:**
- Se o servidor está rodando em um terminal visível
- Pressione **Ctrl+C** no terminal

**Opção C - Via Gerenciador de Tarefas:**
- Ctrl+Shift+Esc
- Procure `python.exe`
- Finalizar Tarefa

#### Passo 2: Limpar Cache (Opcional mas Recomendado)

```bash
# Windows CMD
rmdir /s /q __pycache__
rmdir /s /q middleware\__pycache__
rmdir /s /q services\__pycache__
rmdir /s /q api\__pycache__

# Windows PowerShell
Remove-Item -Recurse -Force __pycache__, middleware\__pycache__, services\__pycache__, api\__pycache__
```

#### Passo 3: Reiniciar

```bash
python app_pev.py
```

#### Passo 4: Verificar Mensagens

Você DEVE ver estas mensagens:

```
Sistema de logs de usuários integrado com sucesso!
Sistema de auditoria de rotas integrado com sucesso!  ← IMPORTANTE!
```

Se não ver a segunda mensagem, há um erro na integração.

---

## 🔍 Verificar se Funcionou

### Teste Rápido:

```bash
python verificar_servidor.py
```

Deve mostrar:
```
[OK] Rota existe! (redirecionando para login)
```

### Teste no Navegador:

Acesse: http://localhost:5002/route-audit/

Deve redirecionar para o **login** (não mais 404).

---

## ❌ Se Ainda Não Funcionar

### 1. Verificar Erros no Console

Ao iniciar `python app_pev.py`, veja se há erros como:

```
ImportError: cannot import name 'route_audit_bp'
ModuleNotFoundError: No module named 'X'
SyntaxError: ...
```

### 2. Verificar se Arquivos Existem

```bash
python testar_sistema_logs.py
```

Deve mostrar todos `[OK]`.

### 3. Verificar Imports

Execute:
```python
python -c "from api.route_audit import route_audit_bp; print('OK')"
```

Deve imprimir `OK`.

### 4. Ver Log de Erro

Se houver erro ao importar, o Python mostrará no console.

---

## 📞 Debug Avançado

Se nada funcionar, execute este comando para ver o stack trace completo:

```bash
python -c "import sys; sys.path.insert(0, '.'); from app_pev import app; print('Blueprints:', list(app.blueprints.keys()))"
```

Deve incluir `'route_audit'` na lista.

---

## ✅ Checklist

- [ ] Parei o servidor antigo
- [ ] Limpei o cache Python
- [ ] Reiniciei com `python app_pev.py`
- [ ] Vi a mensagem "Sistema de auditoria de rotas integrado com sucesso!"
- [ ] Testei http://localhost:5002/route-audit/
- [ ] Redirecionou para login (não mais 404)

---

## 🎯 Depois de Reiniciar

Acesse:
- **Login:** http://localhost:5002/auth/login
- **User:** admin@versus.com.br
- **Pass:** 123456

Depois:
- **Dashboard:** http://localhost:5002/route-audit/

