import re
from collections import Counter
from datetime import datetime, timezone


def clean_text(text):
    """Clean raw post text for analysis: strip URLs, mentions, hashtag symbols,
    excessive whitespace and punctuation, while preserving meaningful content."""
    if not text:
        return ""

    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def normalize_timestamp(value):
    """Parse a timestamp into ISO 8601 UTC string regardless of input format."""
    if value is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except ValueError:
            pass
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return parsed.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return datetime.now(timezone.utc).isoformat()

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    return datetime.now(timezone.utc).isoformat()


def normalize_posts(posts):
    """Normalize a list of collected raw posts into a clean, uniform format."""
    normalized = []
    for p in posts:
        text = clean_text(p.get("text", "") or "")
        if not text:
            continue

        normalized.append({
            "id": p["id"],
            "platform": p.get("platform") or "unknown",
            "author_id": p.get("author_id"),
            "author_handle": p.get("author_handle"),
            "text": text,
            "created_at": normalize_timestamp(p.get("created_at")),
            "collected_at": p.get("collected_at") or datetime.now(timezone.utc).isoformat(),
            "parent_id": p.get("parent_id"),
            "topic_query": p.get("topic_query"),
            "reactions": int(p.get("reactions") or 0),
            "shares": int(p.get("shares") or 0),
            "replies": p.get("replies"),
            "views": p.get("views"),
        })
    return normalized


def dedupe(posts, key="id"):
    """Remove duplicate posts by key, keeping the first occurrence."""
    seen = set()
    unique = []
    for p in posts:
        k = p.get(key)
        if k not in seen:
            seen.add(k)
            unique.append(p)
    return unique


def tokenize(text):
    """Split text into lowercase word tokens, dropping stopwords and short words."""
    stopwords = {
        "the", "a", "an", "and", "or", "but", "of", "in", "on", "for",
        "to", "with", "at", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "can", "could", "should", "may", "might", "must",
        "this", "that", "these", "those", "it", "its", "i", "you", "he",
        "she", "we", "they", "them", "their", "there", "what", "which",
        "who", "whom", "how", "when", "where", "why", "not", "no", "yes",
        "more", "most", "very", "too", "so", "such", "just", "about",
        "into", "out", "over", "under", "up", "down", "as", "than", "then",
        "also", "even", "only", "some", "any", "all", "both", "each",
        "few", "several", "one", "two", "three", "new", "our", "your",
        "their", "his", "her", "its", "get", "got", "make", "made",
        "like", "know", "want", "need", "use", "used", "using", "say",
        "said", "via", "now", "get", "here", "see", "go", "come",
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return [w for w in words if w not in stopwords]
