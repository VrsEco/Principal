"""
Script para testar as APIs de investimento
"""

import sys
import traceback
from config_database import get_db


def test_investment_categories():
    """Test get_plan_investment_categories - COM DEBUG INTERNO"""
    try:
        db = get_db()
        plan_id = 8

        print(f"🔍 Testando get_plan_investment_categories para plan_id={plan_id}")
        print(f"   Tipo de DB: {type(db).__name__}")

        # Testar método DIRETAMENTE COM TRY/CATCH INTERNO
        try:
            conn = db._get_connection()
            cursor = conn.cursor()

            print("   ✓ Conexão obtida")
            print("   ✓ Cursor criado")

            cursor.execute(
                """
                SELECT id, category_type, category_name, display_order
                FROM plan_finance_investment_categories
                WHERE plan_id = %s
                ORDER BY display_order
            """,
                (plan_id,),
            )

            print("   ✓ Query executada")

            rows = cursor.fetchall()
            print(f"   ✓ Fetchall executado - {len(rows)} linhas")

            categories = []
            for i, row in enumerate(rows):
                print(f"   📝 Processando linha {i+1}: {row}")
                print(f"      - row[0] = {row[0]}")
                print(f"      - row[1] = {row[1]}")
                print(f"      - row[2] = {row[2]}")
                print(f"      - row[3] = {row[3]}")

                categories.append(
                    {
                        "id": row[0],
                        "category_type": row[1],
                        "category_name": row[2],
                        "display_order": row[3],
                    }
                )

            conn.close()
            print(f"   ✅ Sucesso! {len(categories)} categorias processadas")
            return True

        except Exception as inner_e:
            print(f"   ❌ ERRO INTERNO: {inner_e}")
            print(f"   ❌ Tipo: {type(inner_e).__name__}")
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ EXCEPTION EXTERNA: {e}")
        traceback.print_exc()
        return False


def test_direct_query():
    """Test direct SQL query"""
    try:
        from config_database import get_db

        db = get_db()
        conn = db._get_connection()
        cursor = conn.cursor()

        print(f"\n🔍 Testando query SQL direta")

        # Query direta
        cursor.execute(
            """
            SELECT id, category_type, category_name, display_order
            FROM plan_finance_investment_categories
            WHERE plan_id = %s
            ORDER BY display_order
        """,
            (8,),
        )

        rows = cursor.fetchall()
        print(f"   Linhas retornadas: {len(rows)}")

        for row in rows:
            print(f"   - {row}")

        conn.close()

        if not rows:
            print("   ⚠️  Nenhuma categoria encontrada para plan_id=8")
            print("   💡 Execute: python scripts/seed_investment_items.py")

        return True

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE APIs DE INVESTIMENTO")
    print("=" * 60)

    # Teste 1: Método do DB
    result1 = test_investment_categories()

    # Teste 2: Query direta
    result2 = test_direct_query()

    print("\n" + "=" * 60)
    if result1 and result2:
        print("✅ Testes concluídos")
    else:
        print("❌ Testes falharam")
        sys.exit(1)
