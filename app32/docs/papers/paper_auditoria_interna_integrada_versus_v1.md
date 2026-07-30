# Paper - Auditoria Interna Integrada ao Gestão Versus v1

**Classe documental:** Paper  
**Status:** evolução conceitual / versão preliminar  
**Data:** 31/05/2026  
**Especialista líder:** @ARQUITETO  
**Apoios naturais:** @BACKEND_SERVICE, @BACKEND_API, @DBA, @AI_ENGINEER, @QA_AUTOMATION

---

## 1. Tese

A **Auditoria Interna** do Gestão Versus deve ser uma camada transversal de assurance sobre os módulos já existentes, e não um silo isolado.

O módulo deve criar contexto, critério, teste, evidência, ponto de auditoria, achado e relatório. A execução das ações corretivas deve reaproveitar **Gestão de Projetos**, **Gestão de Reuniões**, **Gestão de Processos**, **Gestão Financeira** e **Indicadores** sempre que possível.

Fluxo conceitual:

```text
Dados e rotinas do Versus
→ checklists / pontos de auditoria / analisadores
→ teste do auditor
→ evidência e papel de trabalho
→ achado, descarte ou monitoramento
→ ação em projeto / tarefa
→ follow-up em reunião / rotina
→ relatório e comunicação
```

---

## 2. Objetos centrais da Fase 01

A Fase 01 deve começar simples, com os seguintes objetos:

```text
audit_areas
audit_auditors
audit_checklists
audit_checklist_items
audit_schedules
audit_points
audit_workpapers
audit_findings
audit_evidence_links
audit_reports
```

Todos os objetos operacionais precisam possuir `company_id`, escopo tenant-safe, trilha de autoria e vínculo com usuário/colaborador quando aplicável.

---

## 3. Checklists de auditoria

Criar **checklists de auditoria** vinculáveis a:

1. **Processos** - quando o checklist testa controles de um processo ou rotina operacional.
2. **Projetos** - quando o checklist audita entregas, marcos, planos de ação ou projetos corretivos.
3. **Itens autônomos** - quando o checklist representa auditoria avulsa, inspeção, diagnóstico, diligência, conformidade legal ou checagem pontual.

Modelo conceitual:

```text
audit_checklist
├── company_id
├── title
├── description
├── checklist_type       # process, project, autonomous
├── linked_process_id
├── linked_project_id
├── linked_routine_id
├── area_id
├── owner_user_id
├── default_periodicity
├── active
└── metadata
```

Cada checklist possui itens auditáveis:

```text
audit_checklist_item
├── company_id
├── checklist_id
├── title
├── description_for_report
├── expected_evidence
├── criterion
├── weight
├── sort_order
├── active
└── metadata
```

O campo `description_for_report` é obrigatório na visão de produto: ele permite que cada item tenha uma descrição clara para compor o relatório final sem depender apenas do texto curto do checklist.

---

## 4. Status dos itens auditados

A execução do checklist deve aceitar, inicialmente:

```text
Conforme
Conforme com ressalva
Não conforme
Não aplicável
Não testado
```

Regra inicial:

```text
Conforme
→ encerra item sem achado.

Conforme com ressalva
→ pode gerar ponto de auditoria, recomendação ou achado de severidade média.

Não conforme
→ deve gerar ponto de auditoria/achado e demanda ação corretiva.

Não aplicável
→ exige justificativa.

Não testado
→ mantém pendência de execução.
```

O status pode evoluir para tipos configuráveis por tenant, desde que não quebre relatórios consolidados.

---

## 5. Pontos de auditoria

Um **Ponto de Auditoria** é um item que precisa ser checado porque representa possível exceção, fragilidade, ausência de evidência, comportamento fora do padrão ou dúvida de conformidade.

Ele pode nascer de três formas:

```text
Manual
→ auditor ou gestor registra um ponto para checagem.

Checklist
→ item com ressalva ou não conformidade gera ponto de auditoria.

Analisador futuro
→ cruzamento de dados identifica exceção e gera ponto automaticamente.
```

