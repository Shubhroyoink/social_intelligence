from datetime import datetime, timezone
from ntscraper import Nitter

from normalizer.normalizer import dedupe, normalize_posts, normalize_timestamp, stable_post_id


DEFAULT_QUERY_LIMIT = 50


def collect_x_search(query, topic_query, limit=DEFAULT_QUERY_LIMIT):
    """Scrape X/Twitter search results via Nitter (no API keys required).
    Returns a list of dicts in the posts schema.
    """
    scraper = Nitter()
    collected = []

    try:
        tweets = scraper.get_tweets(query, mode="term", number=limit)
        for t in tweets.get("tweets", []):
            text = t.get("text") or ""
            if not text.strip():
                continue

            created_at_raw = t.get("timestamp") or t.get("date")
            created_at = normalize_timestamp(created_at_raw)

            collected.append({
                "id": stable_post_id("x", t.get("id"), text),
                "platform": "x",
                "author_id": t.get("user", {}).get("id"),
                "author_handle": t.get("user", {}).get("name") or t.get("user", {}).get("username"),
                "text": text,
                "created_at": created_at,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "parent_id": None,
                "topic_query": topic_query,
                "reactions": t.get("likes") or t.get("stats", {}).get("likes", 0),
                "shares": t.get("retweets") or t.get("stats", {}).get("retweets", 0),
                "replies": t.get("replies") or t.get("stats", {}).get("comments", 0),
                "views": t.get("views") or None,
            })
    except Exception as e:
        print(f"[X collector] Warning: {e}")

    return collected


def collect_x_profile(handle, topic_query, limit=DEFAULT_QUERY_LIMIT):
    """Scrape recent tweets from a specific user profile handle."""
    scraper = Nitter()
    collected = []

    try:
        tweets = scraper.get_tweets(handle, mode="user", number=limit)
        for t in tweets.get("tweets", []):
            text = t.get("text") or ""
            if not text.strip():
                continue

            created_at_raw = t.get("timestamp") or t.get("date")
            created_at = normalize_timestamp(created_at_raw)

            collected.append({
                "id": stable_post_id("x", t.get("id"), text),
                "platform": "x",
                "author_id": t.get("user", {}).get("id"),
                "author_handle": handle,
                "text": text,
                "created_at": created_at,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "parent_id": None,
                "topic_query": topic_query,
                "reactions": t.get("likes") or t.get("stats", {}).get("likes", 0),
                "shares": t.get("retweets") or t.get("stats", {}).get("retweets", 0),
                "replies": t.get("replies") or t.get("stats", {}).get("comments", 0),
                "views": t.get("views") or None,
            })
    except Exception as e:
        print(f"[X collector] Warning: {e}")

    return collected


if __name__ == "__main__":
    from database.db import create_database, save_posts

    print("Starting X collector...")
    create_database()

    queries = [
        ("AI Agents", "AI Agents"),
        ("artificial intelligence", "AI Agents"),
    ]

    all_posts = []
    for query, topic in queries:
        print(f"  Searching X for '{query}'...")
        posts = collect_x_search(query, topic, limit=30)
        print(f"  Collected {len(posts)} tweets")
        all_posts.extend(posts)

    print(f"Total collected: {len(all_posts)}")
    save_posts(dedupe(normalize_posts(all_posts), key="id"))
    print("Saved to social.db")
