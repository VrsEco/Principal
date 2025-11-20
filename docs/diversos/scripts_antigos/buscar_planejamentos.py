#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para buscar planejamentos da empresa Eua - Moveis Planejados
"""

import re
import os


def buscar_planejamentos(arquivo_sql, company_id=25):
    """
    Busca planejamentos no arquivo SQL
    """
    print(f"\n{'='*60}")
    print(f"Analisando: {os.path.basename(arquivo_sql)}")
    print(f"{'='*60}")

    if not os.path.exists(arquivo_sql):
        print(f"❌ Arquivo não encontrado: {arquivo_sql}")
        return []

    # Verificar tamanho do arquivo
    tamanho_mb = os.path.getsize(arquivo_sql) / (1024 * 1024)
    print(f"📦 Tamanho: {tamanho_mb:.2f} MB")

    planejamentos = []
    linhas_analisadas = 0

    try:
        print(f"🔍 Procurando planejamentos com company_id = {company_id}...")

        with open(arquivo_sql, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                linhas_analisadas += 1

                # Mostrar progresso a cada 10000 linhas
                if linhas_analisadas % 10000 == 0:
                    print(f"   Analisadas {linhas_analisadas} linhas...", end="\r")

                # Procurar por INSERT INTO company_plans
                if "INSERT INTO" in linha and "company_plan" in linha.lower():
                    # Procurar por company_id = 25
                    if f"\t{company_id}\t" in linha or f" {company_id} " in linha:
                        planejamentos.append(linha.strip())

                # Também procurar diretamente por referências ao company_id 25
                elif "company_id" in linha.lower() and str(company_id) in linha:
                    if "plan" in linha.lower():
                        # Extrair informações relevantes
                        planejamentos.append(linha.strip())

        print(f"\n✅ Análise concluída! {linhas_analisadas} linhas verificadas")

    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return []

    return planejamentos


def analisar_resultados(planejamentos, nome_arquivo):
    """
    Analisa e exibe os resultados encontrados
    """
    print(f"\n{'='*60}")
    print(f"📊 RESULTADOS - {nome_arquivo}")
    print(f"{'='*60}")

    if not planejamentos:
        print("❌ Nenhum planejamento encontrado")
        return

    print(f"✅ Encontrados {len(planejamentos)} registro(s)")
    print(f"\n📋 Detalhes:\n")

    for idx, plan in enumerate(planejamentos, 1):
        print(f"{idx}. {plan[:200]}...")
        print()


def main():
    """
    Função principal
    """
    print("=" * 60)
    print("🔍 BUSCA DE PLANEJAMENTOS - EUA MOVEIS PLANEJADOS")
    print("=" * 60)

    # Arquivos para analisar
    arquivos = [
        r"C:\gestaoversus\referencias\recuperacao_28out\backup_recuperacao_20251028_v2.sql",
        r"C:\gestaoversus\referencias\recuperacao_28out\dump_bd_app_versus.sql",
    ]

    todos_planejamentos = {}

    for arquivo in arquivos:
        nome = os.path.basename(arquivo)
        planejamentos = buscar_planejamentos(arquivo, company_id=25)
        todos_planejamentos[nome] = planejamentos
        analisar_resultados(planejamentos, nome)

    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO GERAL")
    print("=" * 60)

    total = 0
    for nome, plans in todos_planejamentos.items():
        qtd = len(plans)
        total += qtd
        print(f"✅ {nome}: {qtd} planejamento(s)")

    print(f"\n🎯 TOTAL GERAL: {total} planejamento(s) para Eua - Moveis Planejados")
    print("=" * 60)


if __name__ == "__main__":
    main()
