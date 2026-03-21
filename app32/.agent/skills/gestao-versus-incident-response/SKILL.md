---
name: gestao-versus-incident-response
description: Use quando investigar e corrigir bugs, incidentes funcionais, falhas de API, divergências entre DEV e produção, problemas de permissão, multi-tenancy, sessão, schema, runtime ou deploy inconsistente no Gestão Versus.
---

# 🚨 Gestão Versus Incident Response

Skill canônica para investigação, correção e validação de incidentes no Gestão Versus.

## Objetivo
Levar o agente ao ponto de correção com evidência objetiva, evitando falso diagnóstico, hotfix cosmético e deploy sem validação de runtime.

## Quando usar
- erro visual/toast genérico
- API falhando ou retornando resposta inesperada
- fluxo funciona em DEV e falha em produção
- suspeita de drift de código, banco ou runtime
- bug de RBAC/permissão contextual
- bug de tenant/sessão/`company_id`
- comportamento inconsistente após deploy

## Princípios obrigatórios
1. **Diagnosticar antes de alterar.**
2. **Provar a camada real da falha.**
3. **Tratar código, banco, dados, sessão e runtime como hipóteses separadas.**
4. **Não encerrar incidente sem validar o fluxo no ambiente afetado.**
5. **Em multi-tenancy, nunca confiar só no id do objeto.**

## Fluxo obrigatório

### 1. Triagem
Capture:
- tela/rota
- usuário/perfil
- empresa/tenant
- id do registro
- ação executada
- mensagem visual
- horário aproximado
- ambiente alvo

### 2. Integridade de ambiente
Validar antes de concluir qualquer diagnóstico:
- código local x remoto
- schema e dados do caso
- boot limpo da aplicação
- workers/restart real
- tenant/sessão/contexto

### 3. Reprodução com evidência
Reproduzir em ordem:
1. UI
2. request exato do frontend
3. route/resource/service

Sempre capturar:
- método
- URL
- querystring
- payload
- status
- body
- logs correlatos

### 4. Análise por camadas
Auditar nesta ordem:
1. template/HTML/Jinja
2. JS/frontend
3. route
4. resource/API
5. service
6. schema/serialização/validação
7. model/ORM
8. banco/dados
9. runtime/infra

### 5. Correção
Aplicar correção mínima e segura:
- preservar multi-tenancy
- preservar RBAC
- evitar duplicação desnecessária de regra
- mapear explicitamente rota nova x rota legada quando coexistirem

### 6. Validação
Executar:
- teste local do caso corrigido
- teste do endpoint afetado
- smoke de boot
- validação no ambiente real

### 7. Deploy disciplinado
Antes de deploy completo, confirmar se a correção já está commitada/pushada quando o fluxo remoto fizer reset/checkout.

### 8. Fechamento
Registrar:
- causa aparente
- causa raiz
- camada real
- arquivos alterados
- validações executadas
- prevenção futura

## Scripts utilitários
### Atalho principal
- `scripts/manut-erro.py`: ponto de entrada rápido para checks iniciais de incidente

### Checks locais
- `scripts/smoke_create_app.py`: smoke de boot da aplicação
- `scripts/tenant_audit.py`: auditoria objetiva de tenant/sessão/objeto
- `scripts/integrity_snapshot.py`: snapshot local de integridade de arquivos e checks rápidos
- `scripts/http_contract_template.py`: template para reproduzir contrato HTTP do bug

### Probes de produção
- `scripts/prod_file_probe.py`: compara hash local x produção para arquivos críticos
- `scripts/prod_request_probe.py`: reproduz request com sessão simulada no servidor e retorna status/body

## Ordem prática recomendada
1. `manut-erro.py`
2. `prod_file_probe.py` se houver suspeita de drift
3. `http_contract_template.py`
4. `prod_request_probe.py` para evidência final no ambiente afetado

## Referências
- `references/runtime-checklist.md`
- `references/multi-tenancy-checklist.md`
- `references/evidence-template.md`

## Compatibilidade
A skill `bug-investigation-playbook` pode continuar existindo como versão compatível, mas a skill recomendada do projeto passa a ser esta.
