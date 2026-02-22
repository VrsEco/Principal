
import os
import sys

# Mock environment variables for local test
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/test_db"

# Ensure we can import from the app directory
sys.path.append(os.getcwd())

try:
    from database.postgres_helper import get_engine
    
    print("Testing get_engine() in local environment...")
    engine = get_engine()
    print(f"Engine created: {engine}")
    print(f"Dialect: {engine.dialect.name}")
    print(f"Driver: {engine.dialect.driver}")
    
    # Check if it's using the fallback (psycopg2)
    if engine.dialect.driver == "psycopg2":
        print("SUCCESS: Local fallback is using psycopg2 as expected.")
    else:
        print(f"WARNING: Unexpected driver '{engine.dialect.driver}' for local environment.")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
