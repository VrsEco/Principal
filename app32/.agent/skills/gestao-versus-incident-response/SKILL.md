---
name: gestao-versus-incident-response
description: Use quando investigar e corrigir bugs, incidentes funcionais, falhas de API, divergências entre DEV e produção, problemas de permissão, multi-tenancy, sessão, schema, runtime ou deploy inconsistente no Gestão Versus.
---

# 🚨 Gestão Versus Incident Response

Skill canônica para investigar, corrigir e validar incidentes com evidência objetiva.

## Use quando
- houver bug funcional, erro de API, drift DEV x produção, problema de tenant, RBAC, sessão, schema ou runtime

## Sequência curta
1. Triar contexto mínimo do incidente
2. Validar integridade de ambiente
3. Reproduzir com evidência objetiva
4. Isolar a camada real da falha
5. Corrigir com mínima alteração segura
6. Validar local e no ambiente afetado
7. Encerrar com causa raiz e prevenção

## Guardrails
- diagnosticar antes de alterar
- tratar código, banco, dados, sessão e runtime como hipóteses separadas
- não encerrar sem validação no ambiente afetado
- nunca relaxar multi-tenancy

## Scripts
- `scripts/manut-erro.py`
- `scripts/smoke_create_app.py`
- `scripts/tenant_audit.py`
- `scripts/integrity_snapshot.py`
- `scripts/http_contract_template.py`
- `scripts/prod_file_probe.py`
- `scripts/prod_request_probe.py`

## Referências
- `references/runtime-checklist.md`
- `references/multi-tenancy-checklist.md`
- `references/evidence-template.md`
