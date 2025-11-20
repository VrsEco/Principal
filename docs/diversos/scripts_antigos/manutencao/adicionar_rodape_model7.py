#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Adicionar Rodapé no Model_7
Executa via Python para maior facilidade
"""

import sqlite3
from datetime import datetime


def adicionar_rodape():
    """Adiciona rodapé ao Model_7"""

    print("=" * 60)
    print("📄 ADICIONANDO RODAPÉ AO MODEL_7")
    print("=" * 60)

    try:
        # Conectar ao banco
        conn = sqlite3.connect("instance/pevapp22.db")
        cursor = conn.cursor()

        # Verificar se Model_7 existe
        cursor.execute("SELECT id, name FROM report_models WHERE id = 7")
        model = cursor.fetchone()

        if not model:
            print("\n❌ Model_7 não encontrado!")
            print("   Execute primeiro o script de criação de modelos.")
            conn.close()
            return False

        print(f"\n✅ Model encontrado: {model[1]}")

        # Configuração do rodapé
        footer_config = {
            "footer_height": 12,  # mm
            "footer_rows": 1,
            "footer_columns": 2,
            "footer_content": "Versus Gestão Corporativa - Todos os direitos reservados||Emitido em: {{date}} às {{time}}",
        }

        print(f"\n📝 Configuração do rodapé:")
        print(f"   - Altura: {footer_config['footer_height']}mm")
        print(f"   - Linhas: {footer_config['footer_rows']}")
        print(f"   - Colunas: {footer_config['footer_columns']}")
        print(f"   - Conteúdo:")

        # Dividir conteúdo por colunas
        columns = footer_config["footer_content"].split("||")
        for i, col in enumerate(columns, 1):
            print(f"      Coluna {i}: {col}")

        # Atualizar no banco
        cursor.execute(
            """
            UPDATE report_models 
            SET 
                footer_height = ?,
                footer_rows = ?,
                footer_columns = ?,
                footer_content = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 7
        """,
            (
                footer_config["footer_height"],
                footer_config["footer_rows"],
                footer_config["footer_columns"],
                footer_config["footer_content"],
            ),
        )

        conn.commit()

        print(f"\n✅ Rodapé adicionado com sucesso!")

        # Verificar a atualização
        cursor.execute(
            """
            SELECT 
                id, name, footer_height, footer_rows, 
                footer_columns, footer_content
            FROM report_models
            WHERE id = 7
        """
        )

        result = cursor.fetchone()

        print(f"\n📊 Verificação:")
        print(f"   - ID: {result[0]}")
        print(f"   - Nome: {result[1]}")
        print(f"   - Altura rodapé: {result[2]}mm")
        print(f"   - Linhas: {result[3]}")
        print(f"   - Colunas: {result[4]}")
        print(f"   - Conteúdo: {result[5]}")

        conn.close()

        print(f"\n" + "=" * 60)
        print("✨ PRONTO! Rodapé configurado no Model_7")
        print("=" * 60)
        print("\n💡 Próximo passo:")
        print("   Gere um novo relatório para ver o rodapé!")
        print("   python teste_relatorio_novo.py")

        return True

    except Exception as e:
        print(f"\n❌ Erro ao adicionar rodapé: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    adicionar_rodape()
