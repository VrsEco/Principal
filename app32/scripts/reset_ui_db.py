import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgres_helper import connect

def reset_db():
    print("Resetando tabelas de UI Reference...")
    conn = connect()
    try:
        cursor = conn.cursor()
        # Truncate com cascade para limpar elementos e páginas
        cursor.execute("TRUNCATE TABLE ui_pages CASCADE")
        # Resetar sequências se houver (aqui usamos códigos manuais, mas ids são serial)
        cursor.execute("ALTER SEQUENCE ui_pages_id_seq RESTART WITH 1")
        cursor.execute("ALTER SEQUENCE ui_elements_id_seq RESTART WITH 1")
        conn.commit()
        print("Tabelas limpas com sucesso!")
    except Exception as e:
        conn.rollback()
        print(f"Erro ao resetar: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    reset_db()
