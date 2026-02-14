import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'backend', 'jinxiaocun.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE products ADD COLUMN original_weight TEXT DEFAULT '无'")
    print("Added original_weight column")
except Exception as e:
    print(f"Column may exist: {e}")

try:
    cur.execute("UPDATE products SET sku = '无' WHERE sku IS NULL")
    cur.execute("UPDATE customers SET phone = '无' WHERE phone IS NULL")
    conn.commit()
    print("Updated defaults")
except Exception as e:
    print(f"Update failed: {e}")

conn.close()