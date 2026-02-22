# 📚 Guia de Conceitos - Virtualização e Deploy

## 🎯 Entendendo o que Criamos

Um guia completo para entender cada tecnologia e conceito usado na virtualização do projeto.

---

## 📖 ÍNDICE POR CONCEITO

1. [Docker - O que é e por que usar?](#docker)
2. [Docker Compose - Orquestrando containers](#docker-compose)
3. [Nginx - Servidor web reverso](#nginx)
4. [PostgreSQL vs SQLite](#banco-de-dados)
5. [Redis - Cache em memória](#redis)
6. [Celery - Tarefas assíncronas](#celery)
7. [Gunicorn - Servidor WSGI](#gunicorn)
8. [CI/CD - Deploy automático](#cicd)
9. [Backup - Proteção de dados](#backup)
10. [SSL/HTTPS - Segurança](#ssl)

---

## 🐳 DOCKER

### O que é?
Docker é como uma "máquina virtual leve" que empacota sua aplicação com tudo que ela precisa para rodar.

### Conceitos Principais

#### Container
- É uma "caixinha isolada" que roda sua aplicação
- Tem tudo dentro: Python, bibliotecas, código
- Funciona igual em qualquer lugar (seu PC, servidor, nuvem)

#### Imagem
- É o "molde" para criar containers
- Como uma receita: diz o que instalar e configurar
- Nosso arquivo: **`Dockerfile`**

#### Por que usar?
```
❌ SEM Docker:
Desenvolvedor: "Funciona na minha máquina!"
Servidor: "Aqui não funciona..." 😢

✅ COM Docker:
Desenvolvedor: "Funciona no container!"
Servidor: "Aqui também funciona!" 😊
```

### Arquivo: `Dockerfile`

```dockerfile
FROM python:3.9-slim        # Começar com Python instalado
WORKDIR /app                # Pasta de trabalho
COPY requirements.txt .     # Copiar dependências
RUN pip install -r ...      # Instalar dependências
COPY . .                    # Copiar código
CMD ["gunicorn", ...]       # Comando para rodar
```

**O que faz:**
1. Pega uma imagem base (Python 3.9)
2. Instala dependências do projeto
3. Copia código da aplicação
4. Define comando de inicialização

**Analogia:**
Imagine construir uma casa:
- `FROM` = Terreno/fundação
- `COPY` = Trazer materiais
- `RUN` = Construir
- `CMD` = "Como usar a casa"

---

## 🎼 DOCKER COMPOSE

### O que é?
Orquestra múltiplos containers trabalhando juntos.

### Por que preciso?
Sua aplicação não é só Flask. Você precisa de:
- Flask App (aplicação)
- PostgreSQL (banco)
- Redis (cache)
- Nginx (servidor web)
- Celery (tarefas background)

Docker Compose gerencia todos de uma vez!

### Arquivos

#### `docker-compose.yml` (Produção)
```yaml
services:
  app:           # Flask App
    build: .
    ports:
      - "5002:5002"
    depends_on:
      - db
  
  db:            # PostgreSQL
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=...
  
  redis:         # Redis Cache
    image: redis:7
  
  nginx:         # Servidor Web
    image: nginx
    ports:
      - "80:80"
      - "443:443"
```

**O que faz:**
- Define todos os containers necessários
- Conecta eles em uma rede privada
- Gerencia inicialização e dependências

#### `docker-compose.dev.yml` (Desenvolvimento)
```yaml
services:
  app_dev:
    volumes:
      - .:/app    # Hot-reload: código atualiza automático
    environment:
      - FLASK_DEBUG=1
    command: python app_pev.py
```

**Diferenças Dev vs Prod:**

| Feature | Desenvolvimento | Produção |
|---------|----------------|----------|
| Debug | ✅ Ativo | ❌ Desativado |
| Hot-reload | ✅ Código atualiza | ❌ Precisa rebuild |
| Banco | SQLite ou PostgreSQL | PostgreSQL sempre |
| Servidor | Flask dev server | Gunicorn |
| SSL | ❌ Não precisa | ✅ Obrigatório |

### Comandos Úteis

```bash
# Iniciar todos os containers
docker-compose up -d

# Ver o que está rodando
docker-compose ps

# Ver logs
docker-compose logs -f app

# Parar tudo
docker-compose down

# Rebuild (após mudanças no código)
docker-compose up -d --build
```

**Analogia:**
Docker Compose é como um maestro de orquestra:
- Cada container = um músico
- docker-compose.yml = partitura
- `up` = começar a tocar
- `down` = parar

---

## 🌐 NGINX

### O que é?
Servidor web que fica na "porta de entrada" da sua aplicação.

### Por que preciso?
Flask sozinho não é bom para produção. Nginx faz:

1. **Reverse Proxy** - Recebe requisições e repassa para Flask
2. **SSL/HTTPS** - Criptografia (cadeado no navegador)
3. **Static Files** - Serve CSS/JS diretamente (mais rápido)
4. **Load Balancing** - Distribui carga entre múltiplos servidores
5. **Rate Limiting** - Proteção contra DDoS

### Como funciona?

```
Cliente (Navegador)
    ↓
HTTPS (443) → NGINX
    ↓
HTTP (5002) → Flask App
    ↓
PostgreSQL
```

### Arquivo: `nginx/nginx.conf`

```nginx
server {
    listen 443 ssl;                    # Porta HTTPS
    server_name congigr.com;           # Seu domínio
    
    ssl_certificate /path/to/cert;     # Certificado SSL
    
    location / {
        proxy_pass http://app:5002;    # Repassa para Flask
    }
    
    location /static/ {
        alias /app/static/;             # Serve arquivos estáticos
    }
}
```

**O que faz:**
- Escuta na porta 443 (HTTPS)
- Requisições normais → Flask
- Arquivos /static/ → Serve direto (mais rápido)
- Adiciona headers de segurança

**Analogia:**
Nginx é como o recepcionista de um hotel:
- Recebe clientes (requisições)
- Direciona para o quarto certo (Flask)
- Entrega correspondência (static files)
- Controla acesso (segurança)

---

## 💾 BANCO DE DADOS

### PostgreSQL vs SQLite

#### SQLite
```
✅ Vantagens:
- Arquivo único (.db)
- Zero configuração
- Perfeito para desenvolvimento

❌ Limitações:
- Um usuário por vez
- Sem concorrência real
- Não escala
```

#### PostgreSQL
```
✅ Vantagens:
- Múltiplos usuários simultâneos
- Transações ACID
- Escala muito bem
- Recursos avançados

❌ Desvantagens:
- Precisa servidor separado
- Mais configuração
```

### Por que migramos para PostgreSQL?

```python
# Desenvolvimento: SQLite OK
DATABASE_URL = 'sqlite:///database.db'

# Produção: PostgreSQL OBRIGATÓRIO
DATABASE_URL = 'postgresql://user:pass@host:5432/db'
```

**Em produção, SQLite não aguenta:**
- 10+ usuários simultâneos
- Escrita concorrente
- Backup online
- Replicação

### Como funciona no Docker?

```yaml
services:
  db:
    image: postgres:15          # Imagem do PostgreSQL
    environment:
      POSTGRES_USER: usuario
      POSTGRES_PASSWORD: senha
      POSTGRES_DB: banco
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persistir dados
```

**Volumes:**
- Dados ficam FORA do container
- Se container morrer, dados permanecem
- Como um HD externo

---

## ⚡ REDIS

### O que é?
Banco de dados **em memória** super rápido.

### Por que usar?
```
PostgreSQL (disco):  ~5ms por query
Redis (memória):    ~0.1ms por query

50x mais rápido! 🚀
```

### Casos de Uso

#### 1. Cache
```python
# Sem cache
@app.route('/dashboard')
def dashboard():
    data = query_complexa()  # 2 segundos
    return render(data)

# Com cache
@app.route('/dashboard')
@cache.cached(timeout=300)  # 5 minutos
def dashboard():
    data = query_complexa()  # 2 segundos na primeira vez
    return render(data)       # 0.001s nas próximas
```

#### 2. Sessões
```python
# Guardar sessão do usuário
SESSION_TYPE = 'redis'
SESSION_REDIS = redis_client
```

#### 3. Filas (com Celery)
```python
# Enviar tarefa para background
send_email.delay(to='user@example.com')  # Retorna imediato
```

### No Docker

```yaml
redis:
  image: redis:7-alpine        # Redis versão 7
  ports:
    - "6379:6379"
```

**Analogia:**
- PostgreSQL = Arquivo no HD (lento, permanente)
- Redis = Bloco de notas na mesa (rápido, temporário)

---

## 🔄 CELERY

### O que é?
Sistema de **filas de tarefas** para processar coisas em background.

### Por que preciso?

**❌ Sem Celery:**
```python
@app.route('/send-report')
def send_report():
    generate_pdf()      # 10 segundos
    send_email()        # 5 segundos
    return 'OK'         # Usuário espera 15 segundos! 😴
```

**✅ Com Celery:**
```python
@app.route('/send-report')
def send_report():
    generate_and_send.delay()  # 0.1 segundo
    return 'Em processamento'   # Usuário feliz! 😊

@celery.task
def generate_and_send():
    generate_pdf()      # Roda em background
    send_email()        # Usuário não espera
```

### Casos de Uso

1. **Envio de emails** - Não travar requisição
2. **Geração de relatórios** - Processar em background
3. **Processamento de imagens** - Redimensionar uploads
4. **Tarefas agendadas** - Backup diário, limpeza

### Como funciona?

```
Flask App
    ↓ (envia tarefa)
Redis (fila)
    ↓ (pega tarefa)
Celery Worker (processa)
    ↓ (salva resultado)
Redis (resultado)
    ↓ (consulta)
Flask App
```

### No Docker

```yaml
celery_worker:
  build: .
  command: celery -A app_pev.celery worker --loglevel=info
  depends_on:
    - redis
```

**Analogia:**
- Flask = Garçom (atende pedidos)
- Celery = Cozinha (prepara pedidos)
- Redis = Balcão (passa pedidos)

---

## 🚀 GUNICORN

### O que é?
Servidor WSGI **profissional** para rodar Flask em produção.

### Flask Dev Server vs Gunicorn

#### Flask Dev Server (desenvolvimento)
```bash
python app_pev.py

✅ Debug mode
✅ Hot-reload
✅ Mensagens de erro detalhadas

❌ 1 requisição por vez
❌ Lento
❌ Inseguro
```

#### Gunicorn (produção)
```bash
gunicorn app_pev:app --workers 4

✅ Múltiplos workers (4 processos)
✅ Rápido e eficiente
✅ Seguro

❌ Sem debug
❌ Sem hot-reload
```

### Workers

```
Cliente 1 → Worker 1
Cliente 2 → Worker 2
Cliente 3 → Worker 3
Cliente 4 → Worker 4
Cliente 5 → Worker 1 (reutiliza)
```

**Quantos workers?**
```
workers = (CPU_cores * 2) + 1

2 CPUs = 5 workers
4 CPUs = 9 workers
```

### No Docker

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "4", "app_pev:app"]
```

**Analogia:**
- Flask dev = Um atendente (lento)
- Gunicorn = Vários atendentes (rápido)

---

## 🔄 CI/CD

### O que é?
**CI** = Continuous Integration (Integração Contínua)  
**CD** = Continuous Deployment (Deploy Contínuo)

### Sem CI/CD (Manual) 😓

```
1. Fazer alteração no código
2. Rodar testes localmente
3. Fazer commit
4. Conectar no servidor (SSH)
5. git pull
6. Reiniciar aplicação
7. Verificar se funcionou
8. Se deu erro, reverter tudo

Tempo: 30 minutos
Chance de erro: Alta
```

### Com CI/CD (Automático) 😊

```
1. Fazer alteração no código
2. git push

GitHub Actions:
✅ Roda testes automaticamente
✅ Build Docker automaticamente
✅ Deploy automaticamente
✅ Rollback se der erro

Tempo: 2 minutos
Chance de erro: Baixa
```

### GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd-production.yml

on:
  push:
    branches: [main]           # Quando fizer push em main

jobs:
  test:                         # 1. Rodar testes
    runs-on: ubuntu-latest
    steps:
      - checkout code
      - run tests
  
  build:                        # 2. Build Docker
    needs: test
    steps:
      - build image
      - push to registry
  
  deploy:                       # 3. Deploy
    needs: build
    steps:
      - deploy to production
```

### O que acontece?

```
git push origin main
    ↓
GitHub detecta push
    ↓
GitHub Actions inicia
    ↓
1. Roda testes (pytest)
    ↓ (se passar)
2. Build Docker image
    ↓
3. Push para Docker Hub
    ↓
4. Deploy no servidor/GCP
    ↓
✅ Aplicação atualizada!
```

**Arquivos criados:**
- `.github/workflows/ci-cd-production.yml` - Deploy produção
- `.github/workflows/ci-cd-development.yml` - Deploy dev
- `.github/workflows/backup.yml` - Backup diário

---

## 💾 BACKUP

### Por que fazer backup?

```
❌ Sem backup:
HD falha → Dados perdidos → Empresa quebra 💀

✅ Com backup:
HD falha → Restaura backup → Tudo normal 😊
```

### Estratégia 3-2-1

```
3 cópias dos dados
2 tipos de mídia diferentes
1 cópia offsite (nuvem)
```

### Nosso sistema

```python
# scripts/backup_database.py

1. Faz dump do PostgreSQL
   ↓
2. Comprime (gzip)
   ↓
3. Upload para S3/GCS
   ↓
4. Mantém últimos 30 dias
   ↓
5. Deleta backups antigos
```

### Tipos de Backup

#### 1. Manual
```bash
python scripts/backup_database.py
```

#### 2. Agendado (CRON)
```bash
# Todo dia às 3:00 AM
0 3 * * * python /app/scripts/backup_database.py
```

#### 3. GitHub Actions
```yaml
# .github/workflows/backup.yml
schedule:
  - cron: '0 3 * * *'  # Diário 3AM UTC
```

### Onde guardar?

#### Local (Servidor)
```
✅ Rápido
❌ Se servidor pegar fogo, perde tudo
```

#### S3/GCS (Nuvem)
```
✅ Seguro
✅ Redundante
✅ Durável (99.999999999%)
❌ Custo (barato, mas tem)
```

### Restauração

```bash
python scripts/restore_database.py

1. Lista backups disponíveis
2. Escolhe qual restaurar
3. Faz backup do atual (segurança)
4. Restaura escolhido
5. Verifica integridade
```

**Analogia:**
Backup é como seguro:
- Espera nunca precisar
- Mas se precisar, salva sua vida

---

## 🔒 SSL/HTTPS

### O que é?

**HTTP** = Protocolo sem segurança (tudo em texto)  
**HTTPS** = HTTP + SSL/TLS (criptografado)

### Por que preciso?

```
❌ HTTP (sem SSL):
Usuário: senha123
Hacker escuta: senha123 😈

✅ HTTPS (com SSL):
Usuário: senha123
Hacker escuta: d8j2k9#$k2... 🤷
```

### Como funciona?

```
1. Cliente pede conexão HTTPS
2. Servidor envia certificado SSL
3. Cliente verifica certificado
4. Geram chave de sessão
5. Toda comunicação criptografada
```

### Obtendo certificado SSL

#### Let's Encrypt (GRÁTIS!)
```bash
# Instalar certbot
sudo apt install certbot

# Obter certificado
sudo certbot certonly --standalone -d congigr.com

# Certificados em:
/etc/letsencrypt/live/congigr.com/
  ├── fullchain.pem   # Certificado
  └── privkey.pem     # Chave privada
```

#### Renovação automática
```bash
# Certificado válido por 90 dias
# Renovar automaticamente:
0 3 * * * certbot renew --quiet
```

### No Nginx

```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/congigr.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/congigr.com/privkey.pem;
    
    # Redirecionar HTTP → HTTPS
    if ($scheme = http) {
        return 301 https://$server_name$request_uri;
    }
}
```

**Analogia:**
- HTTP = Cartão postal (todos veem)
- HTTPS = Envelope lacrado (só destinatário vê)

---

## 📊 RESUMO VISUAL

### Arquitetura Completa

```
Internet (Usuários)
    ↓ HTTPS (443)
┌─────────────────────┐
│  NGINX (Reverse Proxy) │
│  - SSL/TLS           │
│  - Rate Limiting     │
│  - Static Files      │
└─────────────────────┘
    ↓ HTTP (5002)
┌─────────────────────┐
│  GUNICORN (4 workers) │
│  - Flask App         │
│  - 4 processos       │
└─────────────────────┘
    ↓
┌──────────┬──────────┬──────────┐
│PostgreSQL│  Redis   │  Celery  │
│(Dados)   │ (Cache)  │(Background)│
└──────────┴──────────┴──────────┘
    ↓
┌─────────────────────┐
│  Backup (S3/GCS)    │
│  - Diário 3AM       │
│  - 30 dias retenção │
└─────────────────────┘
```

### Fluxo de uma Requisição

```
1. Usuário acessa https://congigr.com/dashboard
   ↓
2. DNS resolve para IP do servidor
   ↓
3. NGINX recebe na porta 443 (HTTPS)
   ↓
4. NGINX decripta SSL
   ↓
5. NGINX repassa para Gunicorn (porta 5002)
   ↓
6. Gunicorn escolhe worker disponível
   ↓
7. Worker executa Flask route
   ↓
8. Flask consulta Redis (cache)
   - Se tem cache → retorna
   - Se não tem → consulta PostgreSQL
   ↓
9. Flask renderiza template
   ↓
10. Resposta volta por todo caminho
    ↓
11. NGINX adiciona headers de segurança
    ↓
12. NGINX criptografa com SSL
    ↓
13. Usuário recebe página
```

---

## 🎓 CONCEITOS IMPORTANTES

### Portas

```
80   = HTTP (não criptografado)
443  = HTTPS (criptografado)
5002 = Flask App (interno)
5432 = PostgreSQL (interno)
6379 = Redis (interno)
8080 = Adminer (dev only)
```

### Ambientes

```
Development:
- Código em teste
- Debug ativo
- Pode quebrar

Staging:
- Cópia da produção
- Testes finais
- Quase idêntico a prod

Production:
- Usuários reais
- Dados reais
- NUNCA pode quebrar
```

### Volumes Docker

```
Sem volume:
Container morre → Dados perdidos 💀

Com volume:
Container morre → Dados salvos ✅

# docker-compose.yml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

### Networks Docker

```
# Todos os containers na mesma rede
networks:
  gestaoversos_network:

# Containers se comunicam por nome
db:              # host = "db"
app:             # host = "app"
redis:           # host = "redis"

# De dentro do container Flask:
DATABASE_URL = 'postgresql://user:pass@db:5432/dbname'
                                      ↑ nome do container!
```

---

## 💡 BOAS PRÁTICAS

### 1. Nunca commitar senhas
```bash
❌ DATABASE_URL=postgresql://user:senha123@...  # no código
✅ DATABASE_URL=os.getenv('DATABASE_URL')       # .env file
```

### 2. Sempre fazer backup antes de mudanças
```bash
python scripts/backup_database.py
# Agora pode fazer mudanças com segurança
```

### 3. Testar localmente antes de produção
```bash
# Dev
docker-compose -f docker-compose.dev.yml up -d
# Testa tudo
# Se OK, então:
docker-compose up -d --build  # Prod
```

### 4. Monitorar logs
```bash
docker-compose logs -f app
# Ver o que está acontecendo
```

### 5. Usar tags de versão
```bash
❌ docker pull postgres:latest      # Pode quebrar
✅ docker pull postgres:15-alpine   # Versão específica
```

---

## 🎯 PRÓXIMOS PASSOS

Agora que você entende os conceitos, pode:

1. **Experimentar localmente**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Explorar cada container**
   ```bash
   docker-compose ps                    # Ver containers
   docker-compose logs -f app           # Ver logs
   docker-compose exec app bash         # Entrar no container
   ```

3. **Fazer modificações**
   - Alterar código
   - Ver atualizar automaticamente (hot-reload)
   - Entender o fluxo

4. **Preparar produção**
   - Ler `DEPLOY.md`
   - Configurar `.env.production`
   - Fazer primeiro deploy

---

## 📚 RECURSOS PARA APRENDER MAIS

### Docker
- [Docker Docs](https://docs.docker.com/)
- [Docker Compose Docs](https://docs.docker.com/compose/)

### Nginx
- [Nginx Docs](https://nginx.org/en/docs/)
- [Nginx Beginner's Guide](https://nginx.org/en/docs/beginners_guide.html)

### PostgreSQL
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)

### Celery
- [Celery Docs](https://docs.celeryproject.org/)

---

**🎉 Parabéns! Agora você entende os conceitos fundamentais!**

**Próximo passo**: Experimentar cada tecnologia na prática! 🚀

