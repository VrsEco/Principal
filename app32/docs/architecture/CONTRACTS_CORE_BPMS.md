# APP32 — Núcleo de Gestão de Contratos + BPMS

**Data:** 2026-05-01  
**Status:** desenho arquitetural alvo  
**Especialista líder:** @ARQUITETO  
**Apoios naturais:** @BACKEND_SERVICE, @BACKEND_API, @DBA, @FRONTEND, @QA_AUTOMATION

---

## 1. Objetivo

Definir como o APP32 deve estruturar o **núcleo funcional de Gestão de Contratos** e como esse núcleo será consumido pelo **BPMS**.

Este documento formaliza:

- o que pertence ao **domínio de contratos**;
- o que pertence à **orquestração BPMS**;
- como os **cadastros compostos por abas** devem ser organizados;
- como suportar **customizações por tenant** sem contaminar o core;
- como o processo BPMN “Gerir Implantação de Contratos” deve consumir essas capacidades.

---

## 2. Tese arquitetural

O APP32 deve tratar **Gestão de Contratos** como um **domínio funcional próprio**, não como simples conjunto de telas abertas por activities BPMN.

Regra central:

> O módulo de contratos concentra dados, regras e estados do contrato.  
> O BPMS orquestra quando, por quem e em qual contexto essas capacidades são executadas.

Portanto:

- **Contrato** é domínio;
- **Gerir Implantação de Contratos** é processo;
- **BPMS** é a camada de orquestração operacional;
- **Shell de execução** é a experiência unificada de trabalho.

---

## 3. Fronteira entre domínio e BPMS

## 3.1. Pertence ao domínio de contratos

- favorecido / contraparte;
- classificação de favorecido:
  - cliente;
  - fornecedor;
  - ambos;
- contrato;
- itens do contrato;
- itens de faturamento;
- condições financeiras;
- condições fiscais;
- gatilhos, datas e recorrências;
- retenções;
- observações;
- artefatos documentais;
- PDF do contrato;
- contrato assinado escaneado;
- status contratual.

## 3.2. Pertence ao BPMS

- sequência do trabalho;
- atividade atual;
- responsáveis operacionais;
- SLA;
- pause / resume;
- rotina;
- execução manual externa;
- execução automática;
- execução por REST/MCP;
- timeline;
- shell única de controle e execução.

---

## 4. Agregados principais do núcleo de contratos

## 4.1. `contract_party`

Representa o favorecido / contraparte.

Campos mínimos esperados:

- `company_id`
- `name`
- `document_number`
- `party_type_flags`
  - `is_customer`
  - `is_supplier`
- dados cadastrais
- contatos
- status

Regra:

> Um favorecido pode ser cliente, fornecedor ou ambos.

## 4.2. `contract`

Entidade raiz do domínio.

Campos mínimos esperados:

- `company_id`
- `party_id`
- `code`
- `title`
- `status`
- `signed_at`
- `service_start_at`
- `billing_start_at`
- `competence_rule`
- `due_rule`
- `periodicity`
- `notes`

## 4.3. `contract_item`

Itens negociados que compõem o contrato.

Exemplos:

- serviço;
- pacote;
- entregável;
- item comercial;
- item operacional.

## 4.4. `contract_billing_item`

Itens e regras de faturamento.

Exemplos:

- item faturável;
- valor;
- competência;
- vencimento;
- periodicidade;
- gatilho de cobrança.

## 4.5. `contract_financial_term`

Condições financeiras da execução do contrato.

Exemplos:

- regra de faturamento;
- condição de pagamento;
- recorrência;
- parcelamento;
- vencimento;
- reajuste.

## 4.6. `contract_fiscal_term`

Condições fiscais e retenções.

Exemplos:

- natureza fiscal;
- retenções;
- parâmetros tributários;
- observações fiscais;
- vínculo futuro com fiscal/faturamento/financeiro.

## 4.7. `contract_trigger`

Datas e gatilhos relevantes.

Exemplos:

- data da assinatura;
- início dos serviços;
- início do faturamento;
- competência;
- data de renovação;
- alertas.

## 4.8. `contract_document`

Artefatos do contrato.

Exemplos:

- minuta;
- PDF gerado;
- contrato assinado escaneado;
- anexos;
- evidências.

---

## 5. Política oficial de composição por abas

Todos os cadastros ricos do domínio de contratos devem suportar composição por abas com separação formal entre:

- **abas core**
- **abas capability**
- **abas extension**

## 5.1. Regra de governança

### Abas core
São estáveis, transversais e pertencem ao núcleo do domínio.

### Abas capability
São acopladas a capacidades reutilizáveis, ativáveis conforme contexto.

### Abas extension
São específicas de tenant ou solução, sem contaminar o core.

Regra:

> Não criar nova tela inteira por cliente quando a necessidade puder ser absorvida por aba capability ou aba extension controlada.

---

## 6. Cadastro de favorecido — composição por abas

## 6.1. Abas core sugeridas

1. **Resumo**
2. **Classificação**
3. **Dados Cadastrais**
4. **Contatos**
5. **Observações**

### Regra da aba `Classificação`

Deve permitir marcar:

- cliente;
- fornecedor;
- ambos.

Isso deve ser atributo do domínio, e não regra escondida em processo.

## 6.2. Abas capability possíveis

- **Financeiro**
- **Fiscal**
- **Documentos**
- **Histórico**

## 6.3. Abas extension possíveis

- dados regulatórios específicos;
- campos setoriais;
- classificações próprias de um cliente.

---

## 7. Cadastro de contrato — composição por abas

## 7.1. Abas core sugeridas

