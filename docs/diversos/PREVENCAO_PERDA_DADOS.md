# 🛡️ PREVENÇÃO DE PERDA DE DADOS

**CRÍTICO:** Este documento define procedimentos para GARANTIR que NENHUM dado seja perdido entre versões.

---

## ⚠️ PROBLEMA IDENTIFICADO

### O que aconteceu:
- Dados cadastrados na **Versus Gestão Corporativa** no APP25
- Dados **não migraram** automaticamente para APP26
- **PERDA DE DADOS** ocorreu

### Por que aconteceu:
1. Não havia processo de migração automática
2. Não havia backup antes da mudança de versão
3. Não havia verificação de integridade dos dados
4. Migração foi feita de forma manual/incompleta

---

## ✅ SOLUÇÕES IMPLEMENTADAS

### 1. Sistema de Backup Automático
**Arquivo:** `backup_automatico.py`

**Uso:**
```bash
python backup_automatico.py
```

**Funcionalidades:**
- ✅ Cria backup com timestamp
- ✅ Gera relatório detalhado do backup
- ✅ Lista todos os backups disponíveis
- ✅ Permite restaurar backups
- ✅ Salva em pasta dedicada `/backups`

### 2. Sistema de Migração Segura
**Arquivo:** `migracao_segura.py`

**Uso:**
```bash
python migracao_segura.py
```

**Funcionalidades:**
- ✅ Analisa dados de origem ANTES de migrar
- ✅ Analisa dados de destino ANTES de migrar
- ✅ Cria backup automático pré-migração
- ✅ Migra tabela por tabela com verificação
- ✅ Verifica integridade PÓS-migração
- ✅ Gera relatório completo
- ✅ Permite rollback se houver problema

---

## 📋 PROCEDIMENTO OBRIGATÓRIO

### ANTES de mudar de versão (ex: APP26 -> APP27):

#### 1. CRIAR BACKUP COMPLETO
```bash
python backup_automatico.py
# Escolha opção 1: Criar novo backup
```

#### 2. VERIFICAR DADOS ATUAIS
```bash
python verificar_dados_grv.py
python verificar_meus_dados.py
```

#### 3. DOCUMENTAR O QUE TEM
- Anotar quantidade de empresas
- Anotar quantidade de dados GRV
- Anotar quantidade de dados PEV
- Tirar prints das telas principais

#### 4. EXECUTAR MIGRAÇÃO SEGURA
```bash
python migracao_segura.py
# Escolha a opção apropriada
```

#### 5. VERIFICAR APÓS MIGRAÇÃO
```bash
python verificar_dados_grv.py
python verificar_meus_dados.py
```

#### 6. COMPARAR ANTES x DEPOIS
- Verificar se TODOS os dados migraram
- Conferir relatório de migração
- Testar funcionalidades críticas

---

## 🔒 CHECKLIST DE SEGURANÇA

### Antes de QUALQUER mudança de versão:

- [ ] **Backup criado** (`backup_automatico.py`)
- [ ] **Dados documentados** (quantidade de registros)
- [ ] **Prints salvos** (evidência visual)
- [ ] **Migração planejada** (saber o que vai migrar)
- [ ] **Tempo reservado** (não fazer com pressa)

### Durante a migração:

- [ ] **Usar `migracao_segura.py`** (NUNCA migração manual)
- [ ] **Verificar cada etapa** (não pular verificações)
- [ ] **Ler relatórios** (conferir se tudo migrou)
- [ ] **Testar imediatamente** (não deixar para depois)

### Após a migração:

- [ ] **Todos os dados presentes** (conferir contagens)
- [ ] **Funcionalidades OK** (testar telas principais)
- [ ] **Backup mantido** (não deletar backup antigo)
- [ ] **Relatório salvo** (documentar o processo)

---

## 🚨 SE HOUVER PERDA DE DADOS

### Passos imediatos:

