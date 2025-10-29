FROM nginx:1.27-alpine

# Install minimal tools required for runtime certificate generation
RUN apk add --no-cache openssl

# Copy custom entrypoint script that guarantees SSL certificates exist
COPY docker-entrypoint.d/00-generate-self-signed.sh /docker-entrypoint.d/00-generate-self-signed.sh

RUN chmod +x /docker-entrypoint.d/00-generate-self-signed.sh
