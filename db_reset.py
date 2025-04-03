import psycopg2
from database import Base, engine

DB_NAME = "local_api_db"
DB_USER = "bruno"
DB_HOST = "localhost"

def full_schema_reset():
    print("🧨 Connecting to database for full schema wipe...")

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, host=DB_HOST)
    conn.autocommit = True
    cursor = conn.cursor()

    print("⚠️ Dropping and recreating public schema...")
    cursor.execute("DROP SCHEMA public CASCADE;")
    cursor.execute("CREATE SCHEMA public;")

    cursor.close()
    conn.close()

    print("✅ Schema wiped.")

    print("📦 Recreating tables from SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)
    print("✅ Done.")

if __name__ == "__main__":
    full_schema_reset()