Regra arquitetural:

> Ponto de Auditoria não é achado. O achado exige análise, evidência e julgamento do auditor.

---

## 6. Integração com Projetos e atividades

Quando um item auditado estiver **Não conforme** ou **Conforme com ressalva**, o auditor deve poder:

1. criar um projeto novo;
2. associar a um projeto existente;
3. criar uma atividade/tarefa vinculada ao item auditado;
4. definir responsável, prazo, prioridade e evidência esperada;
5. acompanhar status sem duplicar plano de ação dentro da auditoria.

Fluxo recomendado:

```text
Item de checklist não conforme
→ ponto de auditoria ou achado
→ projeto novo ou projeto existente
→ atividade corretiva
→ evidência anexada na atividade/projeto
→ auditor valida
→ encerra ou reabre
```

A auditoria deve guardar apenas o vínculo:

```text
audit_finding/project_id/task_id
```

A execução da ação continua pertencendo ao módulo de Projetos.

---

## 7. Cronograma de auditoria

Criar um **cronograma de auditoria** para processos, rotinas, áreas e checklists.

O cronograma pode estar vinculado a:

- processo;
- rotina;
- checklist;
- área/departamento;
- auditor responsável;
- periodicidade.

Modelo conceitual:

```text
audit_schedule
├── company_id
├── title
├── process_id
├── routine_id
├── checklist_id
├── area_id
├── auditor_user_id
├── planned_start_date
├── planned_end_date
├── recurrence_rule
├── status
└── metadata
```

Regra de integração:

```text
Cronograma de auditoria
→ pode gerar execução de checklist
→ pode criar rotina/tarefa operacional
→ pode agendar reunião de abertura ou follow-up
```

---

## 8. Áreas, departamentos e auditores

A Fase 01 deve prever cadastros mínimos para organizar a auditoria:

```text
Área / Departamento
Auditor
Responsável auditado
Gestor da área
Comitê / viewer executivo
```

Perfis mínimos:

```text
auditor_admin
auditor
responsavel_auditado
viewer_executivo
```

Regras:

- auditor registra testes, papéis de trabalho e achados;
- responsável auditado responde ações e anexa evidências;
- viewer executivo consulta relatórios e dashboard;
- toda leitura e escrita exige `company_id`.

---

## 9. Papéis de trabalho

Cada execução de checklist ou ponto de auditoria pode possuir **papéis de trabalho**.

Campos mínimos:

```text
audit_workpaper
├── company_id
├── audit_execution_id
├── checklist_item_id
├── audit_point_id
├── auditor_user_id
├── comments
├── conclusion
├── alert_notes
├── evidence_summary
├── created_at
└── updated_at
```

Recursos obrigatórios:

- comentários do auditor;
- anexos de arquivos;
- anexos de imagens;
- vínculo com objetos do Versus;
- alertas internos;
- histórico de revisão.

Evidências podem ser:

```text
upload de arquivo
imagem / print
link para processo
link para projeto ou tarefa
link para reunião / ata
link para lançamento financeiro
link para indicador
comentário estruturado do auditor
```

---

## 10. Relatórios e comunicação

O módulo deve gerar relatório a partir de:

- descrição do checklist;
- descrição de cada item;
- status dos itens;
- comentários e papéis de trabalho;
- evidências;
- achados;
- ações corretivas;
- responsáveis e prazos;
- conclusão do auditor.

Saídas previstas:

```text
Relatório web
PDF
Envio por e-mail
Envio por WhatsApp
```

Regra de governança:

- envio externo precisa registrar destinatário, data/hora, versão do relatório e usuário remetente;
- WhatsApp deve respeitar seleção de empresa quando houver múltiplos tenants elegíveis;
- relatório financeiro ou sensível deve exigir permissão adequada.

---

## 11. Analisadores e cruzamentos futuros

Quando os dados estiverem estruturados no PostgreSQL, criaremos **Regras de Auditoria / Analisadores de Auditoria / Cruzamentos de Auditoria**.

Fluxo:

