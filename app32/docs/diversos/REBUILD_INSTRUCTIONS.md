# Instruções para Rebuild do Container após Correção Playwright

## Problema Resolvido
O erro `BrowserType.launch: Executable doesn't exist` ocorria porque o Playwright estava instalado mas os browsers não foram baixados.

## Correção Aplicada
O `Dockerfile` foi atualizado para:
1. Instalar dependências do sistema necessárias para Playwright/Chromium
2. Executar `playwright install --with-deps chromium` durante o build

## Como Aplicar a Correção

### Opção 1: Rebuild Completo (Recomendado)
```bash
# Parar todos os containers
docker-compose down

# Rebuild da imagem sem cache
docker-compose build --no-cache app

# Subir os serviços
docker-compose up -d
```

### Opção 2: Rebuild Apenas da App
```bash
# Rebuild apenas do serviço app
docker-compose build --no-cache app

# Restart do serviço
docker-compose up -d --force-recreate app
```

### Opção 3: Rebuild e Restart de Todos os Serviços
```bash
# Rebuild de todos os serviços que dependem do Dockerfile
docker-compose build --no-cache

# Restart completo
docker-compose down
docker-compose up -d
```

## Verificação

Após o rebuild, você pode verificar se o Playwright está funcionando:

```bash
# Acessar o container
docker exec -it gestaoversos_app_prod bash

# Verificar se o chromium foi instalado
playwright --version

# Listar browsers instalados
ls -la /root/.cache/ms-playwright/
```

## Teste da Funcionalidade

Acesse a rota de geração de PDF do mapa de processos:
```
http://localhost:5002/company/{company_id}/process/map-pdf2
```

Se tudo estiver correto, o PDF será gerado sem erros.

## Notas Importantes

- O Celery Worker e Celery Beat também usam o mesmo Dockerfile, então eles também serão atualizados
- O rebuild pode demorar alguns minutos devido ao download do Chromium (~200MB)
- O tamanho final da imagem aumentará em aproximadamente 300-400MB

## Logs para Debug

Se o erro persistir, verifique os logs:

```bash
# Logs do container principal
docker-compose logs -f app

# Logs do Celery Worker (se a geração de PDF for em background)
docker-compose logs -f celery_worker
```

## Dependências Adicionadas ao Dockerfile

Bibliotecas do sistema para Chromium:
- libnss3, libnspr4 (Network Security Services)
- libatk1.0-0, libatk-bridge2.0-0 (Accessibility Toolkit)
- libcups2 (Printing support)
- libdrm2 (Direct Rendering Manager)
- libdbus-1-3 (Message bus system)
- libxkbcommon0 (Keyboard handling)
- libxcomposite1, libxdamage1, libxfixes3, libxrandr2 (X11 extensions)
- libgbm1 (Graphics Buffer Manager)
- libpango-1.0-0, libcairo2 (Text rendering)
- libasound2 (Audio support)
- libatspi2.0-0 (Assistive Technology)

---

**Data da Correção:** 21/10/2025  
**Versão do Playwright:** 1.55.0  
**Browser Instalado:** Chromium headless shell




