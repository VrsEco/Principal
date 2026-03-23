from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Database connection details
PASSWORD = quote_plus("*Paraiso1978")
DB_URL = f"postgresql://postgres:{PASSWORD}@localhost:5432/bdversusv2"

def run_migration():
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        print("Adicionando colunas de rotina...")
        
        # Adicionar routine_id em indicators
        try:
            conn.execute(text("ALTER TABLE indicators ADD COLUMN routine_id INTEGER;"))
            print("Coluna routine_id adicionada em indicators.")
        except Exception as e:
            print(f"Erro ou coluna já existe em indicators: {e}")

        # Adicionar routine_id em indicator_data
        try:
            conn.execute(text("ALTER TABLE indicator_data ADD COLUMN routine_id INTEGER;"))
            print("Coluna routine_id adicionada em indicator_data.")
        except Exception as e:
            print(f"Erro ou coluna já existe em indicator_data: {e}")
            
        # Adicionar foreign keys separadamente para evitar falhas se a coluna já existir mas sem FK
        try:
            conn.execute(text("ALTER TABLE indicators ADD CONSTRAINT fk_indicators_routine FOREIGN KEY (routine_id) REFERENCES routines(id);"))
        except: pass

        try:
            conn.execute(text("ALTER TABLE indicator_data ADD CONSTRAINT fk_indicator_data_routine FOREIGN KEY (routine_id) REFERENCES routines(id);"))
        except: pass

        conn.commit()
        print("Migração concluída.")

if __name__ == "__main__":
    run_migration()
