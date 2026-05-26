# Gestão de Contratos — PJ Contratada como Emissora Fiscal

Status: canônico  
Classe: SPEC

## 1. Objetivo

Definir a regra oficial da aba fiscal do contrato no APP32.

## 2. Decisão oficial

No domínio de contratos:

- a **PJ contratada** deve ser informada no contrato;
- a mesma PJ será a **emissora da nota fiscal**;
- o sistema não deve permitir emissora fiscal divergente no fluxo padrão.

## 3. Boundary oficial

### Contrato

Guarda:

- cliente/tomador;
- `contracting_legal_entity_id`;
- vínculo comercial e jurídico.

### Fiscal do contrato

Guarda:

- integração `manual` | `api` | `spreadsheet`;
- provedor NFS-e;
- série/RPS;
- código do serviço;
- item da lista;
- natureza da operação;
- cidade do serviço;
- cidade do ISS;
- flags de retenção.

## 4. Regra de compliance

O CNPJ da PJ contratada deve ser o mesmo CNPJ usado na emissão fiscal derivada do contrato.

## 5. Regra de implementação

- backend deve validar `company_id`;
- regra de negócio fica em service;
- rota apenas recebe/salva;
- deve existir cadastro próprio de PJ contratada/emissora;
- faturamento nativo deve gerar snapshot fiscal da PJ usada.
