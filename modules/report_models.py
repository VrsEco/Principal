
from database.postgres_helper import connect as pg_connect
import json

def _to_dict(cursor, row):
    """Converts a database row to a dictionary."""
    if not row:
        return None
    d = {}
    for i, col in enumerate(cursor.description):
        d[col[0]] = row[i]
    return d

def _decode_json_fields(row_dict):
    """Decodes fields that are stored as JSON strings."""
    if not row_dict:
        return None
    for key, value in row_dict.items():
        if isinstance(value, str) and value.startswith(('{', '[')):
            try:
                row_dict[key] = json.loads(value)
            except json.JSONDecodeError:
                pass # Keep as string if not valid JSON
    return row_dict

class ReportModelsManager:
    """
    Gerencia os modelos de relatório do banco de dados.
    """
    def __init__(self, db_path='instance/pevapp22.db'):
        """Inicializa o gerenciador."""
        self.db_path = db_path

    def _get_connection(self):
        """Retorna uma conexão com o banco de dados."""
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        return conn

    def get_model(self, model_id):
        """
        Busca um modelo de relatório pelo ID.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM report_models WHERE id = ?", (model_id,))
            row = cursor.fetchone()
            
            dict_row = _to_dict(cursor, row)
            conn.close()
            
            return _decode_json_fields(dict_row)
            
        except Exception as e:
            print(f"Erro ao buscar modelo de relatório {model_id}: {e}")
            return None

    def get_all_models(self):
        """
        Busca todos os modelos de relatório.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM report_models ORDER BY name")
            rows = cursor.fetchall()
            
            dict_rows = [_to_dict(cursor, row) for row in rows]
            conn.close()

            return [_decode_json_fields(row) for row in dict_rows]

        except Exception as e:
            print(f"Erro ao buscar todos os modelos de relatório: {e}")
            return []

    def save_model(self, model_data):
        """
        Salva um novo modelo de relatório.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Prepara os dados para inserção
            insert_data = (
                model_data.get('name', ''),
                model_data.get('description', ''),
                model_data.get('paper_size', 'A4'),
                model_data.get('orientation', 'Retrato'),
                model_data.get('margin_top', 20),
                model_data.get('margin_right', 15),
                model_data.get('margin_bottom', 15),
                model_data.get('margin_left', 20),
                model_data.get('header_height', 25),
                model_data.get('header_rows', 2),
                model_data.get('header_columns', 3),
                model_data.get('header_content', ''),
                model_data.get('footer_height', 12),
                model_data.get('footer_rows', 1),
                model_data.get('footer_columns', 2),
                model_data.get('footer_content', ''),
                model_data.get('created_by', 'system')
            )
            
            cursor.execute("""
                INSERT INTO report_models 
                (name, description, paper_size, orientation, margin_top, margin_right, 
                 margin_bottom, margin_left, header_height, header_rows, header_columns, 
                 header_content, footer_height, footer_rows, footer_columns, footer_content, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, insert_data)
            
            model_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return model_id
            
        except Exception as e:
            print(f"Erro ao salvar modelo de relatório: {e}")
            return None

    def update_model(self, model_id, model_data):
        """
        Atualiza um modelo de relatório existente.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Prepara os dados para atualização
            update_data = (
                model_data.get('name', ''),
                model_data.get('description', ''),
                model_data.get('paper_size', 'A4'),
                model_data.get('orientation', 'Retrato'),
                model_data.get('margin_top', 20),
                model_data.get('margin_right', 15),
                model_data.get('margin_bottom', 15),
                model_data.get('margin_left', 20),
                model_data.get('header_height', 25),
                model_data.get('header_rows', 2),
                model_data.get('header_columns', 3),
                model_data.get('header_content', ''),
                model_data.get('footer_height', 12),
                model_data.get('footer_rows', 1),
                model_data.get('footer_columns', 2),
                model_data.get('footer_content', ''),
                model_id
            )
            
            cursor.execute("""
                UPDATE report_models SET 
                name = ?, description = ?, paper_size = ?, orientation = ?, 
                margin_top = ?, margin_right = ?, margin_bottom = ?, margin_left = ?,
                header_height = ?, header_rows = ?, header_columns = ?, header_content = ?,
                footer_height = ?, footer_rows = ?, footer_columns = ?, footer_content = ?,
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, update_data)
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Erro ao atualizar modelo de relatório {model_id}: {e}")
            return False

    def delete_model(self, model_id):
        """
        Exclui um modelo de relatório.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM report_models WHERE id = ?", (model_id,))
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Erro ao excluir modelo de relatório {model_id}: {e}")
            return False
