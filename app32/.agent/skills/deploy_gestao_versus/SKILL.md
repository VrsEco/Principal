---
name: deploy_gestao_versus
description: Protocolo de deploy atômico e versionado para o ambiente Configr (app.gestaoversus.com.br)
---

# Protocolo de Deploy: Gestão Versus (Configr)

Esta habilidade deve ser invocada SEMPRE que o usuário solicitar "subir o código", "deploy", "produção" ou "atualizar o site".

## 📋 Pré-Deploy (Local/DEV)
1. **Verificar Alterações:** Executar `git status` para garantir que nada foi esquecido.
2. **Migrações de Banco (Alembic):** 
   - Se houver alteração nos modelos Python, gerar a migração: `flask db migrate -m "descricao_atômica"`
   - Verificar se o arquivo `.py` foi criado em `migrations/versions/`.
3. **Commit de Elite:** 
   - Commitar as mudanças: `git commit -m "SQUAD: Descrição técnica do que mudou"`
   - Enviar para o repositório central: `git push origin main`

## 🏗️ Execução (No Servidor Configr via SSH)
Este passo deve ser orientado pela IA, garantindo que o seguinte comando seja rodado na pasta `app32` do servidor:

```bash
./scripts/deploy_configr.sh
```

### O que o script de deploy automatiza:
- **Sincronia Total:** `git reset --hard origin/main` (Limpa lixos e conflitos locais no servidor).
- **Banco Blindado:** `flask db upgrade` (Aplica migrações pendentes).
- **Reinício de Memória:** `touch passenger_wsgi.py` (Força o Passenger/Configr a recarregar o Header, Portal e Lógica).

## 🧪 Validação Pós-Deploy
1. **Verificar Header:** Acessar o site e confirmar visualmente a atualização.
2. **Verificar Portal:** Logar no Portal e testar as novas funcionalidades.
3. **Verificar Banco:** Confirmar se não há erros 500 originados por falta de colunas.

## 🚧 Lições de Elite (Evitar Erros Comuns)
- **Shadowing (Arquivos Fantasmas):** Se houver arquivos duplicados fora da pasta `api/routes/` no servidor (ex: `app32/auth.py`), o Python pode carregar a versão errada. O deploy deve limpar ou alertar sobre redundâncias.
- **Deep Restart (Reinício Profundo):** Sempre tocar o `passenger_wsgi.py` da raiz E o `tmp/restart.txt`.
- **Sync de Dependências:** Garantir que novas libs (ex: `flask-migrate`) estejam sempre no `requirements.txt`.

---
**Status da Stack:** Python 3.12 | Flask | PostgreSQL | Configr Apache/Passenger
