#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Limpar Rodapé do Model_7
Deixa em branco para você adicionar via interface
"""

import sqlite3


def limpar_rodape():
    """Limpa rodapé do Model_7"""

    print("=" * 60)
    print("🧹 LIMPANDO RODAPÉ DO MODEL_7")
    print("=" * 60)

    try:
        # Conectar ao banco
        conn = sqlite3.connect("instance/pevapp22.db")
        cursor = conn.cursor()

        # Limpar rodapé
        cursor.execute(
            """
            UPDATE report_models 
            SET 
                footer_height = 0,
                footer_content = '',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 7
        """
        )

        conn.commit()

        print(f"\n✅ Rodapé limpo com sucesso!")

        # Verificar
        cursor.execute(
            "SELECT id, name, footer_height, footer_content FROM report_models WHERE id = 7"
        )
        result = cursor.fetchone()

        print(f"\n📊 Verificação:")
        print(f"   - ID: {result[0]}")
        print(f"   - Nome: {result[1]}")
        print(f"   - Altura rodapé: {result[2]}mm")
        print(f"   - Conteúdo: '{result[3]}'")

        conn.close()

        print(f"\n" + "=" * 60)
        print("✨ PRONTO! Agora adicione via interface:")
        print("   http://127.0.0.1:5002/settings/reports")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return False


if __name__ == "__main__":
    limpar_rodape()
