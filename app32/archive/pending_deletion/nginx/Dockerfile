# ============================================
# GestaoVersus - Frontend Dockerfile (Nginx)
# ============================================
# Imagem Nginx para servir arquivos estáticos
# e fazer reverse proxy para o backend Flask
# ============================================

FROM nginx:1.27-alpine

# Metadata
LABEL maintainer="GestaoVersus Team"
LABEL version="1.0"
LABEL description="GestaoVersus - Frontend Nginx"

# Install minimal tools required for runtime certificate generation
RUN apk add --no-cache openssl curl

# Criar diretórios necessários
RUN mkdir -p /app/static /app/uploads /app/temp_pdfs /var/www/certbot

# Copy custom entrypoint script that guarantees SSL certificates exist
COPY docker-entrypoint.d/00-generate-self-signed.sh /docker-entrypoint.d/00-generate-self-signed.sh
RUN chmod +x /docker-entrypoint.d/00-generate-self-signed.sh

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Static files são montados via volume no docker-compose.yml
# Não é necessário copiar durante o build, pois são montados em runtime
# O diretório /app/static será preenchido pelo volume mount

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expor portas
EXPOSE 80 443
