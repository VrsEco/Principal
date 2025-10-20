# 🔧 Configuração do Ambiente - APP26

## 📋 Pré-requisitos

- Python 3.8 ou superior
- PostgreSQL (opcional, para produção)
- Redis (opcional, para tarefas assíncronas)

---

## ⚙️ Configuração Inicial

### 1. Criar Arquivo .env

O arquivo `.env` **NÃO** está incluído no repositório por segurança. Você precisa criá-lo manualmente:

```bash
# No diretório raiz do projeto (app26), crie o arquivo .env
copy env.example .env
# OU em Linux/Mac:
cp env.example .env
```

### 2. Configurar Variáveis de Ambiente

Edite o arquivo `.env` com suas configurações:

#### **Banco de Dados (SQLite - Desenvolvimento)**
```env
DB_TYPE=sqlite
SQLITE_DB_PATH=instance/pevapp22.db
```

#### **Banco de Dados (PostgreSQL - Produção)**
```env
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pevapp22
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha_aqui
```

#### **Flask**
```env
FLASK_ENV=development
FLASK_APP=app_pev.py
SECRET_KEY=gere-uma-chave-secreta-forte-aqui
```

#### **Autenticação**
```env
LOGIN_DISABLED=False
```

#### **E-mail (Gmail)**
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app
MAIL_DEFAULT_SENDER=seu-email@gmail.com
```

💡 **Dica:** Para Gmail, use uma [Senha de App](https://support.google.com/accounts/answer/185833)

#### **Inteligência Artificial (OpenAI)**
```env
AI_PROVIDER=openai
AI_API_KEY=sk-sua-chave-openai-aqui
```

**Outros provedores disponíveis:**
- `anthropic` (Claude)
- `local` (sem integração externa)

#### **WhatsApp (Z-API)**
```env
WHATSAPP_PROVIDER=z-api
WHATSAPP_API_KEY=sua-chave-z-api
WHATSAPP_INSTANCE_ID=sua-instancia-id
```

**Outros provedores disponíveis:**
- `twilio`
- `webhook`
- `local` (desabilita envio)

#### **Redis (Opcional)**
```env
REDIS_URL=redis://localhost:6379/0
```

#### **Servidor**
```env
SERVER_HOST=127.0.0.1
SERVER_PORT=5002
DEBUG=False
```

---

## 🚀 Instalação e Execução

### Método 1: Script Automático (Recomendado)

```bash
# No diretório app26
inicio.bat
```

### Método 2: Manual

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Inicializar banco de dados (se necessário)
python setup.py

# 3. Executar aplicação
python app_pev.py
```

### Método 3: Ambiente Virtual (Recomendado para Desenvolvimento)

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar
python app_pev.py
```

---

## 📊 Estrutura de Banco de Dados

### SQLite (Desenvolvimento)
- Arquivo: `instance/pevapp22.db`
- Criado automaticamente na primeira execução
- Ideal para desenvolvimento e testes

### PostgreSQL (Produção)
- Configure as variáveis de ambiente
- Execute migrações se necessário:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

---

## 🔍 Verificação da Configuração

Execute o script de teste:

```bash
python test_basic_config.py
```

Este script irá verificar:
- ✅ Conexão com banco de dados
- ✅ Variáveis de ambiente configuradas
- ✅ Dependências instaladas
- ✅ Estrutura de diretórios

---

## 🐛 Problemas Comuns

### Erro: "No module named 'dotenv'"
```bash
pip install python-dotenv
```

### Erro: "Database not found"
- Verifique se a pasta `instance/` existe
- Execute: `python setup.py`

### Erro: "SECRET_KEY not configured"
- Certifique-se de que o arquivo `.env` existe
- Adicione: `SECRET_KEY=sua-chave-secreta`

### Erro de integração com IA
- Verifique se `AI_API_KEY` está configurada
- Teste com: `AI_PROVIDER=local` (desabilita integração)

### Erro de envio de e-mail
- Verifique credenciais SMTP
- Para Gmail, use senha de app
- Teste com: `MAIL_SERVER=` (desabilita envio)

---

## 📝 Nomenclaturas do Projeto

### Nome do Projeto
- **Nome Técnico:** PEVAPP22
- **Versão Atual:** APP26
- **Nome Amigável:** Sistema de Planejamento Estratégico

### Arquivo Principal
- `app_pev.py` (NÃO é app_new.py)

### Banco de Dados
- **Desenvolvimento:** `instance/pevapp22.db` (SQLite)
- **Produção:** `pevapp22` (PostgreSQL)

### Porta Padrão
- **5002** (http://127.0.0.1:5002)

---

## 🔒 Segurança

### ⚠️ NUNCA commite:
- Arquivo `.env`
- Chaves de API
- Senhas de banco de dados
- Tokens de acesso

### ✅ Use `.env` para:
- Todas as credenciais
- Configurações sensíveis
- Chaves de integração

---

## 📞 Suporte

Para problemas de configuração:
1. Verifique este documento
2. Consulte `README.md`
3. Execute `python test_basic_config.py`
4. Verifique os logs da aplicação

---

**Última atualização:** Outubro 2025




