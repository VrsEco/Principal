# Reorganização Estrutural do `app32`

**Data:** 23/03/2026  
**Escopo:** limpeza segura da raiz de `C:\GestaoVersus\app32`

## O que foi feito

Foi executada uma reorganização **de baixo risco**, focada apenas em arquivos que não compõem o runtime principal:

- artefatos temporários do Codex (`.codex_temp_*`)
- relatórios e dumps gerados (`*.txt`, `*.log`, alguns `*.json` de saída)
- backups remotos/legados (`*_REMOTE.py`, `*.remote_backup`)
- arquivos órfãos de operação (`github_deploy_key_temp`, `null`, `qc`, `query`, `tmp_env_prod`)

Todos esses itens foram movidos para:

- `C:\GestaoVersus\app32\archive\temporary\root_reorg_2026-03-23\`

Manifesto detalhado:

- `C:\GestaoVersus\app32\archive\temporary\root_reorg_2026-03-23\manifest.json`

## Resultado objetivo

- arquivos na raiz antes: **606**
- arquivos na raiz depois: **364**
- itens movidos nesta fase: **242**

## Fase 2 executada

Foi executada uma segunda etapa para retirar scripts Python legados da raiz.

Os arquivos `.py` não essenciais ao runtime foram movidos para:

- `C:\GestaoVersus\app32\scripts\root_legacy\`

Categorias criadas:

- `diagnostics/`
- `database/`
- `migrations/`
- `seed_and_simulation/`
- `tests_manual/`
- `remote_legacy/`
- `misc/`

Manifesto da fase 2:

- `C:\GestaoVersus\app32\scripts\root_legacy\manifest_root_legacy_2026-03-23.json`

### Critério da fase 2

Foram preservados na raiz apenas entrypoints e arquivos centrais de runtime, como:

- `app.py`
- `main.py`
- `config.py`
- `config_database.py`
- `run_dev.py`
- `execute_deploy.py`
- `force_deploy.py`
- `force_deploy_v2.py`
- arquivos `passenger_wsgi*`

### Resultado da fase 2

- scripts Python legados movidos da raiz: **317**
- foco da raiz passou a ser predominantemente runtime/configuração

## O que propositalmente NÃO foi movido

Para não quebrar operação, **não** foram movidos automaticamente:

- arquivos centrais de runtime/configuração
- scripts Python soltos na raiz
- arquivos Markdown de documentação
- arquivos de compose/deploy/uwsgi/passenger

## Diagnóstico arquitetural restante

A raiz melhorou substancialmente, mas ainda existem pontos de evolução:

1. consolidar duplicidades entre `scripts/` e `scripts/root_legacy/`
2. revisar quais scripts legados devem ser:
   - promovidos para `scripts/` oficial
   - mantidos apenas como histórico
   - removidos no futuro
3. revisar documentação operacional que ainda aponta para caminhos antigos da raiz

## Recomendação

Executar uma **fase 3** opcional para saneamento definitivo:

- deduplicação entre scripts antigos e novos
- remoção controlada de legados obsoletos
- normalização de nomenclatura e READMEs por domínio

## Fase 3 executada

Foi executada uma terceira etapa focada em **colisões de nomenclatura** entre:

- `C:\GestaoVersus\app32\scripts\`
- `C:\GestaoVersus\app32\scripts\root_legacy\`

### Estratégia adotada

Quando um script legado possuía o **mesmo nome** de um script já existente na área oficial `scripts/`, ele **não foi removido** automaticamente.

Como os arquivos não eram idênticos, eles foram reclassificados para:

- `C:\GestaoVersus\app32\scripts\root_legacy\shadowed_by_official\`

Isso preserva histórico sem gerar ambiguidade sobre qual caminho é canônico.

### Resultado da fase 3

- colisões classificadas com segurança: **9**
- nenhum script oficial em `scripts/` foi alterado
- nenhum script legado colidente foi descartado

Manifesto da fase 3:

- `C:\GestaoVersus\app32\scripts\root_legacy\manifest_phase3_shadowed_2026-03-23.json`

### Política resultante

- `scripts/` = superfície operacional oficial
- `scripts/root_legacy/` = acervo histórico reorganizado
- `scripts/root_legacy/shadowed_by_official/` = legados preservados, mas explicitamente não canônicos

## Próxima evolução recomendada

Executar uma fase 4 orientada a arquitetura operacional:

1. promover scripts realmente úteis de `root_legacy/` para domínios oficiais
2. encapsular utilitários recorrentes em CLI única ou módulos reutilizáveis
3. remover legados obsoletos apenas após validação de uso real
