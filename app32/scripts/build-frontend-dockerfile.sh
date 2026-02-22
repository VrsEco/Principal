#!/bin/bash

# ============================================
# Script auxiliar para build do frontend
# ============================================
# Este script constrói o frontend copiando
# os arquivos estáticos para o contexto do build
# ============================================

set -e

# Diretório temporário para o build
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "🔨 Preparando contexto de build do frontend..."

# Copiar Dockerfile do nginx
cp nginx/Dockerfile $TEMP_DIR/Dockerfile

# Copiar configurações do nginx
mkdir -p $TEMP_DIR/conf.d
cp nginx/conf.d/*.conf $TEMP_DIR/conf.d/
cp nginx/nginx.conf $TEMP_DIR/nginx.conf

# Copiar entrypoint script
mkdir -p $TEMP_DIR/docker-entrypoint.d
cp nginx/docker-entrypoint.d/*.sh $TEMP_DIR/docker-entrypoint.d/

# Copiar arquivos estáticos
cp -r static $TEMP_DIR/static

# Ajustar caminhos no Dockerfile temporário
sed -i 's|COPY conf.d/|COPY ./conf.d/|g' $TEMP_DIR/Dockerfile
sed -i 's|COPY nginx.conf|COPY ./nginx.conf|g' $TEMP_DIR/Dockerfile
sed -i 's|COPY docker-entrypoint.d/|COPY ./docker-entrypoint.d/|g' $TEMP_DIR/Dockerfile
sed -i 's|ARG STATIC_DIR=../static|ARG STATIC_DIR=./static|g' $TEMP_DIR/Dockerfile

echo "✅ Contexto preparado em $TEMP_DIR"
echo "Execute: docker build -t <tag> -f $TEMP_DIR/Dockerfile $TEMP_DIR"







