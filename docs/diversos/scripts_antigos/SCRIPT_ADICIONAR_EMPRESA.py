#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Adicionar Empresas ao Sistema APP26
Uso: python SCRIPT_ADICIONAR_EMPRESA.py
"""

import sqlite3
from datetime import datetime


def adicionar_empresa():
    """Adiciona uma nova empresa ao banco de dados"""

    print("\n" + "=" * 70)
    print("  ADICIONAR NOVA EMPRESA - APP26")
    print("=" * 70 + "\n")

    # Coletar dados da empresa
    print("Preencha os dados da empresa:\n")

    nome = input("Nome da Empresa (obrigatorio): ").strip()
    if not nome:
        print("ERRO: Nome da empresa e obrigatorio!")
        return

    razao_social = input("Razao Social (opcional): ").strip() or nome
    setor = input("Setor/Industria (opcional): ").strip() or ""
    porte = input("Porte (Micro/Pequena/Media/Grande - opcional): ").strip() or ""
    descricao = input("Descricao da empresa (opcional): ").strip() or ""

    # MVV (Missão, Visão, Valores)
    print("\n--- MISSAO, VISAO E VALORES (opcional) ---")
    missao = input("Missao: ").strip() or ""
    visao = input("Visao: ").strip() or ""
    valores = input("Valores: ").strip() or ""

    # Nome do plano
    print("\n--- PLANO ESTRATEGICO ---")
    ano_atual = datetime.now().year
    nome_plano = input(
        f"Nome do Plano (padrao: Planejamento Estrategico {ano_atual}): "
    ).strip()
    if not nome_plano:
        nome_plano = f"Planejamento Estrategico {ano_atual}"

    ano_plano = input(f"Ano do Plano (padrao: {ano_atual}): ").strip()
    ano_plano = int(ano_plano) if ano_plano.isdigit() else ano_atual

    # Confirmação
    print("\n" + "=" * 70)
    print("CONFIRME OS DADOS:")
    print("=" * 70)
    print(f"Nome: {nome}")
    print(f"Razao Social: {razao_social}")
    print(f"Setor: {setor or '(nao informado)'}")
    print(f"Porte: {porte or '(nao informado)'}")
    print(f"Descricao: {descricao or '(nao informada)'}")
    print(f"Missao: {missao or '(nao informada)'}")
    print(f"Visao: {visao or '(nao informada)'}")
    print(f"Valores: {valores or '(nao informados)'}")
    print(f"Plano: {nome_plano} ({ano_plano})")
    print("=" * 70)

    confirma = input("\nConfirmar adicao? (S/N): ").strip().upper()
    if confirma != "S":
        print("Operacao cancelada.")
        return

    # Adicionar ao banco
    try:
        conn = sqlite3.connect("instance/pevapp22.db")
        cursor = conn.cursor()

        # Inserir empresa
        cursor.execute(
            """
            INSERT INTO companies (
                name, legal_name, industry, size, description,
                mvv_mission, mvv_vision, mvv_values, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                nome,
                razao_social,
                setor,
                porte,
                descricao,
                missao,
                visao,
                valores,
                datetime.now().isoformat(),
            ),
        )

        company_id = cursor.lastrowid

        # Criar plano para a empresa
        cursor.execute(
            """
            INSERT INTO plans (company_id, name, year)
            VALUES (?, ?, ?)
        """,
            (company_id, nome_plano, ano_plano),
        )

        plan_id = cursor.lastrowid

        conn.commit()
        conn.close()

        print("\n" + "=" * 70)
        print("SUCESSO! Empresa adicionada:")
        print("=" * 70)
        print(f"ID da Empresa: {company_id}")
        print(f"Nome: {nome}")
        print(f"ID do Plano: {plan_id}")
        print(f"Plano: {nome_plano}")
        print("\nAcesse: http://127.0.0.1:5002/grv/dashboard")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nERRO ao adicionar empresa: {e}")
        import traceback

        traceback.print_exc()


def listar_empresas():
    """Lista todas as empresas cadastradas"""
    try:
        conn = sqlite3.connect("instance/pevapp22.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, legal_name, industry 
            FROM companies 
            ORDER BY id
        """
        )

        empresas = cursor.fetchall()
        conn.close()

        print("\n" + "=" * 70)
        print("EMPRESAS CADASTRADAS")
        print("=" * 70 + "\n")

        if empresas:
            for emp in empresas:
                emp_id, nome, razao, setor = emp
                print(f"ID: {emp_id:<5} | Nome: {nome:<35} | Setor: {setor or 'N/A'}")
        else:
            print("Nenhuma empresa cadastrada.")

        print("\n" + "=" * 70 + "\n")

    except Exception as e:
        print(f"ERRO ao listar empresas: {e}")


def menu_principal():
    """Menu principal do script"""
    while True:
        print("\n" + "=" * 70)
        print("  GERENCIAMENTO DE EMPRESAS - APP26")
        print("=" * 70)
        print("\n1. Adicionar nova empresa")
        print("2. Listar empresas cadastradas")
        print("3. Sair")
        print("\n" + "=" * 70)

        opcao = input("\nEscolha uma opcao: ").strip()

        if opcao == "1":
            adicionar_empresa()
        elif opcao == "2":
            listar_empresas()
        elif opcao == "3":
            print("\nEncerrando...\n")
            break
        else:
            print("\nOpcao invalida! Tente novamente.")


if __name__ == "__main__":
    menu_principal()
