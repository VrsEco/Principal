# Sistema de Backup Automático - GestaoVersus

## 📋 Visão Geral

Sistema completo de backup automático que protege:
- ✅ Banco de dados PostgreSQL
- ✅ Código da aplicação
- ✅ Arquivos de upload (imagens, PDFs, documentos)

**Destino:** OneDrive (sincronização automática para nuvem)  
**Frequência:** Diário  
**Horários:**
- 18:10 - Servidor Configr gera backup do banco de dados
- 18:30 - PC local baixa tudo para OneDrive
**Retenção:** Mantém os 3 backups mais recentes de cada tipo

---

## 🚀 Configuração Inicial (Executar UMA VEZ)

1. **Clique com botão direito** no arquivo:
   ```
   CONFIGURAR_BACKUP_AUTOMATICO.bat
   ```

2. Escolha: **"Executar como administrador"**

3. Aguarde a mensagem de sucesso

✅ Pronto! O backup será executado automaticamente todos os dias às 18h.

---

## 🔧 Uso Manual

Se quiser fazer um backup imediato (fora do horário agendado):

1. Clique duas vezes em:
   ```
   BAIXAR_BACKUPS_CONFIGR.bat
   ```

2. Aguarde a sincronização (pode levar alguns minutos)

---

## 📁 Localização dos Backups

Todos os backups são salvos em:
```
C:\Users\mff20\OneDrive\Versus\Versus Participações\Versus ERP\Backup_app\
```

Estrutura de pastas:
```
Backup_app/
├── database/          # Backups do banco (.sql.gz)
├── code/              # Snapshots do código (.tar.gz)
└── uploads/           # Arquivos enviados pelos usuários
```

---

## 🗑️ Limpeza Automática

O sistema mantém automaticamente apenas os **3 backups mais recentes** de cada tipo:
- Database: últimos 3 arquivos `.sql.gz`
- Code: últimos 3 snapshots `.tar.gz`
- Uploads: sincronização completa (sem limpeza)

Backups mais antigos são removidos automaticamente.

---

## ⚙️ Gerenciamento da Tarefa Agendada

### Verificar se está ativa:
1. Abra o **Agendador de Tarefas** do Windows
2. Procure por: `GestaoVersus_Backup_Diario`
3. Verifique o status e próxima execução

### Desativar temporariamente:
No Agendador de Tarefas, clique com botão direito na tarefa → **Desabilitar**

### Remover completamente:
Execute no PowerShell (como Administrador):
```powershell
schtasks /Delete /TN "GestaoVersus_Backup_Diario" /F
```

---

## 🔄 Restauração de Backup

### Restaurar Banco de Dados:
1. Localize o arquivo `.sql.gz` mais recente em `Backup_app/database/`
2. Descompacte o arquivo (clique direito → Extrair)
3. Use o pgAdmin ou execute:
   ```bash
   psql -U postgres -d bd_app_versus < backup_file.sql
   ```

### Restaurar Código:
1. Localize o snapshot `.tar.gz` mais recente em `Backup_app/code/`
2. Extraia o arquivo para uma pasta temporária
3. Compare/copie os arquivos necessários

### Restaurar Uploads:
Os arquivos já estão prontos para uso em `Backup_app/uploads/`

---

## 🛡️ Estratégia de Proteção Completa

| Local | Conteúdo | Atualização | Proteção Contra |
|-------|----------|-------------|-----------------|
| **Servidor Configr** | Aplicação ativa | Tempo real | - |
| **GitHub** | Código versionado | A cada push | Perda de código |
| **PC + OneDrive** | Backup completo | Diário às 18h | Ataque ao servidor, falha de hardware |

---

## ⚠️ Troubleshooting

### Backup não está executando:
1. Verifique se o PC está ligado às 18h
2. Verifique conexão com internet
3. Abra o Agendador de Tarefas e veja o histórico de execuções

### Erro de conexão SSH:
1. Verifique se o servidor Configr está online
2. Teste manualmente executando `BAIXAR_BACKUPS_CONFIGR.bat`

### OneDrive não está sincronizando:
1. Verifique se o OneDrive está em execução
2. Verifique espaço disponível na conta
3. Verifique se a pasta está marcada para sincronização

---

## 📞 Suporte

Em caso de problemas, verifique:
- Logs do Agendador de Tarefas do Windows
- Status do OneDrive
- Conectividade com o servidor Configr

---

**Última atualização:** 31/12/2025  
**Versão:** 1.0
