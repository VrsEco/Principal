# Plano de Implementação: Módulo PEV (Planejamento Estratégico de Valor) v2.0

Este documento detalha o estudo e planejamento para a migração e reescrita do módulo PEV do APP31 para o APP32, seguindo a Arquitetura v2.0 e todas as modernidades do projeto.

## 1. Visão Geral
O novo módulo de Planejamento será dividido em dois perfis principais, sem conflitos de navegação com o sistema principal, utilizando uma estrutura de "Sidebars Colináveis" e contexto de empresa/projeto.

### Perfis de Planejamento:
1. **Planejamento de Crescimento (Growth)**: Focado em escala, OKRs e direcionadores de longo prazo.
2. **Planejamento de Implantação (Implantation)**: Focado em estruturação, modelo financeiro e alinhamento estratégico.

---

## 2. Arquitetura de Dados (@DBA & @ARQUITETO)

### Novos Modelos (PostgreSQL):
- `Plan`: Entidade central que define o tipo (`growth` | `implantation`) e status.
- `PlanParticipant`: Gestão de quem participa de cada etapa do plano.
- `PlanSectionStatus`: Controle granular de progresso para cada item do menu (ex: OKRs Globais -> Concluído).
- `PlanDriver`: Direcionadores estratégicos (específico Growth).
- `PlanImplantationData`: Tabela polimórfica ou JSONB para dados de alinhamento, mercado e estruturas (específico Implantation).
- `PlanFinancialMetric`: Métricas do Modelo Financeiro.

### Segurança Multi-tenancy:
- Obrigatoriedade de `company_id` em todas as tabelas.
- Índices compostos por `(company_id, plan_id)`.

---

## 3. Camada de Serviço (@BACKEND_SERVICE)

Implementação de lógica "pura" em `services/plan_service.py`:
- Validação de RBAC (Quem pode editar o planejamento).
- Cálculo automático de `progress` do plano baseado nos `PlanSectionStatus`.
- Integração com `OKRService` e `ProjectService` existentes para criar links reais entre o planejamento e a execução.

---

## 4. API & Protocolo MCP (@BACKEND_API & @AI_ENGINEER)

### Rotas Flask (`/api/v2/plans`):
- Endpoints documentados e validados com **Pydantic**.
- Padrão RESTful para CRUD de planos e seções.

### MCP (Model Context Protocol):
- Exposição de ferramentas para Agentes de IA:
    - `get_plan_context`: Fornece à IA todo o contexto do planejamento atual.
    - `suggest_okrs`: Tool que usa LLM para sugerir OKRs baseada nos drivers do plano.
    - `update_section`: Permite Agentes atualizarem o status do planejamento após análise de arquivos/dados.

---

## 5. Interface e UX (@FRONTEND)

### Sidebar Especializado:
- Implementação de um `DualSidebar`: O sidebar principal do sistema colapsa para ícones, e o sidebar do Planejamento assume a área de navegação contextual.
- Estética Premium: Uso de TailwindCSS, micro-animações de progresso e Glassmorphism.

### Templates Principais:
1. **Dashboard de Planejamento**: Visão geral de progresso e saúde do plano.
2. **Formulários Dinâmicos**: Componentes Jinja2 reutilizáveis para OKRs, Drivers e Métricas.
3. **Relatório Final (Print-Ready)**: CSS `@media print` para gerar documentos impecáveis para apresentação a investidores/stakeholders.

---

## 6. Cronograma de Execução

1. **Sprint 1 (Base)**: Migração de Models e Schemas + Setup do PlanService.
2. **Sprint 2 (Growth)**: Implementação de Drivers e OKRs + UI de Crescimento.
3. **Sprint 3 (Implantation)**: Implementação de Modelo Financeiro e Mercado + UI de Implantação.
4. **Sprint 4 (Inteligência & Relatórios)**: Integração MCP, Agentes AI e Relatório Final Exportável.

---

**Auditoria @ARQUITETO**: O plano respeita a regra de arquivos <500 linhas (será modularizado) e multi-tenancy nativo.
