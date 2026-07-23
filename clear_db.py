import sqlite3

DB_PATH = "sentiment_data.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Delete all records from the comments table
cursor.execute("DELETE FROM comments;")

# 2. Commit the DELETE transaction so it is no longer open
conn.commit()

# 3. Now it is safe to run VACUUM to reclaim storage space
cursor.execute("VACUUM;")

conn.close()

print("✅ Successfully cleared all old data from sentiment_data.db!")