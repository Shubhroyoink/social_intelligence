import json
import os
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from normalizer.normalizer import normalize_timestamp, stable_post_id

load_dotenv()

ALLOWED_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
ALLOWED_URL_SCHEMES = {"http", "https"}

API_BASE = "https://www.googleapis.com/youtube/v3"

ENV_KEY_NAME = "YOUTUBE_API_KEY"

# Quota bookkeeping (YouTube Data API v3: 10,000 units/day).
QUOTA_DAILY_LIMIT = 10000
SEARCH_COST = 100  # search.list costs a flat 100 units per call
COMMENT_BASE_COST = 1  # commentThreads.list: 1 unit per call + 1 per result

LEDGER_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "youtube_quota.json")
)


class YouTubeQuotaExceededError(Exception):
    """Raised when the YouTube daily quota (10k units) is exhausted."""


def _today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_ledger():
    """Load the quota ledger, resetting the counter when UTC day changes."""
    try:
        with open(LEDGER_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("date") != _today_utc():
            data = {"date": _today_utc(), "used": 0}
    except (OSError, ValueError):
        data = {"date": _today_utc(), "used": 0}
    return data


def _save_ledger(data):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def quota_remaining():
    """Units left for today before the API rejects calls."""
    return max(0, QUOTA_DAILY_LIMIT - _load_ledger()["used"])


def spend_quota(units):
    """Record API units used (UTC day reset handled on read)."""
    data = _load_ledger()
    data["used"] += max(0, int(units))
    _save_ledger(data)


def _raise_if_quota_exceeded(resp):
    try:
        errors = resp.json().get("error", {}).get("errors", [])
    except ValueError:
        errors = []
    if any(e.get("reason") == "quotaExceeded" for e in errors):
        raise YouTubeQuotaExceededError(
            "YouTube daily quota (10,000 units) exceeded"
        )


def _get_api_key():
    """Return the YouTube Data API key from the environment (.env)."""
    key = os.environ.get(ENV_KEY_NAME)
    if not key:
        raise RuntimeError(
            "YouTube Data API key missing. Set YOUTUBE_API_KEY in your "
            ".env file (see .env.example)."
        )
    return key


def _validate_youtube_url(video_url):
    """Reject anything other than http(s) YouTube links before handling it.

    Guards against SSRF/local-file probes and ensures we can extract a
    video ID before hitting the YouTube Data API.
    """
    parsed = urlparse(video_url)
    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.netloc.lower() not in ALLOWED_YOUTUBE_HOSTS:
        raise ValueError(f"Unsupported video host: {parsed.netloc!r}")


def _extract_video_id(video_url):
    """Extract a YouTube video ID from a watch, embed, shorts or youtu.be URL."""
    parsed = urlparse(video_url)

    video_id = None
    if parsed.netloc.lower() in {"youtu.be"}:
        video_id = parsed.path.strip("/")
    elif parsed.netloc.lower() in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        path = parsed.path
        if path.startswith("/embed/"):
            video_id = path.split("/")[2]
        elif path.startswith("/shorts/"):
            video_id = path.split("/")[2]
        elif path.startswith("/watch"):
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif path.startswith("/live/"):
            video_id = path.split("/")[2]
        else:
            video_id = parse_qs(parsed.query).get("v", [None])[0]

    if not video_id:
        raise ValueError(f"Could not extract a video ID from URL: {video_url!r}")
    return video_id


def _fetch_comment_threads(api_key, video_id, limit):
    """Fetch top-level comment threads (with replies) via the Data API.

    Returns a list of raw comment dicts in a uniform shape and handles
    pagination until the requested limit is reached. Each API response is
    charged to the quota ledger (1 unit + 1 per result).
    """
    import requests

    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(100, limit),
        "key": api_key,
        "textFormat": "plainText",
        "order": "relevance",
    }

    page_token = None
    comments = []

    while len(comments) < limit:
        if page_token:
            params["pageToken"] = page_token
        else:
            params.pop("pageToken", None)

        resp = requests.get(f"{API_BASE}/commentThreads", params=params, timeout=30)
        if resp.status_code == 403:
            _raise_if_quota_exceeded(resp)
        resp.raise_for_status()
        data = resp.json()

        spend_quota(COMMENT_BASE_COST + len(data.get("items", [])))

        for item in data.get("items", []):
            if len(comments) >= limit:
                break

            snippet = item.get("snippet", {})
            top = snippet.get("topLevelComment", {}).get("snippet", {})

            comment_id = item.get("id")
            text = top.get("textDisplay", "")
            if not text.strip():
                continue

            comments.append({
                "id": comment_id,
                "text": text,
                "author": top.get("authorDisplayName") or "unknown",
                "author_id": top.get("authorChannelId", {}).get("value")
                if top.get("authorChannelId") else "unknown",
                "created_at": top.get("publishedAt") or "",
                "like_count": top.get("likeCount") or 0,
                "reply_count": snippet.get("totalReplyCount") or 0,
                "parent_id": None,
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return comments


def search_videos(query, max_results=5, key=None):
    """Find videos matching a topic query via the search.list endpoint.

    Costs a flat 100 quota units per call regardless of result count.
    Returns flattened video dicts:
        {video_id, title, channel, description, published_at}
    """
    import requests

    key = key or _get_api_key()
    if max_results <= 0:
        return []

    params = {
        "part": "snippet",
        "q": query,
        "maxResults": min(max_results, 50),
        "type": "video",
        "key": key,
    }

    resp = requests.get(f"{API_BASE}/search", params=params, timeout=30)
    if resp.status_code == 403:
        _raise_if_quota_exceeded(resp)
    resp.raise_for_status()
    data = resp.json()

    spend_quota(SEARCH_COST)

    videos = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet", {})
        videos.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "description": snippet.get("description", ""),
            "published_at": normalize_timestamp(snippet.get("publishedAt") or ""),
        })

    return videos


