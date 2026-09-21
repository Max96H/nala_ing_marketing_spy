import sqlite3
from pathlib import Path

db_name = "bank_analysis.db"
schema_file = "schema.sql"

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DB_PATH = ROOT_DIR / "data" / db_name
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA_PATH = SCRIPT_DIR / schema_file

def initialize_database():
    """Loads schema.sql and creates database tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Read schema file content
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_script = f.read()

    # Execute all SQL queries in the script
    cursor.executescript(schema_script)

    conn.commit()
    conn.close()
    print(f"Database '{db_name}' initialized using '{schema_file}'.")


if __name__ == "__main__":
    initialize_database()