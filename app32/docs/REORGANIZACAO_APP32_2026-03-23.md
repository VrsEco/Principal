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

## Fase 4 executada

Foi executada uma curadoria operacional com abordagem **conservadora e orientada a domínio**.

Em vez de promover em massa o conteúdo restante de `root_legacy/`, foram elevados apenas grupos de **alta confiança**:

### Promoções realizadas

- `C:\GestaoVersus\app32\scripts\root_legacy\remote_legacy\` →
  `C:\GestaoVersus\app32\scripts\deploy\legacy_curated_remote\`
- `C:\GestaoVersus\app32\scripts\root_legacy\seed_and_simulation\` →
  `C:\GestaoVersus\app32\scripts\data\legacy_curated_seed_and_simulation\`

Total de scripts promovidos para áreas oficiais: **8**

Manifesto da fase 4:

- `C:\GestaoVersus\app32\scripts\root_legacy\manifest_phase4_curated_2026-03-23.json`

### Critério adotado

Foram promovidos apenas arquivos que atendiam simultaneamente a estes requisitos:

1. domínio funcional claro
2. baixo risco de colisão com superfície oficial existente
3. utilidade operacional evidente para `deploy` ou `data`

### O que ficou explicitamente retido

Os grupos abaixo permaneceram em `root_legacy/` por exigirem auditoria mais profunda:

- `diagnostics/` — alto volume e baixa padronização
- `database/` — potencial mutação de schema/dados; exige auditoria DBA
- `migrations/` — precisa convergir com processo oficial Alembic
- `tests_manual/` — útil para QA, mas ainda não estruturado como suíte oficial
- `misc/` — heterogêneo e sem fronteira arquitetural clara
- `shadowed_by_official/` — histórico preservado explicitamente não canônico

## Estado arquitetural após a fase 4

- raiz de `app32` saneada
- legado da raiz removido da superfície principal
- colisões classificadas
- ativos de `deploy` e `data` com valor operacional já reposicionados

## Próximo passo realmente maduro

O próximo passo não é mais reorganização estrutural ampla. É **industrialização**:

1. consolidar scripts recorrentes em CLIs oficiais por domínio
2. transformar verificações úteis de `diagnostics/` e `tests_manual/` em automação de QA
3. aposentar legado restante com métrica de uso e revisão de impacto
