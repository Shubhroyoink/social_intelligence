from datetime import datetime, timezone
from transformers import pipeline


MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
LABELS = {"LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive"}

_pipe = None


def _get_pipeline():
    global _pipe
    if _pipe is None:
        print("Loading sentiment model...")
        _pipe = pipeline(
            "text-classification",
            model=MODEL_NAME,
            top_k=None,
        )
    return _pipe


def _map_label(model_label):
    return LABELS.get(model_label, "neutral")


def analyze_text(text):
    """Analyze a single text, returning a dict with label + confidence scores."""
    pipe = _get_pipeline()
    result = pipe(text[:512])[0]

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


def analyze_posts(posts, batch_size=32):
    """Run sentiment analysis on a batch of posts.
    Returns list of dicts ready to save into sentiments table."""
    if not posts:
        return []

    pipe = _get_pipeline()
    texts = [p["text"][:512] for p in posts]

    sentiments = []
    analyzed_at = datetime.now(timezone.utc).isoformat()

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        results = pipe(batch)
        for post, result in zip(posts[i:i + batch_size], results):
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

            sentiments.append({
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

    return sentiments
