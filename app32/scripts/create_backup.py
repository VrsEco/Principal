#!/usr/bin/env python3
"""LEGADO BLOQUEADO.

Este script gerava backup local/dev com credencial hardcoded.
Use o fluxo oficial de produção:
    python scripts/download_backups.py

Para backup local controlado, use:
    powershell -File scripts/backup/run_local_pg_backup.ps1 -AllowDevelopmentBackup
"""
raise SystemExit("Script legado bloqueado: use o fluxo oficial documentado em docs/runbooks/backup_producao_configr.md")
