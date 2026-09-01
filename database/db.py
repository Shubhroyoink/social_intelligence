import json
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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS emotions (
            post_id TEXT PRIMARY KEY,
            primary_emotion TEXT,
            emotion_json TEXT,
            sarcasm_flag INTEGER DEFAULT 0,
            stance TEXT,
            analyzed_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_emotions_time
        ON emotions (analyzed_at)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS demographics (
            post_id TEXT PRIMARY KEY,
            language TEXT,
            geo_hint TEXT,
            interests_json TEXT,
            inferred_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS network_nodes (
            handle TEXT,
            topic_query TEXT,
            degree_centrality REAL,
            betweenness_centrality REAL,
            eigenvector_centrality REAL,
            community_id INTEGER,
            is_kol INTEGER DEFAULT 0,
            computed_at TEXT NOT NULL,
            PRIMARY KEY (handle, topic_query)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS network_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_handle TEXT,
            target_handle TEXT,
            weight INTEGER DEFAULT 1,
            sentiment_shift TEXT,
            topic_query TEXT,
            computed_at TEXT NOT NULL
        )
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


def save_emotions(emotions):
    conn = sqlite3.connect(DB_PATH)

    for e in emotions:
        conn.execute("""
            INSERT OR REPLACE INTO emotions (
                post_id, primary_emotion, emotion_json,
                sarcasm_flag, stance, analyzed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            e["post_id"], e["primary_emotion"], e["emotion_json"],
            e["sarcasm_flag"], e["stance"], e["analyzed_at"]
        ))

    conn.commit()
    conn.close()


def get_emotions(topic_query=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = """
        SELECT e.*, p.topic_query, p.created_at
        FROM emotions e
        JOIN posts p ON e.post_id = p.id
        WHERE 1=1
    """
    params = []

    if topic_query:
        query += " AND p.topic_query = ?"
        params.append(topic_query)

    query += " ORDER BY p.created_at ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_demographics(demographics):
    conn = sqlite3.connect(DB_PATH)

    for d in demographics:
        conn.execute("""
            INSERT OR REPLACE INTO demographics (
                post_id, language, geo_hint, interests_json, inferred_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            d["post_id"], d["language"], d["geo_hint"],
            d["interests_json"], d["inferred_at"]
        ))

    conn.commit()
    conn.close()


def get_demographics(topic_query=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = """
        SELECT d.*, p.topic_query
        FROM demographics d
        JOIN posts p ON d.post_id = p.id
        WHERE 1=1
    """
    params = []

    if topic_query:
        query += " AND p.topic_query = ?"
        params.append(topic_query)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_demographics_summary(topic_query=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT d.language, d.geo_hint, d.interests_json
        FROM demographics d
        JOIN posts p ON d.post_id = p.id
        WHERE 1=1
    """
    params = []
    if topic_query:
        query += " AND p.topic_query = ?"
        params.append(topic_query)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return {"languages": {}, "geo": {}, "interests": {}}

    lang_counts = {}
    geo_counts = {}
    interest_counts = {}

    for r in rows:
        lang = r["language"] or "unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        geo = r["geo_hint"]
        if geo:
            geo_counts[geo] = geo_counts.get(geo, 0) + 1

        if r["interests_json"]:
            try:
                interests = json.loads(r["interests_json"])
                for interest in interests:
                    interest_counts[interest] = interest_counts.get(interest, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

    return {"languages": lang_counts, "geo": geo_counts, "interests": interest_counts}


def save_network_nodes(nodes):
    conn = sqlite3.connect(DB_PATH)

    for n in nodes:
        conn.execute("""
            INSERT OR REPLACE INTO network_nodes (
                handle, topic_query, degree_centrality, betweenness_centrality,
                eigenvector_centrality, community_id, is_kol, computed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            n["handle"], n["topic_query"], n["degree_centrality"],
            n["betweenness_centrality"], n["eigenvector_centrality"],
            n["community_id"], n["is_kol"], n["computed_at"]
        ))

    conn.commit()
    conn.close()


def save_network_edges(edges):
    conn = sqlite3.connect(DB_PATH)

    for e in edges:
        conn.execute("""
            INSERT INTO network_edges (
                source_handle, target_handle, weight,
                sentiment_shift, topic_query, computed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            e["source_handle"], e["target_handle"], e["weight"],
            e["sentiment_shift"], e["topic_query"], e["computed_at"]
        ))

    conn.commit()
    conn.close()


def get_network_nodes(topic_query=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM network_nodes WHERE 1=1"
    params = []

    if topic_query:
        query += " AND topic_query = ?"
        params.append(topic_query)

    query += " ORDER BY eigenvector_centrality DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_network_edges(topic_query=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM network_edges WHERE 1=1"
    params = []

    if topic_query:
        query += " AND topic_query = ?"
        params.append(topic_query)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    create_database()
    print("Database ready:", DB_PATH)
