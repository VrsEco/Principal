---
name: configr-engineering-gestao-versus
description: Especialização do Squad de Engenharia para o ambiente de produção Configr/CloudEZ do projeto Gestão Versus.
---

# 🛡️ Guia de Engenharia de Elite: Produção Configr (Gestão Versus)

Este documento contém o conhecimento destilado e protocolos críticos para manutenção e troubleshooting do ambiente de produção `app.gestaoversus.com.br`.

## 📍 Mapa da Infraestrutura

| Recurso | Detalhes do Ambiente APP 1 (Gestão Versus) | Detalhes do Ambiente APP 2 (Secundário) |
| :--- | :--- | :--- |
| **Ponto de Acesso** | `app.gestaoversus.com.br` | `app2.gestaoversus.com.br` (ou app2@...) |
| **Host SSH** | `ip-69-164-205-75.cloudezapp.io` (Porta `22122`) | `ip-69-164-205-75.cloudezapp.io` (Porta `22122`) |
| **Usuário SSH** | `app` | `app2` |
| **Banco de Dados** | `bdversusv2` | `bd_app_versus` |
| **Usuário do Banco**| `app` | `mff2000` |
| **Diretório Raiz (WWW)** | `/srv/appgestaoversuscombr.../www` | `/srv/app619.../www/public_html` (Varia de acordo com app) |
| **Diretório App v32** | `.../www/app32` | `.../www/public_html` |

## 📁 Arquivos Críticos

1.  **`uwsgi_configr.ini`** (No repositório em `www/app32`): Configuração mestre do uWSGI. Deve apontar para `module = passenger_wsgi:application`.
2.  **`passenger_wsgi.py`** (No servidor `www/`): Entry point para o uWSGI/Nginx.
3.  **`app32/.env`**: Contém as chaves `DATABASE_URL` e segredos de produção.
4.  **`app32/config.py`**: Gerenciador de configurações (com fix para ancoragem de diretório).

## 🪵 Logs e Diagnósticos

Se o site der `500 Internal Server Error`, verifique estes arquivos nesta ordem:

1.  **uWSGI Master Log** (O mais importante):
    *   Caminho: `/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/log/uwsgi/uwsgi.log`
    *   Uso: `tail -n 50 <log_path>`
2.  **Flask Error Trace**:
    *   Caminho: `www/error_trace.txt` (Dumps de falhas no startup).
3.  **Aplicação Logs**:
    *   Caminho: `www/app32/logs/app_logs.txt` (Logs de tempo de execução).

## 🚨 Bugs Frequentes e "Antídotos"

### 1. O "Fantasma do Django"
*   **Problema**: O Configr reseta a configuração de inicialização para o padrão Django.
*   **Sintoma**: `ModuleNotFoundError: No module named 'django'` no log do uWSGI.
*   **Antídoto**: Certifique-se que o arquivo `.ini` em `/etc/uwsgi/3.12/apps-enabled/` aponte para `module = passenger_wsgi:application`. Use o arquivo versionado `uwsgi_configr.ini` como base.

### 2. Falha de Autenticação "User postgres"
*   **Problema**: A aplicação falha ao ler o `.env` e usa o fallback de desenvolvimento.
*   **Sintoma**: `FATAL: password authentication failed for user "postgres"`.
*   **Antídoto**: Garantir que `config.py` use `Path(__file__)` para carregar o `.env`. Verifique se a `DATABASE_URL` no `.env` está correta e com URL encoding (ex: `*` -> `%2A`).

### 3. Loop de Timeout (SQLAlchemy .astext)
*   **Problema**: O `ChatTimeoutService` tenta comparar campos JSON (como `metadata_json`) usando API incompatível.
*   **Sintoma**: `Neither 'BinaryExpression' object ... has an attribute 'astext'`.
*   **Antídoto**: Use comparação manual em Python após buscar os objetos ou garanta o uso de `JSONB` no PostgreSQL se for filtrar via SQL direto.

### 4. My Work vazio - scope=me sem employee vinculado
*   **Problema**: O usuário (tipicamente admin/consultor) não tem `Employee` com `user_id` vinculado em produção.
*   **Sintoma**: `/my-work` mostra zero atividades apesar de haver dados no banco. `scope=company` funciona, mas `scope=me` retorna `[]`.
*   **Antídoto**: Corrigido em `services/my_work/discovery_service.py` — quando `my_employee_ids` está vazio, faz fallback para `scope=company` em vez de retornar `[]`. Para solução definitiva, vincular o `user_id` ao registro `Employee` correto no banco.

### 5. Deploy não atualiza o servidor (CI/CD falha silenciosamente)
*   **Problema**: O pipeline faz `git reset --hard origin/main` mas o servidor continua servindo código antigo porque o restart falha.
*   **Sintoma**: API retorna comportamento da versão anterior mesmo após push.
*   **Antídoto**: O método correto de restart no Configr é `touch /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/restart.txt`. Paths como `www/tmp/restart.txt` ou `etc/uwsgi/uwsgi.ini` NÃO funcionam para este ambiente.

## 🚀 Protocolos de Operação

### Reiniciar o Servidor
Para forçar o uWSGI a recarregar o código:
```bash
touch /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/restart.txt
```

### Teste de Sanidade (Remote Test Client)
Use o script `scripts/test_client_prod.py` (ou crie um temporário) para bater na rota `/login` usando o Virtualenv do servidor para ver o Traceback real sem passar pelo Nginx.

### Atualização via GIT (Manual via SSH)
```bash
# 1. SSH no servidor
ssh app@ip-69-164-205-75.cloudezapp.io -p 22122

# 2. Ir para o app (ATENÇÃO: está em www/app32, não em www/)
cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32

# 3. Puxar código
git fetch origin main
git reset --hard origin/main

# 4. Reiniciar (path correto)
touch /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/restart.txt
```

### Script Completo de Deploy Manual
```bash
BASE=/srv/appgestaoversuscombr.45a4cd4b.configr.cloud
$BASE/.virtualenv/3.12/bin/pip install -r $BASE/www/app32/requirements.txt --quiet
touch $BASE/www/restart.txt
```

---
> [!IMPORTANT]
> **Multi-tenancy**: Nunca esqueça do filtro `company_id` em qualquer intervenção direta no banco via SSH.

> [!WARNING]
> O app está em `www/app32`, NÃO em `www/`. Confundir esse path faz o `git pull` atualizar o diretório errado e o código em produção nunca muda!

