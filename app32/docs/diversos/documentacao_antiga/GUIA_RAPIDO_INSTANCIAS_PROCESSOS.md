# Guia Rápido - Instâncias de Processos

## 🎯 O que são Instâncias de Processos?

**Processo** = Modelo/Template (Ex: "Calcular Impostos Mensais")  
**Instância** = Execução específica (Ex: "Calcular Impostos - Janeiro/2025")

## 📍 Como Acessar

**GRV** → **Gestão de Processos** → **Instâncias de Processos**

URL: `http://127.0.0.1:5002/grv/company/{company_id}/process/instances`

---

## 🚀 Disparar um Processo (Criar Instância)

### Passo a Passo:

1. **Clique em**: ⚡ **"Disparar Processo"**

2. **Preencha o formulário**:
   - **Processo**: Selecione (Ex: `AB.C.1.1.2 - Identidade Organizacional`)
   - **Título**: Nome da execução (Ex: "Identidade Organizacional - Janeiro/2025")
   - **Vencimento**: Data/hora limite (padrão: amanhã 17h)
   - **Prioridade**: Baixa / Normal / Alta / Urgente
   - **Descrição**: Observações (opcional)

3. **Sistema busca automaticamente**:
   - ✅ Colaboradores da rotina associada
   - ✅ Horas estimadas de cada um

4. **Clique em**: **"Disparar"**

### Resultado:
- ✅ Código único gerado: `AB.P18.001`
- ✅ Status: **Pendente**
- ✅ Colaboradores atribuídos
- ✅ Card aparece na lista

---

## 📋 Gerenciar uma Instância

### Passo a Passo:

1. **Na lista de instâncias**, clique no botão:
   - **"Iniciar"** (se pendente)
   - **"Gerenciar"** (se em andamento)
   - **"Ver Detalhes"** (se concluída)

2. **Página de Gerenciamento abre** com:

### 📊 Seção: Informações Gerais
- **Status atual**: Badge colorido
- **Prioridade**: Badge colorido
- **Vencimento**: Data/hora
- **Horas Estimadas**: Total previsto
- **Horas Realizadas**: Total executado (atualiza automaticamente)
- **Concluído em**: Data/hora (se concluído)

### 👥 Seção: Colaboradores e Horas

**Para cada colaborador**:
- **Nome**: Ex: "João Silva"
- **Previsto**: Ex: "2.5h"
- **Realizado**: Campo editável com botão "Salvar"

**Como registrar horas**:
1. Digite as horas realizadas no campo
2. Clique em **"Salvar"**
3. ✅ Sistema registra automaticamente no log
4. ✅ Total de horas realizadas atualiza

### 📝 Seção: Registro Diário

Similar às atividades de projetos:

**Adicionar registro**:
1. Digite a observação no campo de texto
2. Clique em **"Adicionar Registro"**
3. ✅ Sistema grava com data/hora automática
4. ✅ Registro aparece na lista abaixo

**Visualizar registros**:
- Ordenados do mais recente para o mais antigo
- Mostra: Autor, Data/hora, Conteúdo
- Registros de sistema (horas, conclusão) aparecem automaticamente

---

## ✅ Concluir uma Instância

### Passo a Passo:

1. **Na página de gerenciamento**, clique em: **"✓ Concluir"**

2. **Pop-up de confirmação abre** com:
   - **Data de Conclusão**: Pré-preenchida com data/hora atual (editável)
   - **Observações finais**: Campo opcional

3. **Clique em**: **"Confirmar Conclusão"**

### O que acontece:
- ✅ Status muda para **"Concluído"**
- ✅ Data de conclusão registrada
- ✅ Log automático: "Instância concluída. [Observações...]"
- ✅ Campos de horas ficam bloqueados (read-only)
- ✅ Botão "Concluir" desaparece
- ✅ Retorna para lista de instâncias

---

## 🎨 Indicadores Visuais

### Status:
- **Pendente**: Cinza
- **Em Andamento**: Azul
- **Aguardando**: Amarelo
- **Concluído**: Verde
- **Cancelado**: Vermelho

### Prioridade:
- **Baixa**: Cinza
- **Normal**: Azul
- **Alta**: Laranja
- **Urgente**: Vermelho

### Tipo de Disparo:
- 🤖 **Automático**: Disparado pelo sistema
- 👤 **Manual**: Disparado por usuário

---

## 🔄 Fluxo Completo de Uso

```
1. Disparar Processo
   ↓
2. Instância criada (Status: Pendente)
   ↓
3. Clicar em "Iniciar" → Gerenciar
   ↓
4. Registrar horas realizadas dos colaboradores
   ↓
5. Adicionar registros diários do andamento
   ↓
6. Clicar em "Concluir"
   ↓
7. Confirmar data de conclusão
   ↓
8. Instância concluída (Status: Concluído)
```

---

## 📝 Códigos Gerados

### Formato: `{CÓDIGO_EMPRESA}.P{ID_PROCESSO}.{SEQUENCIAL}`

**Exemplos**:
- Primeira instância do processo 18: `AB.P18.001`
- Segunda instância do processo 18: `AB.P18.002`
- Terceira instância do processo 33: `AB.P33.003`

**Vantagens**:
- ✅ Rastreabilidade completa
- ✅ Identificação única
- ✅ Hierarquia visual
- ✅ Facilita buscas e relatórios

---

## 🔌 APIs Disponíveis

### Listar Instâncias
```
GET /api/companies/{company_id}/process-instances
```

### Criar Instância (Disparar)
```
POST /api/companies/{company_id}/process-instances
```

### Atualizar Instância
```
PATCH /api/companies/{company_id}/process-instances/{instance_id}
```

**Campos atualizáveis**:
- `status`
- `priority`
- `assigned_collaborators` (JSON)
- `actual_hours`
- `notes` (JSON com logs)
- `completed_at`
- `started_at`

### Buscar Colaboradores da Rotina
```
GET /api/companies/{company_id}/processes/{process_id}/routine-collaborators
```

---

## 💡 Dicas de Uso

1. **Organize por Status**: Use os filtros para ver apenas pendentes, em andamento, etc.
2. **Priorize**: Marque urgências para destacar na lista
3. **Registre diariamente**: Mantenha o histórico atualizado
4. **Acompanhe horas**: Compare previsto vs realizado para melhorar estimativas
5. **Use códigos**: Facilita comunicação com a equipe

---

## ✅ Funcionalidades Implementadas

- [x] Criação de instâncias (disparo manual)
- [x] Listagem com filtros e busca
- [x] Página de gerenciamento
- [x] Registro de horas (previsto vs realizado)
- [x] Registro diário de logs
- [x] Conclusão com confirmação
- [x] Geração automática de códigos
- [x] Busca automática de colaboradores
- [x] Badges visuais por status e prioridade

---

## 🔮 Próximas Melhorias

- [ ] Disparo automático via rotinas
- [ ] Notificações de vencimento
- [ ] Relatórios de performance
- [ ] Dashboard de instâncias
- [ ] Anexos de arquivos
- [ ] Comentários entre colaboradores
- [ ] Histórico de mudanças de status

---

**Sistema pronto para uso! 🎉**

