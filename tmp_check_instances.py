from database.postgres_helper import connect


def main():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT current_database()")
    db_name = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT id, company_id, process_id, instance_code, title, status, created_at
        FROM process_instances
        ORDER BY id DESC
        LIMIT 10
        """
    )
    rows = cursor.fetchall()
    conn.close()
    print("database:", db_name)
    for row in rows:
        print(dict(row))


if __name__ == "__main__":
    main()