1. **Resumo**
2. **Cliente**
3. **Itens do Contrato**
4. **Itens de Faturamento**
5. **Periodicidade**
6. **Fiscal**
7. **Cobrança**
8. **Observações**
9. **Revisão**

## 7.2. Abas capability sugeridas

1. **Validar / Editar Contrato**
2. **Gerar PDF**
3. **Documentos / Anexos**
4. **Contrato Assinado**
5. **Histórico do Processo**
6. **Integrações**
7. **Faturamento Derivado**

### Shell MVP implementado em 2026-05-01

O MVP publicado do módulo passou a refletir esta matriz com:

- favorecido com card de **Classificação** e opções explícitas `Cliente` / `Fornecedor`;
- contrato com abas:
  - `Resumo`
  - `Cliente`
  - `Itens do Contrato`
  - `Itens de Faturamento`
  - `Periodicidade`
  - `Fiscal`
  - `Cobrança`
  - `Observações`
  - `Revisão`
  - `Validar / Editar Contrato`
  - `Gerar PDF`
  - `Contrato Assinado`
  - `Documentos / Anexos`

## 7.3. Abas extension possíveis

Exemplos:

- composição fiscal específica por tenant;
- cláusulas setoriais;
- dados operacionais próprios de um cliente;
- regras especiais de retenção;
- complementos de cobrança.

---

## 8. Metadados mínimos por aba

Cada aba deve ser governada por metadados:

- `tab_key`
- `label`
- `scope`
  - `core`
  - `capability`
  - `extension`
- `entity_type`
- `capability_key` quando aplicável
- `visible_when`
- `required_when`
- `order`
- `interaction_mode`
- `save_strategy`

Exemplo conceitual:

```json
{
  "tab_key": "contract_billing_items",
  "label": "Itens de Faturamento",
  "scope": "core",
  "entity_type": "contract",
  "visible_when": ["contract_started"],
  "required_when": ["before_review"],
  "order": 40,
  "interaction_mode": "form_inline",
  "save_strategy": "step"
}
```

---

## 9. Classificação da demanda por aba

Ao modelar um processo e identificar uma necessidade nova, a decisão deve seguir a ordem:

### A. Já existe aba core?
- usar como está;
- ou evoluir o core se a necessidade for transversal.

### B. Já existe capability reutilizável?
- ativar aba capability;
- ajustar binding com BPMS.

### C. É algo exclusivo do tenant?
- criar aba extension;
- manter isolamento por `company_id`;
- evitar contaminar a experiência dos demais tenants.

### D. Não existe nada aderente?
- criar capability nova ou módulo novo, conforme classificação arquitetural.

---

## 10. Consumo pelo BPMS

O BPMS não deve armazenar dados estruturais do contrato como fonte primária.

Ele deve armazenar apenas:

- `bpmn_element_id`
- `execution_mode`
- `interaction_mode`
- `capability_key`
- `route_name`
- `ui_schema_json`
- `completion_rules_json`
- `sla_minutes`

Exemplos:

- activity “Cadastrar favorecido”
  - abre aba `Classificação` + `Dados Cadastrais`
- activity “Cadastrar contrato”
  - abre `Itens do Contrato`, `Itens de Faturamento`, `Financeiro`, `Fiscal`, `Datas e Gatilhos`
- activity “Gerar PDF”
  - executa capability de geração documental
- activity “Incluir contrato assinado escaneado”
  - abre aba `Contrato Assinado`

---

## 11. Relação com customizações por cliente

## 11.1. O que pode ir para o núcleo

Vai para o núcleo quando:

- a necessidade é recorrente;
- há forte probabilidade de reuso;
- a regra representa conceito contratual real;
- a solução melhora a plataforma como um todo.

## 11.2. O que deve virar aba extension

Vai para extensão quando:

- é exigência regulatória ou setorial de um cliente;
- a nomenclatura ou campos são exclusivos;
- a lógica não tem aderência transversal suficiente.

## 11.3. O que deve permanecer fora do APP32

Pode permanecer fora quando:

- a execução é externa;
- não compensa construir interface própria;
- o APP32 precisa apenas controlar status, prazo, evidência e vínculo.

Nesses casos:

- usar `manual_external`; ou
- usar integração REST/MCP quando fizer sentido.

---

## 12. Ordem recomendada de implementação

### Fase 1 — Núcleo mínimo

1. favorecido com classificação cliente/fornecedor/ambos
2. contrato
3. itens do contrato
4. itens de faturamento
5. financeiro
6. fiscal
7. datas e gatilhos
8. observações
9. documentos

### Fase 2 — Capacidades complementares

1. validação/edição do contrato
2. geração de PDF
3. upload de contrato assinado
4. histórico operacional

### Fase 3 — Acoplamento BPMS

1. contratos de atividade
2. binding BPMN → capability/tela
3. shell de execução
4. rotina
5. instância piloto

### Fase 4 — Integrações futuras

1. faturamento
2. financeiro
3. fiscal
4. assinatura
5. MCP / REST

---

## 13. Conclusão

O APP32 deve tratar **Gestão de Contratos** como:

- **domínio funcional próprio no core/capabilities**
- **cadastros compostos por abas governadas**
- **customizações absorvidas por abas extension quando necessário**
- **BPMS como camada final de orquestração**

Frase-guia:

> O contrato vive no domínio.  
> O processo vive no BPMN.  
> A execução vive no BPMS.  
> A experiência do usuário vive no shell único.

## 14. Documentos complementares

Para o detalhamento lógico de entidades, relacionamentos, abas por entidade, índices e MVP de implementação, consultar:

- `C:\GestaoVersus\app32\app32\docs\architecture\CONTRACTS_DATA_MODEL.md`