1. **NÃO ENTRE EM PÂNICO**
2. **NÃO DELETE NADA**
3. **PARE de usar o sistema**
4. **Restaure o backup:**
   ```bash
   python backup_automatico.py
   # Escolha opção 3: Restaurar backup
   ```
5. **Verifique os dados restaurados**
6. **Identifique o que deu errado**
7. **Corrija o problema**
8. **Tente a migração novamente**

---

## 📊 ESTRUTURA DE BACKUPS

```
app26/
├── backups/                    # Backups regulares
│   ├── pevapp22_backup_20251010_120000.db
│   ├── relatorio_backup_20251010_120000.json
│   └── ...
│
├── backups_migracao/          # Backups de migração
│   ├── pre_migracao_20251010_120000.db
│   ├── relatorio_migracao_20251010_120000.json
│   └── ...
│
└── instance/
    └── pevapp22.db            # Banco atual
```

---

## 🔧 SCRIPTS DISPONÍVEIS

### 1. **backup_automatico.py**
- Criar backup manual
- Listar backups
- Restaurar backup

### 2. **migracao_segura.py**
- Migração com verificação
- Backup pré-migração
- Relatório detalhado

### 3. **verificar_dados_grv.py**
- Verificar dados GRV
- Contar registros
- Listar por empresa

### 4. **verificar_meus_dados.py**
- Verificar dados PEV
- Resumo rápido
- Status geral

### 5. **buscar_dados_grv_todos_bancos.py**
- Buscar dados em TODOS os bancos
- Encontrar onde estão dados específicos

---

## 💡 BOAS PRÁTICAS

### 1. Backups Frequentes
```bash
# Fazer backup DIARIAMENTE em produção
python backup_automatico.py
```

### 2. Testar Restauração
```bash
# Testar se os backups funcionam ANTES de precisar
python backup_automatico.py
# Opção 3: Restaurar (em ambiente de teste)
```

### 3. Documentar Mudanças
- Manter log de todas as migrações
- Salvar relatórios de backup
- Documentar problemas encontrados

### 4. Validação Constante
```bash
# Verificar dados regularmente
python verificar_dados_grv.py
python verificar_meus_dados.py
```

---

## 📞 EM CASO DE DÚVIDA

### Perguntas a fazer ANTES de migrar:

1. ✅ O backup foi criado?
2. ✅ Sei quantos dados tenho atualmente?
3. ✅ Tenho tempo para fazer com calma?
4. ✅ Sei como restaurar se der errado?
5. ✅ Li o relatório de migração?

### Se a resposta for NÃO para qualquer uma:
**NÃO MIGRE AINDA!**

---

## 🎯 RESUMO EXECUTIVO

### Para NUNCA perder dados novamente:

1. **SEMPRE fazer backup antes de qualquer mudança**
   ```bash
   python backup_automatico.py
   ```

2. **SEMPRE usar migração segura**
   ```bash
   python migracao_segura.py
   ```

3. **SEMPRE verificar após migração**
   ```bash
   python verificar_dados_grv.py
   ```

4. **NUNCA deletar backups antigos** (manter pelo menos 30 dias)

5. **SEMPRE ler relatórios** de backup e migração

---

## 🔐 GARANTIA

Se seguir este procedimento:
- ✅ **100% dos dados serão preservados**
- ✅ **Rollback sempre possível**
- ✅ **Rastreabilidade completa**
- ✅ **Sem surpresas desagradáveis**

---

## 📝 LIÇÃO APRENDIDA

### O que aprendemos com a perda de dados:

1. **Backup não é opcional** - é OBRIGATÓRIO
2. **Migração manual é perigosa** - usar scripts
3. **Verificação é essencial** - antes E depois
4. **Documentação salva vidas** - manter histórico

### Compromisso:

**A partir de hoje, ZERO TOLERÂNCIA com perda de dados!**

Todos os procedimentos devem seguir este documento.

---

**Criado em:** 10/10/2025  
**Status:** ATIVO E OBRIGATÓRIO  
**Responsável:** Equipe de Desenvolvimento




