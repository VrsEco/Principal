# 📘 Especificação Funcional – GestaoVersus (Ambiente Local)

**Última atualização:** 2025-11-10  
**Responsável:** Squad GestaoVersus  
**Status:** ✅ Ativa  
**Escopo:** Aplicação Flask servida em `http://127.0.0.1:5003`

---

## 1. Contexto do Sistema

GestaoVersus é uma plataforma modular de gestão empresarial construída em Flask,
organizada em blueprints e camadas (`models → services → modules → templates`).
Os módulos principais são:

- **PEV (Planejamento Estratégico Versus):** Implantação de planos, modelagem
  financeira (ModeFin) e acompanhamento de resultados.
- **GRV (Gestão de Resultados Versus):** Portfólios, projetos, indicadores e
  processos.
- **Meetings:** Gestão de agendas, pautas e atas.
- **My Work:** Distribuição e acompanhamento de tarefas individuais.

A aplicação utiliza PostgreSQL em produção e SQLite em desenvolvimento,
seguindo os padrões definidos em `docs/governance/*.md`.

---

## 2. Ambiente e Acesso

- **Base URL:** `http://127.0.0.1:5003`
- **Blueprints registrados:** `/pev`, `/grv`, `/meetings`, `/my-work`, `/auth`,
  `/logs`, `/route-audit`
- **Credenciais padrão (dev):**
  - Usuário: `admin@versus.com.br`
  - Senha: `123456`
- **Requisitos de sessão:** Flask-Login; cookies `gestaoversos_dev_session`
- **Tecnologias relevantes:** Python 3.9+, Flask 2.3.3, SQLAlchemy 2.x, Jinja2,
  Celery (opcional), Modal System v2 (`static/js/modal-system.js`)

---

## 3. Perfis de Usuário e Permissões

| Perfil        | Descrição                                     | Permissões principais                                     |
|---------------|-----------------------------------------------|-----------------------------------------------------------|
| `admin`       | Administrador interno Versus                  | Gerencia usuários, planos, dados sensíveis               |
| `consultant`  | Consultor Versus                              | Acesso total aos módulos operacionais                     |
| `client`      | Cliente final                                 | Visão restrita ao plano/company associado                 |

- Todas as rotas protegidas exigem `@login_required`.
- Endpoints CRUD devem aplicar `@auto_log_crud(entity_type)` para auditoria.
- O módulo de logs registra ações em `user_logs` com IP e user agent.

---

## 4. Fluxos Funcionais Principais

### 4.1 Autenticação

1. Usuário acessa `GET /auth/login` → formulário Jinja (`templates/auth/login.html`).
2. `POST /auth/login` (JSON ou form) valida credenciais via `AuthService`.
3. Em caso de sucesso:
   - Sessão Flask-Login criada (`remember` opcional).
   - Resposta JSON: `{"success": true, "redirect": "/dashboard"}`.
   - Log automático em `user_logs`.
4. `GET /auth/logout` encerra sessão e redireciona para `/auth/login`.

### 4.2 Entrada / Seleção de Plano

- `GET /` ou `/main` redireciona usuários autenticados para o hub do módulo PEV.
- `GET /plans/<plan_id>` carrega contexto do plano (empresa, ano, status).
- Navegação principal:
  - `http://127.0.0.1:5003/pev/implantacao?plan_id=<id>`
  - Cards direcionam para subpáginas (ex.: ModeFin, Produtos, Estruturas).

### 4.3 Módulo PEV – Implantação & ModeFin

- **Objetivo:** acompanhar implantação do plano estratégico e viabilidade financeira.
- **URLs-chave:**
  - `/pev/implantacao?plan_id=6` – visão geral de implantação.
  - `/pev/implantacao/modelo/modefin?plan_id=6` – ModeFin (modelagem financeira).
- **ModeFin (8 seções funcionais):**
  1. Resultados (resumo de margens, custos, links rápidos).
  2. Investimentos (CRUD Capital de Giro + planilha Bloco × Mês, integração com imobilizado).
  3. Fontes de recursos (CRUD por tipo, cards de totais).
  4. Distribuição de lucros (percentuais condicionais + destinações com data).
  5. Fluxo de caixa do investimento (saldo acumulado, colunas comparativas).
  6. Fluxo de caixa do negócio (60 meses, 11 colunas, cabeçalho fixo, acumulados).
  7. Fluxo de caixa do investidor (60 meses, foco na perspectiva do investidor).
  8. Análise de viabilidade (configuração de período, custo de oportunidade, VPL,
     ROI, TIR, resumo executivo).
- **Regras importantes:**
  - Faturamento é mensal (não dividir por 12).
  - Percentuais de destinação só aplicam em resultado positivo.
  - Datas de início controlam quando cada destinação passa a vigorar.
  - Todos os CRUDs seguem padrão modal documentado em
    `docs/governance/MODAL_STANDARDS.md`.

### 4.4 Módulo GRV – Gestão de Resultados

