# 📍 Onde Estão Meus Dados?

**Guia Visual de Localização**

---

## 🗺️ Mapa Completo

```
SEUS DADOS ESTÃO EM 2 LUGARES:

┌─────────────────────────────────────────────────────────────┐
│                    1. WINDOWS (Direto)                       │
│              Sempre Acessível - Sem Docker                   │
└─────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┴─────────────────────────┐
    │                                                     │
    ▼                                                     ▼
📁 Uploads                                          📁 Backups
C:\GestaoVersus\app31\uploads                C:\GestaoVersus\app31\backups
    │                                                     │
    ▼                                                     ▼
📁 Logs                                            📁 PDFs Temp
C:\GestaoVersus\app31\logs                   C:\GestaoVersus\app31\temp_pdfs


┌─────────────────────────────────────────────────────────────┐
│              2. DOCKER VOLUMES (Via WSL)                     │
│         Requer Docker Desktop Rodando                        │
└─────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┴─────────────────────────┐
    │                                                     │
    ▼                                                     ▼
🐳 PostgreSQL                                      🐳 Redis
\\wsl$\docker-desktop-data\...                  \\wsl$\docker-desktop-data\...
app31_postgres_data_dev\_data                   app31_redis_data_dev\_data
```

---

## 📁 1. Arquivos no Windows (Sempre Acessíveis)

### Uploads (Arquivos dos Usuários)

**Caminho:**
```
C:\GestaoVersus\app31\uploads
```

**Como Abrir:**
1. Pressione `Windows + E` (Explorador de Arquivos)
2. Cole: `C:\GestaoVersus\app31\uploads`
3. Pressione Enter

**Ou simplesmente:**
- Navegue até a pasta do projeto: `C:\GestaoVersus\app31`
- Entre na pasta `uploads`

---

### Backups (Backups do Banco)

**Caminho:**
```
C:\GestaoVersus\app31\backups
```

**Aqui ficam salvos:**
- Backups automáticos
- Backups manuais (quando você executa `backup_docker_completo.bat`)

**Como Abrir:**
```
Windows + E → C:\GestaoVersus\app31\backups
```

---

### Logs (Logs da Aplicação)

**Caminho:**
```
C:\GestaoVersus\app31\logs
```

**Aqui ficam:**
- Logs da aplicação Flask
- Logs de erros
- Logs de acesso

---

### PDFs Temporários

**Caminho:**
```
C:\GestaoVersus\app31\temp_pdfs
```

**Aqui ficam:**
- PDFs gerados temporariamente
- Relatórios em PDF

---

## 🐳 2. Volumes Docker (Via WSL)

### PostgreSQL (Banco de Dados Principal)

**Caminho WSL:**
```
\\wsl$\docker-desktop-data\data\docker\volumes\app31_postgres_data_dev\_data
```

**Como Abrir:**

**Método 1 - Via Explorador:**
1. Abra o Explorador de Arquivos (`Windows + E`)
2. Cole na barra de endereço:
   ```
   \\wsl$\docker-desktop-data\data\docker\volumes\app31_postgres_data_dev\_data
   ```
3. Pressione Enter

**Método 2 - Via Executar:**
1. Pressione `Windows + R`
2. Cole:
   ```
   \\wsl$\docker-desktop-data\data\docker\volumes\app31_postgres_data_dev\_data
   ```
3. Pressione Enter

**⚠️ IMPORTANTE:**
- Este caminho **SÓ FUNCIONA** quando Docker Desktop está rodando!
- Você verá pastas como: `base/`, `global/`, `pg_wal/`, etc.
- **NÃO modifique** estes arquivos diretamente!

---

### Redis (Cache e Filas)

**Caminho WSL:**
```
\\wsl$\docker-desktop-data\data\docker\volumes\app31_redis_data_dev\_data
```

**Como Abrir:**
Mesmo método do PostgreSQL, só mudar o caminho.

---

## 🚀 Atalho Rápido

**Execute este script:**
```batch
abrir_localizacao_dados.bat
```

Este script abre automaticamente todas as localizações para você!

---

## 🔍 Como Verificar se Docker Está Rodando

**Antes de tentar acessar os volumes Docker:**

### Método 1 - Via Ícone
- Veja se o ícone da baleia do Docker está na bandeja do sistema
- Se estiver verde/azul = rodando ✅
- Se estiver cinza/vermelho = parado ❌

### Método 2 - Via Comando
```cmd
docker ps
```

Se mostrar lista de containers = rodando ✅  
Se der erro = parado ❌

---

## 📊 Tabela de Referência Rápida

