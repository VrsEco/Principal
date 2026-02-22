#!/bin/bash
# Script de Início Rápido - GestaoVersus (APP30)
# Facilita o deploy em diferentes ambientes

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║     GestaoVersus (APP30) - Deploy Manager        ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Menu
echo ""
echo "Escolha o ambiente:"
echo ""
echo "1. 🔧 Desenvolvimento (Local)"
echo "2. 🚀 Produção (Docker Compose)"
echo "3. ☁️  Google Cloud Platform"
echo "4. 💾 Backup Database"
echo "5. 🔄 Restaurar Backup"
echo "6. 🏥 Health Check"
echo "0. ❌ Sair"
echo ""

read -p "Opção: " choice

case $choice in
    1)
        echo -e "\n${BLUE}🔧 Iniciando ambiente de desenvolvimento...${NC}\n"
        
        # Verificar se .env.development existe
        if [ ! -f .env.development ]; then
            echo -e "${YELLOW}⚠️  Arquivo .env.development não encontrado. Criando...${NC}"
            cp .env.example .env.development
            echo -e "${YELLOW}⚠️  Configure .env.development antes de continuar!${NC}"
            exit 1
        fi
        
        # Iniciar containers
        docker-compose -f docker-compose.dev.yml up -d
        
        echo -e "\n${GREEN}✅ Ambiente de desenvolvimento iniciado!${NC}"
        echo -e "📱 Acesse: http://localhost:5002"
        echo -e "🗄️  Adminer: http://localhost:8080"
        echo ""
        echo "Para ver logs: docker-compose -f docker-compose.dev.yml logs -f"
        ;;
    
    2)
        echo -e "\n${BLUE}🚀 Iniciando ambiente de produção...${NC}\n"
        
        # Verificar se .env.production existe
        if [ ! -f .env.production ]; then
            echo -e "${RED}❌ Arquivo .env.production não encontrado!${NC}"
            echo -e "${YELLOW}Execute: cp .env.example .env.production${NC}"
            echo -e "${YELLOW}E configure todas as variáveis!${NC}"
            exit 1
        fi
        
        # Confirmar
        read -p "⚠️  Isso vai iniciar a aplicação em modo PRODUÇÃO. Continuar? (S/N): " confirm
        if [ "$confirm" != "S" ] && [ "$confirm" != "s" ]; then
            echo -e "${RED}❌ Cancelado.${NC}"
            exit 0
        fi
        
        # Build e start
        docker-compose up -d --build
        
        echo -e "\n${GREEN}✅ Ambiente de produção iniciado!${NC}"
        echo -e "📱 Acesse: https://congigr.com (ou seu domínio)"
        echo ""
        echo "Para ver logs: docker-compose logs -f"
        ;;
    
    3)
        echo -e "\n${BLUE}☁️  Deploy no Google Cloud Platform...${NC}\n"
        
        # Verificar se gcloud está instalado
        if ! command -v gcloud &> /dev/null; then
            echo -e "${RED}❌ gcloud CLI não está instalado!${NC}"
            echo -e "Instale em: https://cloud.google.com/sdk/docs/install"
            exit 1
        fi
        
        # Executar setup
        chmod +x scripts/setup_gcp.sh
        ./scripts/setup_gcp.sh
        ;;
    
    4)
        echo -e "\n${BLUE}💾 Fazendo backup do database...${NC}\n"
        
        if [ -f scripts/backup_database.py ]; then
            python3 scripts/backup_database.py
        else
            echo -e "${RED}❌ Script de backup não encontrado!${NC}"
            exit 1
        fi
        ;;
    
    5)
        echo -e "\n${BLUE}🔄 Restaurando backup...${NC}\n"
        
        if [ -f scripts/restore_database.py ]; then
            python3 scripts/restore_database.py
        else
            echo -e "${RED}❌ Script de restauração não encontrado!${NC}"
            exit 1
        fi
        ;;
    
    6)
        echo -e "\n${BLUE}🏥 Verificando saúde da aplicação...${NC}\n"
        
        read -p "URL da aplicação (padrão: http://localhost:5002): " url
        url=${url:-http://localhost:5002}
        
        if [ -f scripts/health_check.py ]; then
            python3 scripts/health_check.py --url "$url"
        else
            # Health check simples com curl
            echo "Verificando $url/health..."
            curl -f "$url/health" && echo -e "\n${GREEN}✅ Aplicação OK${NC}" || echo -e "\n${RED}❌ Aplicação com problemas${NC}"
        fi
        ;;
    
    0)
        echo -e "${BLUE}👋 Até logo!${NC}"
        exit 0
        ;;
    
    *)
        echo -e "${RED}❌ Opção inválida!${NC}"
        exit 1
        ;;
esac

echo ""