def estimate_collect_topic_units(max_videos, comments_per_video):
    """Rough unit cost of a topic run: 1 search + N comment extractions."""
    return SEARCH_COST + int(max_videos) * (
        COMMENT_BASE_COST + max(1, int(comments_per_video))
    )


def _collect_comments_for_video(video_id, topic_query, limit=100, api_key=None):
    """Build uniform posts for one video's comments (shared by URL & search)."""
    api_key = api_key or _get_api_key()

    try:
        comments = _fetch_comment_threads(api_key, video_id, limit)
    except YouTubeQuotaExceededError:
        raise
    except Exception as e:
        print(f"[YouTube collector] Failed to fetch comments for video {video_id}: {e}")
        return []

    if not comments:
        print("[YouTube collector] No comments found (video may have comments disabled)")
        return []

    collected = []
    for c in comments:
        collected.append({
            "id": stable_post_id("yt", c["id"], c["text"]),
            "platform": "youtube",
            "author_id": str(c["author_id"]),
            "author_handle": c["author"],
            "text": c["text"],
            "created_at": normalize_timestamp(c["created_at"]),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "parent_id": f"yt_{c['parent_id']}" if c.get("parent_id") else None,
            "topic_query": topic_query,
            "reactions": c["like_count"],
            "shares": 0,
            "replies": c["reply_count"],
            "views": None,
        })

    return collected


def collect_youtube_comments(video_url, topic_query, limit=100):
    """Extract comments from a YouTube video using the official Data API v3.

    Requires a YOUTUBE_API_KEY in the .env file. Uses the commentThreads
    endpoint (top-level comments plus reply counts) with pagination.

    Args:
        video_url: Full YouTube video URL or watch/shorts/embed URL.
        topic_query: Topic tag to attach to collected posts.
        limit: Maximum number of top-level comments to retrieve.

    Returns:
        List of post dicts in the uniform schema.
    """
    _validate_youtube_url(video_url)
    video_id = _extract_video_id(video_url)
    return _collect_comments_for_video(video_id, topic_query, limit=limit)


