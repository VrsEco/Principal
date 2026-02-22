Os agentes serão reorganizados em 6 Agentes de Trabalho, sob a liderança de um Agente Supervisor (Líder).

## 1. Agente Estrategista (CSO Virtual)
- **Foco:** Planejamento Estratégico, Análise de Mercados e Cenários.
- **Responsabilidades:** Elaboração e revisão do PEV, análise SWOT, busca de tendências de mercado, sugestão de OKRs.
- **Ferramentas:** `search_web`, `read_strategic_plan`, `generate_okrs`.

## 2. Agente de Negócios (Business Architect)
- **Foco:** Arquitetura Empresarial e Análise de Negócios.
- **Responsabilidades:** Mapeamento de processos, análise de maturidade empresarial, sugestão de melhorias em fluxos e organograma.
- **Ferramentas:** `analyze_processes`, `consult_company_structure`.

## 3. Agente de Operações (COO Virtual)
- **Foco:** Gestão de Rotinas, Prazos, Projetos e Desempenho.
- **Responsabilidades:** Monitoramento de prazos, cobrança de atividades (WhatsApp/Email), gestão de projetos, alertas de desvio de metas.
- **Ferramentas:** `check_deadlines`, `query_kpis`, `send_whatsapp_reminder`, `manage_projects`.
- **Autonomia:** Pode enviar mensagens ativamente para cobrar prazos.

## 4. Agente Financeiro (CFO Virtual)
- **Foco:** Gestão Financeira, Custos e Precificação.
- **Responsabilidades:** Análise de DRE, fluxo de caixa, viabilidade de projetos, cálculo de margem e projeções financeiras.
- **Ferramentas:** `query_financial_data`, `calculate_valuation`, `forecast_cashflow`.

## 5. Agente Auditor (Compliance Officer)
- **Foco:** Auditoria Interna e Regras.
- **Responsabilidades:** Garantir compliance, detectar anomalias, auditar logs e verificar consistência de dados.
- **Ferramentas:** `audit_logs`, `consult_rules` (RAG), `verify_consistency`.

## 6. Agente de Onboarding (Guia do Usuário)
- **Foco:** Cadastros e Auxílio na Utilização do Sistema.
- **Responsabilidades:** Guia passo a passo para novos usuários, auxílio no preenchimento de cadastros complexos (wizard), ensino sobre o uso do sistema.
- **Ferramentas:** `start_cadastro_wizard`, `search_knowledge_base`.
- **Permissão:** Pode realizar escritas no banco de dados (cadastros).

## Liderança: Agente Supervisor (Líder)
- **Função:** Orquestrador central. Recebe demandas, entende o contexto e delega para o agente especialista correto. Consolida a resposta final.
- **Canais:** App, WhatsApp, Email.
