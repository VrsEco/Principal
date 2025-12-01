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

# Instalar dependências do sistema (incluindo para compilar pycairo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar apenas requirements primeiro (cache de layers)
COPY requirements.txt .
COPY requirements_relatorios.txt .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements_relatorios.txt

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.9-slim

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app_pev.py \
    FLASK_ENV=production

# Instalar dependências runtime e build necessárias para xhtml2pdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    postgresql-client \
    curl \
    # Dependências para compilar pycairo (necessário para xhtml2pdf)
    gcc \
    g++ \
    pkg-config \
    libcairo2-dev \
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
