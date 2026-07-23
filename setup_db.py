"""
setup_db.py
Initializes the local SQLite database for the Sentiment Tracker.

Run this ONCE before starting the pipeline:
    python setup_db.py
"""

import sqlite3

DB_PATH = "sentiment_data.db"


def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # WAL (Write-Ahead Logging) mode is important here: the pipeline script
    # writes to this DB continuously while the dashboard reads from it at the
    # same time. Default SQLite journal mode locks the whole file on write,
    # which would make the dashboard hang. WAL allows concurrent read+write.
    cursor.execute("PRAGMA journal_mode=WAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            author TEXT,
            source TEXT,
            keyword_matched TEXT,
            sentiment_score REAL,
            sentiment_label TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    # Index on timestamp speeds up the "ORDER BY timestamp" queries
    # the dashboard runs every few seconds.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON comments (timestamp)
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    initialize_database()