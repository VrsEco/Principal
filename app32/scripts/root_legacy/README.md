# Root Legacy

Scripts Python historicamente mantidos na raiz de `app32` foram reorganizados aqui por categoria em 23/03/2026.

Categorias:
- `diagnostics/`
- `database/`
- `migrations/`
- `seed_and_simulation/`
- `tests_manual/`
- `remote_legacy/`
- `misc/`

## Fase 3 — saneamento de colisões

Na fase 3 da reorganização, os scripts legados que possuíam **mesmo nome** de scripts já existentes em `C:\GestaoVersus\app32\scripts\` foram reclassificados para:

- `shadowed_by_official/`

Objetivo:

- evitar ambiguidade operacional
- preservar histórico sem promover script legado a canônico
- deixar explícito que o caminho oficial é `scripts/`

Manifesto da fase 3:

- `C:\GestaoVersus\app32\scripts\root_legacy\manifest_phase3_shadowed_2026-03-23.json`

### Política canônica

- Scripts em `C:\GestaoVersus\app32\scripts\` são a referência operacional oficial.
- Scripts em `C:\GestaoVersus\app32\scripts\root_legacy\` são histórico controlado.
- Scripts em `C:\GestaoVersus\app32\scripts\root_legacy\shadowed_by_official\` não devem ser usados como entrypoint padrão sem revisão técnica explícita.
