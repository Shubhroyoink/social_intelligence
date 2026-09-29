import hashlib
import json
import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

from normalizer.normalizer import dedupe, normalize_posts, normalize_timestamp, stable_post_id

load_dotenv()

DEFAULT_QUERY_LIMIT = 50
SOCIALFETCH_API_URL = "https://api.socialfetch.dev/v1/twitter/search"


def _get_redis_client():
    """Retrieve Redis client for query caching if available."""
    try:
        from task_queue.job_manager import get_job_manager
        jm = get_job_manager()
        if jm and jm.is_redis_active and jm._redis_client:
            return jm._redis_client
    except Exception:
        pass
    return None


def _collect_socialfetch_api(query, topic_query, limit=DEFAULT_QUERY_LIMIT):
    """Collect tweets via SocialFetch API (https://socialfetch.dev).
    Fast, reliable live Twitter data without managing browser scrapers.
    """
    api_key = os.environ.get("SOCIALFETCH_API_KEY")
    if not api_key or not api_key.strip():
        return None

    try:
        headers = {
            "x-api-key": api_key.strip(),
            "Accept": "application/json",
            "User-Agent": "SocialIntelligencePipeline/1.0",
        }
        params = {
            "query": query,
            "section": "latest",
        }

        resp = requests.get(SOCIALFETCH_API_URL, headers=headers, params=params, timeout=10.0)
        
        if resp.status_code == 401 or resp.status_code == 403:
            print(f"[SocialFetch API] Auth error (Status {resp.status_code}): Invalid or expired API key.")
            return None
        elif resp.status_code != 200:
            print(f"[SocialFetch API] Search returned HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        body = resp.json()
        raw_items = []
        data_block = body.get("data")

        if isinstance(data_block, list):
            raw_items = data_block
        elif isinstance(data_block, dict):
            raw_items = (
                data_block.get("tweets")
                or data_block.get("posts")
                or data_block.get("results")
                or data_block.get("items")
                or []
            )
        elif "tweets" in body:
            raw_items = body.get("tweets") or []
        elif "posts" in body:
            raw_items = body.get("posts") or []

        collected = []
        for item in raw_items[:limit]:
            if not isinstance(item, dict):
                continue
            
            raw_id = item.get("id") or item.get("tweet_id") or item.get("id_str")
            text = (
                item.get("text")
                or item.get("content")
                or item.get("full_text")
                or item.get("body")
                or ""
            )
            if not text.strip():
                continue

            author = item.get("author") or item.get("user") or {}
            author_id = (
                str(item.get("author_id"))
                if item.get("author_id")
                else str(author.get("id") or author.get("id_str") or "")
            )
            handle = (
                author.get("username")
                or author.get("handle")
                or author.get("screen_name")
                or item.get("author_handle")
                or item.get("username")
            )
            author_handle = f"@{handle.lstrip('@')}" if handle else None

            metrics = item.get("public_metrics") or item.get("stats") or item.get("metrics") or {}
            reactions = (
                metrics.get("like_count")
                or item.get("likes")
                or item.get("favorite_count")
                or 0
            )
            shares = (
                metrics.get("retweet_count")
                or item.get("retweets")
                or item.get("repost_count")
                or 0
            )
            replies = (
                metrics.get("reply_count")
                or item.get("replies")
                or 0
            )
            views = (
                metrics.get("impression_count")
                or item.get("views")
                or None
            )

            created_raw = item.get("created_at") or item.get("timestamp") or item.get("date")
            created_at = normalize_timestamp(created_raw)

            collected.append({
                "id": stable_post_id("x", raw_id, text),
                "platform": "x",
                "author_id": author_id or None,
                "author_handle": author_handle,
                "text": text,
                "created_at": created_at,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "parent_id": None,
                "topic_query": topic_query,
                "reactions": int(reactions) if reactions else 0,
                "shares": int(shares) if shares else 0,
                "replies": int(replies) if replies else 0,
                "views": int(views) if views is not None else None,
            })

        print(f"[SocialFetch API] Successfully fetched {len(collected)} tweets for query '{query}'")
        return collected
    except Exception as e:
        print(f"[SocialFetch API] Warning during fetch for '{query}': {e}")
        return None


def _collect_x_api(query, topic_query, limit=DEFAULT_QUERY_LIMIT):
    """Collect tweets via official Twitter/X API v2 if TWITTER_BEARER_TOKEN is set."""
    token = os.environ.get("TWITTER_BEARER_TOKEN") or os.environ.get("X_BEARER_TOKEN")
    if not token or not token.strip():
        return None

    try:
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {token.strip()}"}
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
        print(f"[Twitter API v2] Successfully fetched {len(collected)} tweets for query '{query}'")
        return collected
    except Exception as e:
        print(f"[X API v2] Warning: {e}")
        return None


def collect_x_search(query, topic_query, limit=DEFAULT_QUERY_LIMIT, use_cache=True):
    """Scrape X/Twitter search results with multi-tier failover:
    1. Check Redis Cache (TTL 1 hour)
    2. Try SocialFetch API (SOCIALFETCH_API_KEY)
    3. Try Official Twitter API v2 (TWITTER_BEARER_TOKEN)
    4. Fast fallback / skip if no tokens configured
    """
    # 0. Redis Cache Check
    cache_key = None
    r_client = _get_redis_client() if use_cache else None
    if r_client:
        try:
            q_hash = hashlib.md5(f"{query}:{topic_query}:{limit}".encode()).hexdigest()
            cache_key = f"cache:x_search:{q_hash}"
            cached_val = r_client.get(cache_key)
            if cached_val:
                posts = json.loads(cached_val)
                print(f"[X collector] Retrieved {len(posts)} cached tweets from Redis for query '{query}'")
                return posts
        except Exception:
            pass

    # 1. Try SocialFetch API
    sf_results = _collect_socialfetch_api(query, topic_query, limit=limit)
    if sf_results is not None:
        if r_client and cache_key and sf_results:
            try:
                r_client.setex(cache_key, 3600, json.dumps(sf_results))  # Cache for 1 hour
            except Exception:
                pass
        return sf_results

    # 2. Try Official Twitter API v2
    api_results = _collect_x_api(query, topic_query, limit=limit)
    if api_results is not None:
        if r_client and cache_key and api_results:
            try:
                r_client.setex(cache_key, 3600, json.dumps(api_results))
            except Exception:
                pass
        return api_results

    # 3. If no Twitter tokens are configured, skip cleanly
    has_token = bool(
        os.environ.get("SOCIALFETCH_API_KEY")
        or os.environ.get("TWITTER_BEARER_TOKEN")
        or os.environ.get("X_BEARER_TOKEN")
    )
    if not has_token:
        print(f"[X collector] Notice: Neither SOCIALFETCH_API_KEY nor TWITTER_BEARER_TOKEN configured in .env. Skipping X query '{query}'.")
        return []

    # 4. Optional Nitter scraper fallback
    collected = []
    try:
        from ntscraper import Nitter
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
    clean_handle = handle.lstrip("@")
    return collect_x_search(f"from:{clean_handle}", topic_query, limit=limit)


if __name__ == "__main__":
    from database.db import create_database, save_posts

    print("Starting X collector test...")
    create_database()

    queries = [
        ("AI Agents", "AI Agents"),
    ]

    all_posts = []
    for query, topic in queries:
        print(f"  Searching X for '{query}'...")
        posts = collect_x_search(query, topic, limit=20)
        print(f"  Collected {len(posts)} tweets")
        all_posts.extend(posts)

    print(f"Total collected: {len(all_posts)}")
    if all_posts:
        save_posts(dedupe(normalize_posts(all_posts), key="id"))
        print("Saved to social.db")

