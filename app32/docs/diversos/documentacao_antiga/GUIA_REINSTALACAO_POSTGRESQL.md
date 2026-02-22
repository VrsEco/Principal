# 🔄 Guia de Reinstalação do PostgreSQL

## 📋 Problema Identificado

O PostgreSQL atual tem problemas de encoding que impedem a migração. Vamos reinstalar corretamente.

## 🚀 Solução: Reinstalação Completa

### Passo 1: Executar como Administrador

1. **Clique com botão direito** em `reinstall_postgresql.bat`
2. Selecione **"Executar como administrador"**
3. Aguarde a conclusão do processo

### Passo 2: O que o Script Faz

1. ✅ **Para serviços** PostgreSQL existentes
2. ✅ **Remove serviços** do Windows
3. ✅ **Desinstala** PostgreSQL 16 e 17
4. ✅ **Remove diretórios** restantes
5. ✅ **Baixa** PostgreSQL 16.3
6. ✅ **Instala** com configurações corretas
7. ✅ **Configura** usuário e senha
8. ✅ **Cria** banco `bd_app_versus`
9. ✅ **Testa** conexão

### Passo 3: Configurações da Nova Instalação

- **Usuário**: `postgres`
- **Senha**: `postgres123`
- **Porta**: `5432`
- **Encoding**: `UTF8`
- **Banco**: `bd_app_versus`

### Passo 4: Executar Migração

Após a reinstalação, execute:

```bash
python migrate_final_correct.py
```

## 🔧 Configuração Manual (Alternativa)

Se o script automático não funcionar:

### 1. Desinstalar Manualmente
```bash
# Parar serviços
sc stop postgresql-x64-16
sc stop postgresql-x64-17

# Remover serviços
sc delete postgresql-x64-16
sc delete postgresql-x64-17

# Desinstalar via Painel de Controle
```

### 2. Baixar PostgreSQL
- URL: https://www.postgresql.org/download/windows/
- Versão: PostgreSQL 16.3
- Arquitetura: x64

### 3. Instalar com Configurações
- **Usuário**: postgres
- **Senha**: postgres123
- **Porta**: 5432
- **Encoding**: UTF8
- **Locale**: C

### 4. Configurar Banco
```bash
# Conectar
psql -U postgres

# Criar banco
CREATE DATABASE bd_app_versus;

# Sair
\q
```

## 📊 Verificação

Após a reinstalação, teste:

```bash
# Testar conexão
psql -U postgres -d bd_app_versus -c "SELECT version();"

# Verificar encoding
psql -U postgres -d bd_app_versus -c "SHOW client_encoding;"
```

## 🎯 Próximos Passos

1. ✅ **Reinstalar** PostgreSQL
2. ✅ **Executar** migração
3. ✅ **Configurar** .env
4. ✅ **Testar** aplicação

## 🐛 Solução de Problemas

### Erro: "Acesso negado"
- Execute como **administrador**

### Erro: "Download falhou"
- Baixe manualmente de: https://www.postgresql.org/download/windows/

### Erro: "Instalação falhou"
- Verifique se não há outros bancos rodando
- Reinicie o computador e tente novamente

### Erro: "Conexão falhou"
- Verifique se o serviço está rodando
- Teste com: `services.msc` → PostgreSQL

---

**Status**: 🔄 Aguardando reinstalação  
**Próximo**: Execute `reinstall_postgresql.bat` como administrador
