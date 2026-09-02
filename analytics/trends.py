import io
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import combinations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from normalizer.normalizer import tokenize


N_TOP_WINDOW_KEYWORDS = 10
N_TOP_ALL_TIME = 25


def _split_windows(posts, window_size_hours=24):
    """Split posts into chronological time windows for trend comparison."""
    if not posts:
        return []

    df = pd.DataFrame(posts)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.dropna(subset=["created_at"]).sort_values("created_at")

    if df.empty:
        return []

    start = df["created_at"].min()
    end = df["created_at"].max()
    window = timedelta(hours=window_size_hours)

    windows = []
    current_start = start
    while current_start <= end:
        current_end = current_start + window
        mask = (df["created_at"] >= current_start) & (df["created_at"] < current_end)
        window_posts = df[mask]
        if not window_posts.empty:
            windows.append({
                "start": current_start,
                "end": current_end,
                "posts": window_posts,
            })
        current_start = current_end
    return windows


def extract_keywords(posts, top_n=N_TOP_ALL_TIME):
    """Extract top keywords across all posts using TF-IDF scoring."""
    if not posts:
        return []

    docs = [" ".join(tokenize(p["text"])) for p in posts]
    docs = [d for d in docs if d.strip()]

    if not docs:
        return []

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=500)
    matrix = vectorizer.fit_transform(docs)
    feature_names = vectorizer.get_feature_names_out()

    scores = matrix.sum(axis=0).A1
    ranked = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
    return [(kw, float(score)) for kw, score in ranked[:top_n]]


def _count_keywords(posts):
    counter = Counter()
    for p in posts:
        for token in tokenize(p["text"]):
            counter[token] += 1
    return counter


def detect_trends(posts, topic_query, window_size_hours=24, top_n=N_TOP_WINDOW_KEYWORDS):
    """Detect rising keywords across time windows.
    Returns list of dicts ready to save into trends table.
    A keyword is 'trending' if it appears in a window with a meaningful
    frequency compared to its overall baseline."""
    if not posts:
        return []

    windows = _split_windows(posts, window_size_hours)
    if not windows:
        return []

    overall_counter = _count_keywords(posts)
    total_posts = len(posts)

    analyzed_at = datetime.now(timezone.utc).isoformat()
    trend_rows = []

    for w in windows:
        window_posts = w["posts"]
        window_counter = _count_keywords(window_posts.to_dict("records"))

        # Score: frequency in window weighted by how unusual it is vs baseline,
        # then keep only the top_n real spikes per window.
        scored = []
        for keyword, freq in window_counter.most_common(top_n * 2):
            baseline = overall_counter.get(keyword, 1)
            base_rate = baseline / max(total_posts, 1)
            window_rate = freq / max(len(window_posts), 1)

            # Spike score: how much more frequent than the baseline rate
            boost = window_rate / max(base_rate, 1e-6)
            scored.append((freq * boost, keyword, int(freq)))

        scored.sort(key=lambda x: x[0], reverse=True)

        for _, keyword, freq in scored[:top_n]:
            trend_rows.append({
                "topic_query": topic_query,
                "keyword": keyword,
                "frequency": int(freq),
                "window_start": w["start"].isoformat(),
                "window_end": w["end"].isoformat(),
                "analyzed_at": analyzed_at,
            })

    return trend_rows


def rising_terms(posts, window_size_hours=24, top_n=N_TOP_WINDOW_KEYWORDS):
    """Return the currently-rising terms: highest-frequency keywords in the
    most recent window compared to the previous window baseline."""
    if not posts:
        return []

    df = pd.DataFrame(posts)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.dropna(subset=["created_at"]).sort_values("created_at")

    if df.empty or len(df) < 2:
        return extract_keywords(posts, top_n)

    window = timedelta(hours=window_size_hours)
    last_ts = df["created_at"].max()
    prev_ts = last_ts - window

    recent = df[df["created_at"] > prev_ts]["text"].tolist()
    older = df[df["created_at"] <= prev_ts]["text"].tolist()

    recent_counter = Counter()
    for text in recent:
        recent_counter.update(tokenize(text))

    older_counter = Counter()
    for text in older:
        older_counter.update(tokenize(text))

    total_recent = max(sum(recent_counter.values()), 1)
    total_older = max(sum(older_counter.values()), 1)

    ranked = []
    for kw, freq in recent_counter.items():
        recent_rate = freq / total_recent
        older_rate = older_counter.get(kw, 0) / total_older
        boost = recent_rate / max(older_rate, 1e-6)
        ranked.append((kw, freq, boost))

    ranked.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [(kw, freq) for kw, freq, _ in ranked[:top_n]]
