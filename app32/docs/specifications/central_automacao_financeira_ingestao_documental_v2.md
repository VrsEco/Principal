## Central de Automação Financeira — Ingestão Documental Fiscal v2

### Objetivo
Evoluir a Central para receber **XML fiscal**, **DANFE/DACTE em PDF/imagem** e **recibos**, gerando um **registro financeiro candidato revisável** com arquivos vinculados, rastreabilidade e storage canônico.

### Escopo implementado nesta v2
- upload de XML, PDF e imagem para a Central;
- storage canônico com artefatos:
  - original;
  - otimizado;
  - preview;
- detecção documental:
  - `nfe_xml`, `nfce_xml`, `cte_xml`;
  - `danfe_pdf`, `dacte_pdf`;
  - `receipt_pdf`, `receipt_image`;
  - `unknown_document`;
- extração estruturada:
  - chave, número, série, emitente, destinatário, datas, total;
- agrupamento documental por `document_group_key`;
- consolidação XML + DANFE em **um registro financeiro principal**;
- revisão assistida em `/financial/automation` com preview de origem e campos extraídos.

### Regras arquiteturais
- **multi-tenant obrigatório** via `company_id`;
- **Financeiro oficial não recebe documento bruto**; recebe apenas itens validados/gerados;
- **XML prevalece sobre DANFE** quando ambos estiverem presentes no mesmo grupo;
- **arquivo original é preservado**;
- **preview/artefatos derivados** são separados do original;
- **sem lógica de negócio na rota**; toda orquestração permanece em service.

### Persistência
#### financial_automation_documents
Evolução para representar documento fiscal/recibo e seus derivados:
- `original_relative_path`
- `optimized_relative_path`
- `preview_relative_path`
- `file_size_original`
- `file_size_optimized`
- `document_family`
- `document_type`
- `source_kind`
- `parser_status`
- `parser_version`
- `document_group_key`
- `structured_payload_json`
- `confidence_score`

#### financial_automation_records
Evolução para expor dados documentais revisáveis:
- `document_group_key`
- `document_type`
- `document_key`
- `external_document_number`
- `issuer_name`
- `issuer_document`
- `recipient_name`
- `recipient_document`
- `issue_date`
- `extracted_fields_json`
- `review_flags_json`

### Pipeline
1. upload do arquivo;
2. persistência do original;
3. geração opcional de otimizado/preview;
4. detecção do tipo documental;
5. extração estruturada;
6. agrupamento por chave fiscal ou fingerprint composto;
7. consolidação em registro candidato;
8. revisão humana na Central;
9. geração no Financeiro oficial.

### Estratégia de agrupamento
- prioridade 1: chave fiscal (`document_key`);
- prioridade 2: fingerprint composto:
  - tipo documental,
  - emitente,
  - destinatário,
  - número,
  - série,
  - data de emissão,
  - valor.

### Estratégia de classificação inicial
- XML fiscal: maior confiança;
- PDF textual: confiança média;
- imagem/OCR/recibo: confiança menor e revisão obrigatória.

### UI
Na grade da Central, cada registro deve mostrar:
- tipo do documento;
- número/série/chave;
- emitente/destinatário;
- valor/data;
- confiança;
- pendências;
- ação para visualizar documentos vinculados.
