# 🚀 Guia Rápido - Como Iniciar o APP26

## ⚡ Início Rápido (5 minutos)

### 1️⃣ Criar arquivo .env
```bash
copy env.example .env
```

### 2️⃣ Configurar variáveis mínimas
Abra o arquivo `.env` e configure:

```env
# Obrigatório
FLASK_APP=app_pev.py
SECRET_KEY=minha-chave-secreta-123
DB_TYPE=sqlite
SQLITE_DB_PATH=instance/pevapp22.db
```

### 3️⃣ Verificar configuração
```bash
python verificar_config.py
```

### 4️⃣ Iniciar aplicação
```bash
python app_pev.py
```

### 5️⃣ Acessar no navegador
```
http://127.0.0.1:5002
```

---

## 📋 Checklist Pré-Execução

- [ ] Python 3.8+ instalado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Arquivo `.env` criado
- [ ] Variáveis mínimas configuradas
- [ ] Pasta `instance/` existe
- [ ] Verificação passou (`python verificar_config.py`)

---

## 🔧 Configurações Adicionais (Opcional)

### Para usar PostgreSQL:
```env
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pevapp22
POSTGRES_USER=postgres
POSTGRES_PASSWORD=senha123
```

### Para integrar IA (OpenAI):
```env
AI_PROVIDER=openai
AI_API_KEY=sk-sua-chave-aqui
```

### Para enviar e-mails:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app
```

### Para WhatsApp (Z-API):
```env
WHATSAPP_PROVIDER=z-api
WHATSAPP_API_KEY=sua-chave
WHATSAPP_INSTANCE_ID=sua-instancia
```

---

## 🐛 Problemas Comuns

### Erro: "No module named 'flask'"
```bash
pip install -r requirements.txt
```

### Erro: "No .env file found"
```bash
copy env.example .env
```

### Erro: "Database not found"
```bash
mkdir instance
python setup.py
```

### Aplicação não inicia
```bash
python verificar_config.py
```

---

## 📚 Documentação Completa

- **Configuração:** `CONFIGURACAO_AMBIENTE.md`
- **Análise:** `RESUMO_ANALISE_APP26.md`
- **README:** `README.md`

---

## ✅ Pronto!

Agora você pode:
- Criar planos estratégicos
- Gerenciar participantes
- Configurar OKRs
- Gerar relatórios em PDF
- Usar agentes de IA para análises

**Boa sorte! 🎉**