```text
Dados no PostgreSQL
→ analisador executa regra/cruzamento
→ identifica exceção ou padrão fora do esperado
→ cria alerta operacional ou ponto de auditoria
→ auditor analisa
→ achado, descarte ou monitoramento
```

Exemplos:

```text
FinancialRecipientClassificationAnalyzer
EmployeePaymentClassificationAnalyzer
RepeatedPaymentAnalyzer
ProcessOwnershipGapAnalyzer
IndicatorWithoutActionPlanAnalyzer
ProjectFollowupDelayAnalyzer
AccountingManualEntryAnalyzer
```

Regra central:

> Analisador cria Ponto de Auditoria, nunca achado direto.

---

## 12. Auditoria financeira - primeiros cruzamentos

Primeiros cruzamentos financeiros previstos:

1. validar pagamentos feitos a um destinatário e verificar classificações diferentes;
2. validar pagamentos a funcionários com classificação diferente de salário, despesas de viagem, reembolso ou congêneres;
3. validar pagamentos repetidos para a mesma conta com classificações diversas.

Saída:

```text
Lançamentos financeiros
→ regra de consistência
→ alerta operacional financeiro
→ ponto de auditoria financeira
→ auditor revisa evidências
→ achado, descarte ou monitoramento
```

---

## 13. MVP recomendado atualizado

Fase 01:

```text
Auditoria Interna v0.1
├── Cadastros de área/departamento e auditores
├── Checklists vinculados a processos, projetos ou autônomos
├── Itens de checklist com descrição para relatório
├── Execução de checklist com status
├── Pontos de Auditoria
├── Papéis de trabalho com anexos, imagens, comentários e alertas
├── Achados
├── Projeto/atividade corretiva para não conformidades
├── Cronograma de auditoria vinculado a processo/rotina/checklist
├── Relatório web/PDF
└── Envio por e-mail / WhatsApp
```

Fora da Fase 01:

- IA generativa de relatório;
- motor avançado de anomalias;
- risk scoring sofisticado;
- biblioteca completa COSO/COBIT;
- automação total de achados sem auditor.

---

## 14. Decisão proposta

A evolução proposta transforma a Auditoria Interna em uma camada prática de execução e governança:

```text
Checklist
→ execução
→ ponto de auditoria
→ papel de trabalho
→ achado
→ projeto/atividade
→ reunião de alinhamento
→ relatório
→ follow-up
```

Esse desenho mantém a simplicidade da Fase 01, mas já prepara o módulo para cruzamentos automáticos e auditoria contínua no futuro.

---

## 15. Onda 4 — relatório controlado e follow-up

A Onda 4 fecha o ciclo operacional básico sem duplicar Projetos, Atividades ou Reuniões:

```text
achado
→ projeto/atividade existente
→ reunião de alinhamento
→ relatório versionado
→ follow-up
→ validação do auditor
→ encerramento ou reabertura
```

### 15.1 Relatório versionado

- cada relatório nasce vinculado a uma execução e ao `company_id`;
- versões são numeradas por empresa e execução;
- o rascunho pode ser alterado até a aprovação humana;
- a emissão congela um snapshot de execução, itens, papéis de trabalho, evidências e achados;
- versão emitida é imutável; alterações exigem nova versão;
- a versão anterior passa para `superseded`, sem perda histórica;
- a saída web é preparada para impressão A4 e salvamento em PDF.

### 15.2 Follow-up

Estados operacionais:

```text
aguardando ação
→ em andamento
→ aguardando validação
→ resolvido
→ encerrado
```

O auditor pode reabrir o achado. Cada acompanhamento registra:

- status anterior e novo status;
- ação executada;
- evidências recebidas;
- validação do auditor;
- prazo e próxima revisão;
- usuário e data/hora do registro.

### 15.3 Limites desta entrega

Onda 4 entrega relatório controlado, visualização/PDF pelo navegador e follow-up. Distribuição auditável por e-mail e WhatsApp permanece como evolução incremental, com registro obrigatório de destinatário, versão, remetente e data/hora.
