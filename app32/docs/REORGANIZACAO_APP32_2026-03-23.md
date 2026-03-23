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

## O que propositalmente NÃO foi movido

Para não quebrar operação, **não** foram movidos automaticamente:

- arquivos centrais de runtime/configuração
- scripts Python soltos na raiz
- arquivos Markdown de documentação
- arquivos de compose/deploy/uwsgi/passenger

## Diagnóstico arquitetural restante

A raiz de `app32` ainda concentra muitos scripts utilitários e diagnósticos históricos.  
O principal hotspot remanescente é:

- **329 arquivos `.py` ainda soltos na raiz**

Isso indica necessidade de uma **fase 2** de reorganização, com triagem cuidadosa por categoria:

1. `scripts/diagnostics/`
2. `scripts/db/`
3. `scripts/migrations/`
4. `scripts/ops/`
5. `scripts/legacy_root/`

## Recomendação

Executar a fase 2 em branch dedicada, com:

- inventário de referências internas
- migração incremental por famílias de script
- aliases/README para preservar rastreabilidade operacional

