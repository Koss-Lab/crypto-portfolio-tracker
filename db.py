# db.py

import psycopg2
import os
from dotenv import load_dotenv

def init_db():
    load_dotenv()

    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("📂 Connecting to database...")

        with open("schema.sql", "r", encoding="utf-8") as f:
            schema_sql = f.read()

        print("⚙️  Executing schema.sql...")
        cur.execute(schema_sql)

        print("✅ Database initialized successfully!")

    except Exception as e:
        print("❌ Error while initializing the database:", e)

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔌 Connection closed.")

if __name__ == "__main__":
    init_db()
