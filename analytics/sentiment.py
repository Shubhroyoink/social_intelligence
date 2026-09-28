import os
from datetime import datetime, timezone
import torch
from transformers import pipeline


MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
LABELS = {"negative": "negative", "neutral": "neutral", "positive": "positive",
          "LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive"}

_pipe = None


def _get_pipeline():
    global _pipe
    if _pipe is None:
        device = 0 if torch.cuda.is_available() else -1
        if device == -1:
            try:
                torch.set_num_threads(max(1, os.cpu_count() or 4))
            except Exception:
                pass
        print(f"Loading sentiment model ({'CUDA/GPU' if device == 0 else 'CPU'})...")
        _pipe = pipeline(
            "text-classification",
            model=MODEL_NAME,
            top_k=None,
            device=device,
            batch_size=64,
        )
    return _pipe


def _map_label(model_label):
    return LABELS.get(model_label, "neutral")


def analyze_text(text):
    """Analyze a single text, returning a dict with label + confidence scores."""
    pipe = _get_pipeline()
    with torch.inference_mode():
        result = pipe(text[:256])[0]

    scores = {}
    total = 0.0
    for entry in result:
        label = _map_label(entry["label"])
        scores[label] = entry["score"]
        total += entry["score"]

    if total == 0:
        total = 1.0
    # normalize to sum 1
    for k in scores.keys():
        scores[k] /= total

    return {
        "label": max(scores, key=lambda k: scores[k]),
        "positive_score": scores.get("positive", 0.0),
        "neutral_score": scores.get("neutral", 0.0),
        "negative_score": scores.get("negative", 0.0),
    }


def analyze_posts(posts, batch_size=64, check_db_cache=True):
    """Run sentiment analysis on posts with DB caching and GPU/batch acceleration.
    Returns list of dicts ready to save into sentiments table."""
    if not posts:
        return []

    cached_sentiments = {}
    posts_to_analyze = []

    if check_db_cache:
        try:
            from database.db import get_sentiments
            existing = get_sentiments()
            existing_map = {s["post_id"]: s for s in existing}
            for p in posts:
                pid = p["id"]
                if pid in existing_map:
                    cached_sentiments[pid] = existing_map[pid]
                else:
                    posts_to_analyze.append(p)
        except Exception:
            posts_to_analyze = posts
    else:
        posts_to_analyze = posts

    new_sentiments = []
    if posts_to_analyze:
        pipe = _get_pipeline()
        texts = [p["text"][:256] for p in posts_to_analyze]
        analyzed_at = datetime.now(timezone.utc).isoformat()

        with torch.inference_mode():
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                try:
                    results = pipe(batch, batch_size=len(batch))
                except TypeError:
                    results = pipe(batch)
                for post, result in zip(posts_to_analyze[i:i + batch_size], results):
                    scores = {}
                    total = 0.0
                    for entry in result:
                        label = _map_label(entry["label"])
                        scores[label] = entry["score"]
                        total += entry["score"]

                    if total == 0:
                        total = 1.0
                    for k in list(scores.keys()):
                        scores[k] /= total

                    new_sentiments.append({
                        "post_id": post["id"],
                        "platform": post.get("platform"),
                        "created_at": post.get("created_at"),
                        "topic_query": post.get("topic_query"),
                        "label": max(scores, key=lambda k: scores[k]),
                        "positive_score": scores.get("positive", 0.0),
                        "neutral_score": scores.get("neutral", 0.0),
                        "negative_score": scores.get("negative", 0.0),
                        "analyzed_at": analyzed_at,
                    })

    all_results = []
    for p in posts:
        pid = p["id"]
        if pid in cached_sentiments:
            all_results.append(cached_sentiments[pid])
        else:
            matching = [s for s in new_sentiments if s["post_id"] == pid]
            if matching:
                all_results.append(matching[0])

    return all_results
