# 📋 Decision Log - Decisões Arquiteturais

**Projeto:** GestaoVersus  
**Última atualização:** 23/10/2025

---

## 🎯 Formato de Registro

Cada decisão deve conter:
- **Data:** Quando foi tomada
- **Contexto:** Por que foi necessária
- **Decisão:** O que foi decidido
- **Alternativas:** O que foi considerado
- **Consequências:** Impactos da decisão
- **Status:** Ativa, Superada, Cancelada

---

## 📚 Decisões Registradas

### **#001 - Uso de PostgreSQL como Banco Principal**

**Data:** 18/10/2025  
**Contexto:** Necessidade de suportar operações avançadas e escalabilidade  
**Decisão:** PostgreSQL como banco principal, SQLite apenas para testes locais  
**Alternativas:** MySQL, MongoDB  
**Consequências:** +Performance, +Features avançadas, -Simplicidade  
**Status:** ✅ Ativa

---

### **#002 - Arquitetura Modular com Blueprints**

**Data:** 18/10/2025  
**Contexto:** Separar módulos PEV, GRV, Meetings  
**Decisão:** Usar Flask Blueprints para modularização  
**Alternativas:** Monolito, Microserviços  
**Consequências:** +Organização, +Manutenibilidade, =Complexidade  
**Status:** ✅ Ativa

---

### **#003 - Database Abstraction Layer**

**Data:** 18/10/2025  
**Contexto:** Suportar PostgreSQL e SQLite simultaneamente  
**Decisão:** Criar `DatabaseInterface` com implementações específicas  
**Alternativas:** SQLAlchemy ORM completo  
**Consequências:** +Flexibilidade, +Controle, -Código boilerplate  
**Status:** ✅ Ativa

---

### **#004 - Soft Delete ao Invés de Hard Delete**

**Data:** 18/10/2025  
**Contexto:** Necessidade de auditoria e recuperação de dados  
**Decisão:** Usar `is_deleted=True` ao invés de DELETE real  
**Alternativas:** Hard delete, Archive table  
**Consequências:** +Auditoria, +Recuperação, -Complexidade queries  
**Status:** ✅ Ativa

---

### **#005 - Jinja2 Templates ao Invés de SPA**

**Data:** 18/10/2025  
**Contexto:** Simplicidade e manutenibilidade  
**Decisão:** Server-side rendering com Jinja2 + JavaScript Vanilla  
**Alternativas:** React, Vue, Angular  
**Consequências:** +Simplicidade, +SEO, -Interatividade  
**Status:** ✅ Ativa

---

### **#006 - Tipos de Planejamento (Evolução vs Implantação)**

**Data:** 23/10/2025  
**Contexto:** Diferentes fluxos para empresas existentes vs novos negócios  
**Decisão:** Campo `plan_mode` com valores 'evolucao' e 'implantacao'  
**Alternativas:** Dois módulos separados, Feature flags  
**Consequências:** +Flexibilidade, +Reutilização código, -Complexidade rotas  
**Status:** ✅ Ativa

---

### **#007 - Padrão PFPN para Formulários**

**Data:** 23/10/2025  
**Contexto:** Necessidade de UX consistente em formulários de edição  
**Decisão:** Criar padrão PFPN (Visualização/Edição) para todos os formulários  
**Alternativas:** Edição inline sempre ativa, Modals para edição  
**Consequências:** +UX profissional, +Consistência, +Segurança (confirmações)  
**Implementação:** `docs/patterns/PFPN_PADRAO_FORMULARIO.md`  
**Status:** ✅ Ativa

**Detalhes da decisão #007:**
- Campos em modo visualização: fundo cinza (#f1f5f9), readonly
- Campos em modo edição: fundo branco, editável
- Botões: Editar, Cancelar, Salvar, Excluir
- Restauração de valores ao cancelar
- Notificações de sucesso/erro
- Implementado primeiro em: Canvas de Expectativas dos Sócios

---

### **#008 - Docker para Desenvolvimento e Produção**

**Data:** [Data anterior]  
**Contexto:** Consistência entre ambientes dev/prod  
**Decisão:** Docker Compose para orquestração de serviços  
**Alternativas:** Instalação local, Vagrant  
**Consequências:** +Consistência, +Isolamento, -Curva aprendizado  
**Status:** ✅ Ativa

---

## 📝 Como Adicionar Nova Decisão

1. Copie o template abaixo
2. Preencha todos os campos
3. Adicione na seção "Decisões Registradas"
4. Atualize a data de última atualização

```markdown
### **#XXX - Título da Decisão**

**Data:** DD/MM/YYYY  
**Contexto:** [Por que foi necessária]  
**Decisão:** [O que foi decidido]  
**Alternativas:** [O que foi considerado]  
**Consequências:** [Impactos esperados]  
**Status:** ✅ Ativa / ⚠️ Em Revisão / ❌ Superada
```

---

## 🔍 Revisão de Decisões

Decisões devem ser revisadas:
- Trimestralmente (verificar se ainda fazem sentido)
- Quando aparecer problema relacionado
- Ao adicionar nova feature que conflite

---

**Mantenha este arquivo atualizado!**  
**Decisões arquiteturais impactam todo o time.**
