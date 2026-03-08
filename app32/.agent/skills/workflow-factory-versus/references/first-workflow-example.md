# Exemplo inicial recomendado

## Caso sugerido
`collaborator.occupancy`

### Objetivo
Responder a ocupacao de um colaborador no periodo informado, trazendo:
- horas disponiveis
- horas tomadas com processos
- horas registradas em projetos
- horas comprometidas com projetos
- saldo do periodo

### Entradas
- `empresa` (quando houver multiplas empresas)
- `colaborador`
- `periodo`

### Saida
- painel executivo
- base de calculo do periodo
- numeros de consumo e compromisso
- observacao sobre a heuristica usada para compromisso em projetos

### Integracoes esperadas
- `schemas/collaborator.py`
- `handlers/collaborator_handler.py`
- `presenters/collaborator_presenter.py`
- `menu_engine.py`
- `direct_execution.py`
- `workflow_engine_v3.md`