- **URL base:** `/grv`
- **Dashboard empresa:** `/grv/company/<company_id>`
  - Cards com projetos ativos, processos mapeados, capacidade operacional.
  - Navegação lateral estruturada (Identidade, Processos, Projetos, Indicadores,
    Rotina).
- **Funcionalidades principais:**
  - Cadastro e gestão de portfólios/projetos (`/grv/company/<id>/projects`).
  - Indicadores OKR (metas, avaliações, integrações com tabelas `indicators`).
  - Registro de processos e rotinas operacionais.
  - Uso intensivo de Playwright para exportações (instalação on-demand).
- **Regras de negócio:**
  - Normalização de códigos de indicadores (`normalize_indicator_code`).
  - Garantia de schemas auxiliares (`ensure_indicator_schema`).
  - CRUDs protegidos por `@login_required` e `@auto_log_crud`.

### 4.5 Módulo Meetings

- **URL base:** `/meetings`
- **Funcionalidades:** agendamento de reuniões, pauta, registro de decisões e anexos.
- **Fluxo típico:**
  1. Selecionar plano/empresa.
  2. Cadastrar reunião (data, participantes, pauta).
  3. Registrar atas e próximos passos.
  4. Exportar relatórios para PDF (via Playwright ou templates dedicados).

### 4.6 Módulo My Work

- **URL base:** `/my-work`
- **Objetivo:** dar visibilidade individual de tarefas, checklists e atividades vinculadas
  aos planos/OKRs.
- Integra com dados de distribuição de trabalho e indicadores.

---

## 5. APIs Relevantes (Referência para Testes)

| Método | Endpoint                                               | Descrição                                    | Auth | Logs |
|--------|--------------------------------------------------------|----------------------------------------------|------|------|
| POST   | `/auth/login`                                          | Autenticação (JSON/form)                     | ❌   | ✅   |
| GET    | `/auth/logout`                                         | Logout (redirect)                            | ✅   | ✅   |
| POST   | `/auth/logout`                                         | Logout via API                               | ✅   | ✅   |
| GET    | `/auth/users`                                          | Listar usuários (admin)                      | ✅   | ✅   |
| POST   | `/auth/users`                                          | Criar usuário (admin)                        | ✅   | ✅   |
| PUT    | `/auth/users/<id>`                                     | Atualizar usuário (admin)                    | ✅   | ✅   |
| PUT    | `/auth/users/<id>/status`                              | Ativar/inativar usuário (admin)              | ✅   | ✅   |
| GET    | `/api/companies/<company_id>/projects`                 | Listar projetos PEV/GRV                      | ✅   | ✅   |
| POST   | `/api/companies/<company_id>/projects`                 | Criar projeto                                | ✅   | ✅   |
| GET    | `/api/plans/<plan_id>/modefin/metrics`                 | Dados agregados ModeFin                      | ✅   | ✅   |
| POST   | `/api/plans/<plan_id>/modefin/capital-giro`            | CRUD Capital de Giro                         | ✅   | ✅   |
| POST   | `/api/plans/<plan_id>/modefin/funding`                 | CRUD Fontes de Recursos                      | ✅   | ✅   |
| POST   | `/api/plans/<plan_id>/modefin/profit-distribution`     | CRUD Distribuição de Lucros                  | ✅   | ✅   |
| POST   | `/api/plans/<plan_id>/modefin/result-rules`            | CRUD Destinações (percentual/fixo)           | ✅   | ✅   |
| POST   | `/api/plans/<plan_id>/modefin/analysis-settings`       | Configurar análise de viabilidade            | ✅   | ✅   |
| GET    | `/logs/user`                                           | Consulta de auditoria                       | ✅   | ❌   |
| GET    | `/route-audit/status`                                  | Status de cobertura de logging               | ✅   | ❌   |

> **Formato de resposta padrão:** `{"success": bool, "data": ..., "error": ...}`  
> **Status codes:** 200/201 sucesso; 400 requisição inválida; 401 não autenticado;
> 403 proibido; 404 não encontrado.

---

## 6. Principais Entidades e Campos

| Entidade                      | Campos-chave                                                                 |
|-------------------------------|------------------------------------------------------------------------------|
| `users`                       | `id`, `email`, `password_hash`, `name`, `role`, `is_active`, auditoria      |
| `companies`                   | `id`, `name`, `industry`, `client_code`, `created_at`, `is_deleted`         |
| `plans`                       | `id`, `company_id`, `name`, `year`, `status`, `created_at`, `updated_at`    |
| `plan_finance_capital_giro`   | `id`, `plan_id`, `name`, `type`, `amount`, `start_month`, `is_deleted`      |
| `plan_finance_funding_sources`| `id`, `plan_id`, `fund_type`, `amount`, `cost_rate`, `start_month`          |
| `plan_finance_result_rules`   | `id`, `plan_id`, `rule_type`, `value`, `start_date`, `notes`, `is_deleted`  |
| `plan_finance_metrics`        | `plan_id`, `executive_summary`, `periodo_analise_meses`, `custo_oportunidade_anual` |
| `projects` / `company_projects`| Dados de projetos e portfólios vinculados a empresas e planos               |
| `indicators`, `indicator_goals`| Metas e medidas OKR (vide funções `ensure_indicator_schema`)               |
| `user_logs`                   | Auditoria de ações (`user_id`, `action`, `entity_type`, `old_values`, `new_values`) |

