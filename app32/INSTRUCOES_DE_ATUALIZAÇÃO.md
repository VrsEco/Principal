# 🚀 GUIA DE ATUALIZAÇÃO DE ELITE (CONFIGR)

Este projeto foi limpo de resquícios de Docker/Google Cloud. Agora seguimos a **Arquitetura v2.0 (Configr + Python 3.12 + PostgreSQL)**.

## 🛠️ Como Atualizar seu Site (Versionamento Full)

Para que o **Portal**, o **Header** e o **Banco de Dados** fiquem sempre idênticos ao seu local (DEV):

### 1. No seu Computador (DEV):
Sempre que fizer uma mudança e testar localmente:
```powershell
git commit -m "Descricao do que mudou"
git push origin main
```

### 2. No Servidor (Configr via SSH):
Acesse sua pasta `app32` e rode o script que a Squad de Elite criou para você:
```bash
./scripts/deploy_configr.sh
```

**O que este script faz (Missão Crítica):**
- **Git Force:** Limpa qualquer alteração acidental que tenha ocorrido no servidor.
- **Alembic Upgrade:** Atualiza as tabelas do PostgreSQL automaticamente com base nas suas classes Python.
- **Reinício Automático:** "Toca" o `passenger_wsgi.py` para forçar o servidor a recarregar o novo código (Header, Portal, etc).

---

## 🏗️ Regras de Ouro para Versionamento

1. **CUIDADO com Shadowing (Shadow Files):** Se você mover arquivos de lugar (ex: de `routes/` para `api/routes/`), certifique-se de que os arquivos antigos foram apagados no servidor. Arquivos duplicados fazem o Python carregar o código errado.
2. **Sempre use o Alembic:** Nunca rode SQL na mão no servidor. Se mudar o modelo de dados localmente, rode `flask db migrate` e o script de deploy fará o resto no servidor.
3. **Gerencie Dependências:** Toda nova biblioteca instalada localmente (ex: `pip install flask-migrate`) deve ser adicionada ao `requirements.txt` (`pip freeze > requirements.txt`). O servidor não as instalará automaticamente se você esquecer disso.
4. **Não mude nada direto no Configr:** Todas as mudanças devem vir do seu DEV via Git.

**Squad de Engenharia de Elite - Gestão Versus** 🚀