def collect_youtube_topic(
    topic_query,
    max_videos=5,
    comments_per_video=100,
    refresh=False,
    budget_units=2000,
    api_key=None,
):
    """Discover videos for a topic, then extract their comments incrementally.

    Flow:
        1. Refuse the run if it cannot afford its estimated quota cost
           (respecting both the per-run budget cap and the remaining daily quota).
        2. search.list for the topic (100 units) -> candidate videos.
        3. Consult the youtube_videos cache in social.db: videos whose comments
           were already extracted for this topic are skipped unless refresh=True
           (this is what makes re-runs cheap instead of re-fetching everything).
        4. Fetch comments for the new videos, mark them as fetched, and return
           the posts in the uniform schema.

    Args:
        topic_query: Search query used to discover videos.
        max_videos: Videos to consider per topic run.
        comments_per_video: Top-level comments to pull per video.
        refresh: Force re-extraction of already-cached videos.
        budget_units: Hard cap on the units this single run may estimate.
        api_key: Optional Data API key (falls back to YOUTUBE_API_KEY env).

    Returns:
        List of post dicts (uniform schema) tagged with topic_query.
    """
    api_key = api_key or _get_api_key()

    estimated = estimate_collect_topic_units(max_videos, comments_per_video)
    available = min(budget_units, quota_remaining())
    if estimated > available:
        print(
            f"[YouTube] Skipping topic '{topic_query}': estimated {estimated} units "
            f"> available {available} (budget cap {budget_units}, "
            f"remaining today {quota_remaining()})."
        )
        return []

    print(
        f"[YouTube] Searching up to {max_videos} videos for '{topic_query}' "
        f"(est. {estimated} units)..."
    )
    try:
        videos = search_videos(topic_query, max_results=max_videos, key=api_key)
    except YouTubeQuotaExceededError:
        print("[YouTube] Daily quota exhausted during search; stopping.")
        return []
    except Exception as e:
        print(f"[YouTube] Video search failed for '{topic_query}': {e}")
        return []

    if not videos:
        print(f"[YouTube] No videos found for '{topic_query}'; skipped.")
        return []

    from database.db import get_fetched_youtube_video_ids, upsert_youtube_video

    fetched_ids = set(get_fetched_youtube_video_ids(topic_query))
    to_fetch = []
    for video in videos:
        upsert_youtube_video(video, topic_query)
        if refresh or video["video_id"] not in fetched_ids:
            to_fetch.append(video)

    already_cached = len(videos) - len(to_fetch)
    print(
        f"[YouTube] {len(to_fetch)} new video(s) to extract; "
        f"{already_cached} already cached (skipped)."
    )

    all_posts = []
    for video in to_fetch:
        fetched_ok = True
        try:
            posts = _collect_comments_for_video(
                video["video_id"], topic_query,
                limit=comments_per_video, api_key=api_key,
            )
        except YouTubeQuotaExceededError:
            print("[YouTube] Daily quota exhausted during comment fetch; stopping.")
            break
        except Exception as e:
            title = (video.get("title") or "")[:40]
            print(f"[YouTube] Comment fetch failed for {video['video_id']} "
                  f"({title!r}): {e}")
            posts = []
            fetched_ok = False

        all_posts.extend(posts)
        if fetched_ok:
            upsert_youtube_video(
                video, topic_query,
                last_fetched_at=datetime.now(timezone.utc).isoformat(),
                comments_count=len(posts),
            )

    return all_posts


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    posts = collect_youtube_comments(url, topic_query="AI Agents", limit=20)
    print(f"Collected {len(posts)} YouTube comments")
    for p in posts[:5]:
        print(f"  [{p['author_handle']}] {p['text'][:80]}...")