Todas as tabelas devem possuir `created_at`, `updated_at`, `is_deleted` e ser
compatíveis com PostgreSQL e SQLite.

---

## 7. Regras de Negócio Essenciais

1. **Autenticação obrigatória** para qualquer rota protegida; redirecionar não
   autenticados para `/auth/login`.
2. **Soft delete** (`is_deleted = True`) em todas as exclusões lógicas.
3. **Paginação** obrigatória em listagens volumosas (consultar serviços antes de
   expor dados).
4. **Auditoria automática** em CRUD via `@auto_log_crud`.
5. **Validação de entrada** em todos os endpoints (usar serviços para aplicar
   regras).
6. **ModeFin:**
   - Destinações percentuais só aplicam quando `resultado_periodo > 0`.
   - Datas de início determinam aplicação de regras mês a mês.
   - Fluxos devem sempre possuir 60 meses de projeção.
7. **Indicadores:** códigos devem ser normalizados (`.IND.` → `.`), metas com
   tipos válidos (`single`, `monthly`, etc.).
8. **Uploads:** somente extensões permitidas em `UPLOAD_FOLDER`; arquivos ficam
   em `uploads/` com subpastas específicas.

---

## 8. Dados de Referência (Ambiente Local)

| Recurso                     | Valor/Observação                                                    |
|-----------------------------|---------------------------------------------------------------------|
| Empresa padrão Versus       | `company_id = 13` (ajustar conforme base local)                     |
| Plano exemplo implantado    | `plan_id = 6` (usado nos guias de implantação/ModeFin)              |
| URL ModeFin                 | `http://127.0.0.1:5003/pev/implantacao/modelo/modefin?plan_id=6`    |
| URL Implantação (geral)     | `http://127.0.0.1:5003/pev/implantacao?plan_id=6`                   |
| URL Projetos GRV            | `http://127.0.0.1:5003/grv/company/13/projects/projects`            |
| URL Dashboard GRV           | `http://127.0.0.1:5003/grv/dashboard`                               |
| URL Reuniões                | `http://127.0.0.1:5003/meetings`                                    |

> Confirme IDs reais via `/plans/<id>` e scripts auxiliares em `check_*` antes de
> executar testes automáticos.

---

## 9. Requisitos Não Funcionais

- **Segurança:** sem credenciais hardcoded adicionais; obedecer regras de logging
  (não registrar dados sensíveis).
- **Compatibilidade:** código deve rodar com PostgreSQL e SQLite, evitando tipos
  específicos (`JSONB`, `ARRAY`, etc.).
- **Performance:** evitar N+1; usar eager loading quando disponível; fluxos ModeFin
  calculados no serviço para evitar recomputações no template.
- **UX:** modais seguem `MODAL_STANDARDS` (z-index 25000, remover classe `hidden`
  ao abrir); scroll vertical/horizontal configurado conforme padrões.
- **Internacionalização:** formato numérico BR (`format_number_br`, `format_percent_br`).

---

## 10. Cenários de Teste Recomendados

1. **Login/logout feliz:** autenticar com admin, acessar dashboard, efetuar logout.
2. **Restrições de permissão:** tentar acessar `/auth/users` com perfil não admin
   → esperar 403.
3. **ModeFin – CRUD Capital de Giro:** criar item, editar valores, excluir (verificar
   persistência e recalculo dos cards).
4. **ModeFin – Destinações:** cadastrar regra percentual com data futura, validar que
   apenas meses elegíveis são afetados.
5. **ModeFin – Fluxos:** conferir que tabelas exibem 60 linhas (meses) e totais
   acumulados corretos.
6. **ModeFin – Análise:** alterar período para 36 meses e custo oportunidade 12%,
   validar recalculo de VPL/ROI/Payback.
7. **Projetos GRV:** criar novo projeto via API, consultar listagem, validar log em
   `user_logs`.
8. **Indicadores GRV:** atualizar meta com `goal_type` válido e confirmar normalização
   de códigos.
9. **Meetings:** criar reunião, anexar pauta, registrar ata, exportar (quando
   playwright disponível).
10. **Auditoria:** executar ações CRUD e verificar registros em `/logs/user` e
    `/route-audit/status`.

---

## 11. Referências

- `docs/governance/TECH_STACK.md`
- `docs/governance/ARCHITECTURE.md`
- `docs/governance/API_STANDARDS.md`
- `docs/governance/MODAL_STANDARDS.md`
- `docs/governance/FRONTEND_STANDARDS.md`
- `MODEFIN_IMPLEMENTACAO_COMPLETA_FINAL.md`
- Scripts auxiliares em `check_*.py` e `testar_*.py`

---

**Próxima revisão sugerida:** sincronizar este documento com novas features ou
migrações significativas (rodar checklist após cada implantação relevante).


