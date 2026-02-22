#!/usr/bin/env python
"""
Script para executar todos os testes e gerar relatório
"""
import subprocess
import sys
import json
from datetime import datetime


def run_tests():
    """Executa todos os testes e retorna resultados"""
    print("=" * 70)
    print("EXECUTANDO TODOS OS TESTES DO GESTAOVERSUS")
    print("=" * 70)
    print()

    # Executar pytest com formato JSON para parsing
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_*.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_report.json",
        ],
        capture_output=True,
        text=True,
        cwd="testsprite_tests",
    )

    # Mostrar saída
    print(result.stdout)
    if result.stderr:
        print("ERROS:", result.stderr)

    # Tentar ler relatório JSON se existir
    try:
        with open("testsprite_tests/test_report.json", "r") as f:
            report = json.load(f)
            return report
    except:
        pass

    return {
        "exitcode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


if __name__ == "__main__":
    report = run_tests()
    print("\n" + "=" * 70)
    print("TESTES CONCLUÍDOS")
    print("=" * 70)
    sys.exit(report.get("exitcode", 0))
