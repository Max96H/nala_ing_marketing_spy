import sqlite3


def initialize_database(
    db_name="./data/bank_analysis.db", schema_file="schema.sql"
):
    """Loads schema.sql and creates database tables."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Read schema file content
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_script = f.read()

    # Execute all SQL queries in the script
    cursor.executescript(schema_script)

    conn.commit()
    conn.close()
    print(f"Database '{db_name}' initialized using '{schema_file}'.")


if __name__ == "__main__":
    initialize_database()