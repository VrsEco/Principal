from database.postgresql_db import PostgreSQLDatabase

print("has method", hasattr(PostgreSQLDatabase, "get_company_profile"))
print("methods", [m for m in dir(PostgreSQLDatabase) if "company" in m])
