import json
import os
import sqlite3
from datetime import datetime, timezone


DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "social.db")
)


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass
    return conn


def create_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            author_id TEXT,
            author_handle TEXT,
            text TEXT NOT NULL,
            raw_text TEXT,
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

    _migrate_posts_raw_text(conn)

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS narratives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_query TEXT,
            backend TEXT NOT NULL,
            model TEXT,
            stats_json TEXT,
            report_markdown TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_narratives_topic_created
        ON narratives (topic_query, created_at)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS youtube_videos (
            video_id TEXT NOT NULL,
            topic_query TEXT NOT NULL,
            title TEXT,
            channel TEXT,
            description TEXT,
            published_at TEXT,
            first_seen_at TEXT NOT NULL,
            last_fetched_at TEXT,
            comments_count INTEGER DEFAULT 0,
            PRIMARY KEY (video_id, topic_query)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_youtube_videos_topic
        ON youtube_videos (topic_query)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS x_profiles (
            handle TEXT NOT NULL,
            topic_query TEXT NOT NULL,
            display_name TEXT,
            platform_user_id TEXT,
            followers INTEGER,
            tweets_count INTEGER,
            lookup_status TEXT,
            first_seen_at TEXT NOT NULL,
            last_fetched_at TEXT,
            tweets_collected INTEGER DEFAULT 0,
            PRIMARY KEY (handle, topic_query)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_x_profiles_topic
        ON x_profiles (topic_query)
    """)

    conn.commit()
    conn.close()


def _migrate_posts_raw_text(conn):
    """Add the raw_text column to pre-existing posts tables (non-destructive).

    New databases create it in the CREATE TABLE already; this covers databases
    created before the column existed, so old rows simply get NULL.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
    if "raw_text" not in columns:
        conn.execute("ALTER TABLE posts ADD COLUMN raw_text TEXT")


def save_posts(posts):
    conn = get_connection()

    for p in posts:
        conn.execute("""
            INSERT OR IGNORE INTO posts (
                id, platform, author_id, author_handle, text,
                raw_text, created_at, collected_at, parent_id, topic_query,
                reactions, shares, replies, views
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["id"], p["platform"], p["author_id"], p["author_handle"],
            p["text"], p.get("raw_text"), p["created_at"], p["collected_at"],
            p["parent_id"], p["topic_query"], p["reactions"], p["shares"],
            p["replies"], p["views"]
        ))

    conn.commit()
    conn.close()


def save_sentiments(sentiments):
    conn = get_connection()

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
    conn = get_connection()

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
    conn = get_connection()
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
    conn = get_connection()
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
    conn = get_connection()
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
    conn = get_connection()

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
    conn = get_connection()
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
    conn = get_connection()

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
    conn = get_connection()
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
    conn = get_connection()
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
    conn = get_connection()

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
    conn = get_connection()

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
    conn = get_connection()
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
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM network_edges WHERE 1=1"
    params = []

    if topic_query:
        query += " AND topic_query = ?"
        params.append(topic_query)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_narrative(narrative):
    conn = get_connection()

    conn.execute("""
        INSERT INTO narratives (
            topic_query, backend, model, stats_json, report_markdown, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        narrative["topic_query"], narrative["backend"], narrative.get("model"),
        narrative.get("stats_json"), narrative["report_markdown"],
        narrative["created_at"]
    ))

    conn.commit()
    conn.close()


def upsert_youtube_video(video, topic_query, last_fetched_at=None, comments_count=None):
    """Record a video discovered for a topic (search cache / incremental dedup).

    First-seen metadata is preserved across updates; only discovery fields are
    refreshed. last_fetched_at/comments_count are set when the caller has
    actually extracted comments for the video.
    """
    conn = get_connection()

    conn.execute("""
        INSERT INTO youtube_videos (
            video_id, topic_query, title, channel, description, published_at,
            first_seen_at, last_fetched_at, comments_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id, topic_query) DO UPDATE SET
            title = excluded.title,
            channel = excluded.channel,
            description = excluded.description,
            published_at = excluded.published_at,
            last_fetched_at = CASE
                WHEN excluded.last_fetched_at IS NOT NULL
                THEN excluded.last_fetched_at
                ELSE youtube_videos.last_fetched_at
            END,
            comments_count = CASE
                WHEN excluded.comments_count IS NOT NULL
                THEN excluded.comments_count
                ELSE youtube_videos.comments_count
            END
    """, (
        video["video_id"], topic_query, video.get("title"),
        video.get("channel"), video.get("description"),
        video.get("published_at"), datetime.now(timezone.utc).isoformat(),
        last_fetched_at, comments_count
    ))

    conn.commit()
    conn.close()


def get_fetched_youtube_video_ids(topic_query):
    """Video IDs for a topic whose comments have already been extracted."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT video_id FROM youtube_videos
        WHERE topic_query = ? AND last_fetched_at IS NOT NULL
    """, (topic_query,)).fetchall()
    conn.close()
    return [r["video_id"] for r in rows]


def upsert_x_profile(profile, topic_query, lookup_status="found",
                     last_fetched_at=None, tweets_collected=None):
    """Record an X profile discovered for a topic (search cache / incremental dedup).

    Bookkeeping only: the tweets themselves land in the `posts` table and are
    what the analytics stages read. This table exists so re-runs skip handles
    whose timeline has already been pulled -- including private/not_found
    handles that return zero tweets but still bill a credit, which would
    otherwise be re-paid on every single run.

    First-seen metadata is preserved across updates; only discovery fields are
    refreshed. `profile` is the collector's normalized dict
    (`handle`, `display_name`, `platformUserId`, `metrics`), so this module
    stays free of API-specific field names.

    Any row written here represents a paid, completed lookup, so
    `last_fetched_at` defaults to now. Leaving it null would hide the handle
    from `get_fetched_x_handles` and silently re-bill it forever.
    """
    conn = sqlite3.connect(DB_PATH)

    metrics = profile.get("metrics") or {}
    conn.execute("""
        INSERT INTO x_profiles (
            handle, topic_query, display_name, platform_user_id,
            followers, tweets_count, lookup_status,
            first_seen_at, last_fetched_at, tweets_collected
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(handle, topic_query) DO UPDATE SET
            display_name = excluded.display_name,
            platform_user_id = excluded.platform_user_id,
            followers = excluded.followers,
            tweets_count = excluded.tweets_count,
            lookup_status = excluded.lookup_status,
            last_fetched_at = CASE
                WHEN excluded.last_fetched_at IS NOT NULL
                THEN excluded.last_fetched_at
                ELSE x_profiles.last_fetched_at
            END,
            tweets_collected = CASE
                WHEN excluded.tweets_collected IS NOT NULL
                THEN excluded.tweets_collected
                ELSE x_profiles.tweets_collected
            END
    """, (
        profile.get("handle"), topic_query, profile.get("display_name"),
        profile.get("platformUserId"), metrics.get("followers"),
        metrics.get("tweets"), lookup_status,
        datetime.now(timezone.utc).isoformat(),
        last_fetched_at or datetime.now(timezone.utc).isoformat(),
        tweets_collected
    ))

    conn.commit()
    conn.close()


def get_fetched_x_handles(topic_query):
    """Handles for a topic whose timeline has already been pulled at least once."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT handle FROM x_profiles
        WHERE topic_query = ? AND last_fetched_at IS NOT NULL
    """, (topic_query,)).fetchall()
    conn.close()
    return [r["handle"] for r in rows]


def get_x_profiles(topic_query=None):
    """Recorded X profile lookups, newest discovery first."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if topic_query is None:
        rows = conn.execute("""
            SELECT * FROM x_profiles ORDER BY first_seen_at DESC
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM x_profiles
            WHERE topic_query = ?
            ORDER BY first_seen_at DESC
        """, (topic_query,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_narratives(topic_query=None, limit=None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM narratives WHERE 1=1"
    params = []

    if topic_query:
        query += " AND topic_query = ?"
        params.append(topic_query)

    query += " ORDER BY created_at DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    create_database()
    print("Database ready:", DB_PATH)
