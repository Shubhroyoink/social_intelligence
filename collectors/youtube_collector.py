import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from normalizer.normalizer import normalize_timestamp, stable_post_id


ALLOWED_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
ALLOWED_URL_SCHEMES = {"http", "https"}


def _validate_youtube_url(video_url):
    """Reject anything other than http(s) YouTube links before handing it to yt-dlp.

    yt-dlp will happily process local paths and other schemes, making an
    unvalidated user-supplied URL an SSRF/local-file probe vector.
    """
    parsed = urlparse(video_url)
    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.netloc.lower() not in ALLOWED_YOUTUBE_HOSTS:
        raise ValueError(f"Unsupported video host: {parsed.netloc!r}")


def _js_runtime_available():
    from shutil import which

    if which("deno") or which("node"):
        return True
    return os.path.exists(os.path.join(os.path.expanduser("~"), ".deno", "bin", "deno.exe"))


def collect_youtube_comments(video_url, topic_query, limit=100):
    """Extract comments from a YouTube video using yt-dlp (no API key needed).

    Notes:
        - YouTube now requires a JavaScript runtime to extract comments
          (anti-bot challenge). yt-dlp uses deno or node when available.
          If no JS runtime is found, comment extraction is skipped and
          a warning is printed — install deno (https://deno.land) to enable it.

    Args:
        video_url: Full YouTube video URL or video ID.
        topic_query: Topic tag to attach to collected posts.
        limit: Maximum number of comments to retrieve.

    Returns:
        List of post dicts in the uniform schema.
    """
    _validate_youtube_url(video_url)

    try:
        import yt_dlp
    except ImportError:
        print("[YouTube collector] yt-dlp not installed. Run: pip install yt-dlp")
        return []

    runtime = _js_runtime_available()
    if not runtime:
        print("[YouTube collector] WARNING: no JavaScript runtime (deno/node) found. "
              "YouTube comment extraction requires one. Install deno: https://deno.land")

    collected = []

    ydl_opts = {
        "skip_download": True,
        "getcomments": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {"youtube": {"max_comments": [str(limit), "all", "all"]}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
    except Exception as e:
        print(f"[YouTube collector] Failed to extract video: {e}")
        return []

    comments = info.get("comments") or []
    if not comments:
        print("[YouTube collector] No comments found (video may have comments disabled)")
        return []

    for c in comments[:limit]:
        text = c.get("text") or ""
        if not text.strip():
            continue

        author = c.get("author") or "unknown"
        author_id = c.get("author_id") or c.get("author") or "unknown"
        created_at = normalize_timestamp(c.get("timestamp"))

        collected.append({
            "id": stable_post_id("yt", c.get("id"), text),
            "platform": "youtube",
            "author_id": str(author_id),
            "author_handle": author,
            "text": text,
            "created_at": created_at,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "parent_id": f"yt_{c.get('parent', '')}" if c.get("parent") else None,
            "topic_query": topic_query,
            "reactions": c.get("like_count") or 0,
            "shares": 0,
            "replies": c.get("reply_count") or 0,
            "views": None,
        })

    return collected


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    posts = collect_youtube_comments(url, topic_query="AI Agents", limit=20)
    print(f"Collected {len(posts)} YouTube comments")
    for p in posts[:5]:
        print(f"  [{p['author_handle']}] {p['text'][:80]}...")