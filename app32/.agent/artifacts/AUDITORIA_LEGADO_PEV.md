# AUDITORIA DE REFATORACAO PEV - APP32
# MAPEAMENTO DE ARQUIVOS LEGADOS VS NOVOS

Este documento rastreia os arquivos que estao sendo substituidos pela nova arquitetura modular do PEV.
Estes arquivos devem ser removidos ou arquivados somente apos a validacao completa do novo modulo.

================================================================================
STATUS: EM ANDAMENTO
DATA INICIO: 15/02/2026
================================================================================

## 1. MODELOS (models/)

| Arquivo Legado | Novo Arquivo Modular | Status | Observacoes |
|----------------|----------------------|--------|-------------|
| models/plan.py | models/pev/plan.py | [OK] | O antigo sera PEVPlan no __init__.py por enquanto |
| models/participant.py | models/pev/participant.py | [OK] | O antigo sera PEVParticipant por enquanto |
| models/okr_global.py | models/pev/growth/okr_global.py | [PEND] | Ainda a ser criado |
| models/okr_area.py | models/pev/growth/okr_area.py | [PEND] | Ainda a ser criado |
| models/product.py | models/pev/implantation/product.py | [PEND] | Ainda a ser criado |

## 2. SERVICOS (services/)

| Arquivo Legado | Novo Arquivo Modular | Status | Observacoes |
|----------------|----------------------|--------|-------------|
| (Novo) | services/pev/plan_service.py | [PEND] | Logica centralizada |
| (Novo) | services/pev/participant_service.py | [PEND] | Logica de participantes |
| (Novo) | services/pev/section_status_service.py| [PEND] | Logica de fluxo de secoes |

## 3. ROTAS API (api/routes/)

| Arquivo Legado | Novo Arquivo Modular | Status | Observacoes |
|----------------|----------------------|--------|-------------|
| api/routes/pev.py | api/routes/pev/v1/plans.py | [PEND] | O antigo usa Blueprints mistos |

## 4. TEMPLATES (templates/modules/pev/)

| Arquivo Legado | Novo Arquivo Modular | Status | Observacoes |
|----------------|----------------------|--------|-------------|
| templates/modules/pev/*.html | templates/modules/pev/common/ | [PEND] | Dashboard, Selecao, etc |
| templates/modules/pev/*.html | templates/modules/pev/growth/ | [PEND] | OKRs, Entrevistas, etc |
| templates/modules/pev/*.html | templates/modules/pev/implantation/ | [PEND] | Produtos, Modelos Fin, etc |

================================================================================
NOTAS DE INTEGRACAO
================================================================================

- No arquivo `models/__init__.py`, os novos modelos estao importados como `PEVPlan` e `PEVParticipant` para evitar conflito com os arquivos legados que ainda estao na raiz da pasta `models/`.
- O banco de dados ja foi atualizado com as tabelas definitivas.

================================================================================
LISTA DE EXCLUSAO POS-VALIDACAO
================================================================================
1. [ ] models/plan.py
2. [ ] models/participant.py
3. [ ] api/routes/pev.py
4. [ ] templates/modules/pev/ (conteudo antigo)
