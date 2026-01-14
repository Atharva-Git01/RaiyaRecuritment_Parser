
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "saas_db"),
        )
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM batches LIKE 'batch_guid'")
        result = cursor.fetchone()
        
        if not result:
            print("Adding batch_guid column...")
            cursor.execute("ALTER TABLE batches ADD COLUMN batch_guid VARCHAR(36) AFTER batch_id")
            conn.commit()
            print("✅ Added batch_guid column.")
        else:
            print("ℹ️ batch_guid column already exists.")

        conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate()
