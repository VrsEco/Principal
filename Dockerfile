# ============================================
# GestaoVersus - Dockerfile Produção
# ============================================
# Imagem otimizada para Python 3.9 Flask App
# Multi-stage build para reduzir tamanho final
# ============================================

FROM python:3.9-slim as builder

# Metadata
LABEL maintainer="GestaoVersus Team"
LABEL version="1.0"
LABEL description="GestaoVersus - Sistema de Gestão Empresarial"

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar apenas requirements primeiro (cache de layers)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.9-slim

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app_pev.py \
    FLASK_ENV=production

# Instalar apenas dependências runtime necessárias + Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    postgresql-client \
    curl \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/uploads /app/temp_pdfs /app/logs /app/backups && \
    chown -R appuser:appuser /app

# Definir diretório de trabalho
WORKDIR /app

# Copiar dependências instaladas do builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Instalar browsers do Playwright (antes de mudar para appuser)
RUN playwright install --with-deps chromium

# Copiar código da aplicação
COPY --chown=appuser:appuser . .

# Mudar para usuário não-root
USER appuser

# Expor porta
EXPOSE 5002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# Comando de inicialização
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app_pev:app"]
