import sqlite3
from datetime import datetime, timezone


DB_PATH = "social.db"


def create_database():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            author_id TEXT,
            author_handle TEXT,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            parent_id TEXT,
            topic_query TEXT,
            reactions INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            replies INTEGER,
            views INTEGER
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_topic_created
        ON posts (topic_query, created_at)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sentiments (
            post_id TEXT PRIMARY KEY,
            platform TEXT,
            created_at TEXT,
            topic_query TEXT,
            label TEXT NOT NULL,
            positive_score REAL DEFAULT 0,
            neutral_score REAL DEFAULT 0,
            negative_score REAL DEFAULT 0,
            analyzed_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sentiment_time
        ON sentiments (topic_query, created_at)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_query TEXT,
            keyword TEXT NOT NULL,
            frequency INTEGER DEFAULT 0,
            window_start TEXT,
            window_end TEXT,
            analyzed_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trends_keyword
        ON trends (topic_query, keyword)
    """)

    conn.commit()
    conn.close()


def save_posts(posts):
    conn = sqlite3.connect(DB_PATH)

    for p in posts:
        conn.execute("""
            INSERT OR IGNORE INTO posts (
                id, platform, author_id, author_handle, text,
                created_at, collected_at, parent_id, topic_query,
                reactions, shares, replies, views
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["id"], p["platform"], p["author_id"], p["author_handle"],
            p["text"], p["created_at"], p["collected_at"], p["parent_id"],
            p["topic_query"], p["reactions"], p["shares"], p["replies"],
            p["views"]
        ))

    conn.commit()
    conn.close()


def save_sentiments(sentiments):
    conn = sqlite3.connect(DB_PATH)

    for s in sentiments:
        conn.execute("""
            INSERT OR REPLACE INTO sentiments (
                post_id, platform, created_at, topic_query, label,
                positive_score, neutral_score, negative_score, analyzed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s["post_id"], s["platform"], s["created_at"], s["topic_query"],
            s["label"], s["positive_score"], s["neutral_score"],
            s["negative_score"], s["analyzed_at"]
        ))

    conn.commit()
    conn.close()


def save_trends(trends):
    conn = sqlite3.connect(DB_PATH)

    for t in trends:
        conn.execute("""
            INSERT INTO trends (
                topic_query, keyword, frequency, window_start, window_end, analyzed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            t["topic_query"], t["keyword"], t["frequency"],
            t["window_start"], t["window_end"], t["analyzed_at"]
        ))

    conn.commit()
    conn.close()


def get_posts(topic_query=None, platform=None, limit=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM posts WHERE 1=1"
    params = []

    if topic_query:
        query += " AND topic_query = ?"
        params.append(topic_query)
    if platform:
        query += " AND platform = ?"
        params.append(platform)

    query += " ORDER BY created_at DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sentiments(topic_query=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM sentiments WHERE 1=1"
    params = []

    if topic_query:
        query += " AND topic_query = ?"
        params.append(topic_query)

    rows = conn.execute(query + " ORDER BY created_at ASC", params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trends(topic_query=None, limit=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM trends"
    params = []

    if topic_query:
        query += " WHERE topic_query = ?"
        params.append(topic_query)

    query += " ORDER BY window_start DESC, frequency DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    create_database()
    print("Database ready:", DB_PATH)
