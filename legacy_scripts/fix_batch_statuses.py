import mysql.connector
from app.saas_db import get_db_connection, check_and_update_batch_status

def fix_all_batches():
    print("🔄 Checking and updating all batch statuses...")
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT batch_id FROM batches")
        batches = cursor.fetchall()
        
    count = 0
    for b in batches:
        bid = b['batch_id']
        try:
            check_and_update_batch_status(bid)
            count += 1
        except Exception as e:
            print(f"❌ Error updating batch {bid}: {e}")
            
    print(f"✅ Finished checking {count} batches.")

if __name__ == "__main__":
    fix_all_batches()
