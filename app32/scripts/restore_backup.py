#!/usr/bin/env python3
"""LEGADO BLOQUEADO.

Este script de restore continha credencial hardcoded.
Restauração deve ser feita por runbook específico, com credenciais via ambiente/secret store
e confirmação humana explícita por envolver operação destrutiva.
"""
raise SystemExit("Restore legado bloqueado: criar/usar runbook seguro antes de restaurar banco")