| Dados | Caminho | Requer Docker? |
|-------|---------|----------------|
| **Uploads** | `C:\GestaoVersus\app31\uploads` | ❌ NÃO |
| **Backups** | `C:\GestaoVersus\app31\backups` | ❌ NÃO |
| **Logs** | `C:\GestaoVersus\app31\logs` | ❌ NÃO |
| **PDFs Temp** | `C:\GestaoVersus\app31\temp_pdfs` | ❌ NÃO |
| **PostgreSQL** | `\\wsl$\docker-desktop-data\...` | ✅ SIM |
| **Redis** | `\\wsl$\docker-desktop-data\...` | ✅ SIM |

---

## 🎯 Cenários Comuns

### Quero ver meus backups
```
C:\GestaoVersus\app31\backups
```
✅ Sempre acessível

---

### Quero ver arquivos enviados por usuários
```
C:\GestaoVersus\app31\uploads
```
✅ Sempre acessível

---

### Quero ver os dados do banco PostgreSQL
```
\\wsl$\docker-desktop-data\data\docker\volumes\app31_postgres_data_dev\_data
```
⚠️ Precisa Docker rodando  
⚠️ NÃO modifique diretamente!

**Melhor forma:** Use backup!
```batch
backup_docker_completo.bat
```

---

### Quero copiar tudo para backup

**Arquivos Windows (fácil):**
```
Copiar toda a pasta: C:\GestaoVersus\app31
```

**Banco PostgreSQL (use script):**
```batch
backup_docker_completo.bat
```

---

## ⚠️ Avisos Importantes

### ❌ NÃO FAÇA:

1. **Não modifique arquivos do volume Docker diretamente**
   - Pode corromper o banco
   - Pode causar perda de dados
   - Docker pode não reconhecer as mudanças

2. **Não copie arquivos para dentro do volume Docker manualmente**
   - Use ferramentas do PostgreSQL
   - Use backups/restore

3. **Não delete o volume Docker sem backup**
   - Perda permanente de dados
   - Sem recuperação possível

---

### ✅ FAÇA:

1. **Para backup:**
   ```batch
   backup_docker_completo.bat
   ```

2. **Para restore:**
   ```batch
   restore_docker_backup.bat arquivo.zip
   ```

3. **Para ver dados:**
   - Use Adminer: http://localhost:8080
   - Use comandos Docker: `docker exec ...`
   - Use ferramentas PostgreSQL

---

## 🛠️ Ferramentas Úteis

### Explorador de Arquivos - Favoritos

Adicione aos Favoritos do Windows:

1. `C:\GestaoVersus\app31\backups`
2. `C:\GestaoVersus\app31\uploads`
3. `\\wsl$\docker-desktop-data\data\docker\volumes` (raiz)

**Como adicionar:**
1. Navegue até a pasta
2. Arraste para "Acesso rápido" na barra lateral

---

### Adminer (Interface Web)

**Para ver dados do PostgreSQL via navegador:**

1. Inicie o Docker:
   ```batch
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. Acesse: http://localhost:8080

3. Login:
   - Sistema: PostgreSQL
   - Servidor: db_dev
   - Usuário: postgres
   - Senha: dev_password
   - Base: bd_app_versus_dev

---

## 📞 Comandos Úteis

### Ver Volumes Docker
```bash
docker volume ls --filter "name=app31"
```

### Ver Tamanho dos Volumes
```bash
docker system df -v | findstr "app31"
```

### Inspecionar Volume
```bash
docker volume inspect app31_postgres_data_dev
```

### Abrir WSL no Terminal
```bash
wsl
cd /var/lib/docker/volumes/app31_postgres_data_dev/_data
ls -lah
```

---

## 🎓 Resumo Visual

```
┌──────────────────────────────────────────────────────────┐
│                  SEUS DADOS ESTÃO EM:                     │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  📂 WINDOWS (Sempre Acessível)                            │
│  ├─ C:\GestaoVersus\app31\uploads                        │
│  ├─ C:\GestaoVersus\app31\backups                        │
│  ├─ C:\GestaoVersus\app31\logs                           │
│  └─ C:\GestaoVersus\app31\temp_pdfs                      │
│                                                            │
│  🐳 DOCKER (Requer Docker Rodando)                        │
│  ├─ \\wsl$\...\app31_postgres_data_dev\_data            │
│  └─ \\wsl$\...\app31_redis_data_dev\_data               │
│                                                            │
│  🚀 ATALHO:                                               │
│  └─ abrir_localizacao_dados.bat                          │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

---

## ✅ Checklist

- [ ] Executei `abrir_localizacao_dados.bat`
- [ ] Consegui acessar pastas do Windows
- [ ] Docker Desktop está rodando
- [ ] Consegui acessar volumes Docker via `\\wsl$\`
- [ ] Adicionei pastas importantes aos Favoritos
- [ ] Fiz backup: `backup_docker_completo.bat`

---

**Criado por:** Cursor AI  
**Data:** 28/10/2025  
**Status:** ✅ Guia Completo de Localização


