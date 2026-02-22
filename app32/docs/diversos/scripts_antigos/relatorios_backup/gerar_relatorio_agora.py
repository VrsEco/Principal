#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera um relatório de teste rapidamente
"""

import sys
from modules.gerador_relatorios_reportlab import GeradorRelatoriosProfissionais

print("=" * 70)
print("GERANDO RELATORIO DE TESTE")
print("=" * 70)
print()

try:
    # Empresa ID (default = 1)
    empresa_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    print(f"Empresa ID: {empresa_id}")
    print("Iniciando geracao...")
    print()

    # Gera o relatório
    gerador = GeradorRelatoriosProfissionais()
    pdf_path = gerador.gerar_relatorio_projetos(empresa_id)

    print("=" * 70)
    print("[SUCESSO] RELATORIO GERADO!")
    print("=" * 70)
    print()
    print(f"Arquivo: {pdf_path}")
    print()

except Exception as e:
    print("=" * 70)
    print("[ERRO]", str(e))
    print("=" * 70)
    import traceback

    traceback.print_exc()
