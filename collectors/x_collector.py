import os
import requests
from datetime import datetime, timezone
from ntscraper import Nitter

from normalizer.normalizer import dedupe, normalize_posts, normalize_timestamp, stable_post_id


DEFAULT_QUERY_LIMIT = 50


def _collect_x_api(query, topic_query, limit=DEFAULT_QUERY_LIMIT):
    """Collect tweets via official Twitter/X API v2 if TWITTER_BEARER_TOKEN is set."""
    token = os.environ.get("TWITTER_BEARER_TOKEN") or os.environ.get("X_BEARER_TOKEN")
    if not token:
        return None

    try:
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "query": query,
            "max_results": min(100, max(10, limit)),
            "tweet.fields": "created_at,public_metrics,author_id,conversation_id",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        res = requests.get(url, headers=headers, params=params, timeout=5.0)
        if res.status_code != 200:
            return None

        data = res.json()
        users_map = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        collected = []
        for t in data.get("data", []):
            text = t.get("text", "")
            user = users_map.get(t.get("author_id"), {})
            metrics = t.get("public_metrics", {})
            collected.append({
                "id": stable_post_id("x", t.get("id"), text),
                "platform": "x",
                "author_id": t.get("author_id"),
                "author_handle": f"@{user.get('username')}" if user.get("username") else None,
                "text": text,
                "created_at": normalize_timestamp(t.get("created_at")),
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "parent_id": None,
                "topic_query": topic_query,
                "reactions": metrics.get("like_count", 0),
                "shares": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "views": metrics.get("impression_count", None),
            })
        return collected
    except Exception as e:
        print(f"[X API v2] Warning: {e}")
        return None


def collect_x_search(query, topic_query, limit=DEFAULT_QUERY_LIMIT):
    """Scrape X/Twitter search results (Official API v2 or fast scraper fallback).
    Returns a list of dicts in the posts schema.
    """
    # 1. Try official API v2 first if token available
    api_results = _collect_x_api(query, topic_query, limit=limit)
    if api_results is not None:
        return api_results

    # 2. If no Twitter API token is configured, skip immediately to prevent 5-minute Nitter network timeouts
    token = os.environ.get("TWITTER_BEARER_TOKEN") or os.environ.get("X_BEARER_TOKEN")
    if not token:
        print(f"[X collector] Notice: TWITTER_BEARER_TOKEN not set in .env. Skipping X query '{query}'.")
        return []

    collected = []
    try:
        scraper = Nitter(log_level=0)
        tweets = scraper.get_tweets(query, mode="term", number=min(limit, 10))
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
    token = os.environ.get("TWITTER_BEARER_TOKEN") or os.environ.get("X_BEARER_TOKEN")
    if not token:
        print(f"[X collector] Notice: TWITTER_BEARER_TOKEN not set. Skipping profile '{handle}'.")
        return []

    scraper = Nitter(log_level=0)
    collected = []

    try:
        tweets = scraper.get_tweets(handle, mode="user", number=min(limit, 10))
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
