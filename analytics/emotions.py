import json
import re
from datetime import datetime, timezone
from transformers import pipeline


EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"
EMOTION_LABELS = [
    "anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"
]

SARCASM_PATTERNS = [
    r"\boh great\b", r"\bsure[\.\.\.]?\b", r"\byeah right\b",
    r"\bwhat a surprise\b", r"\bjust wonderful\b", r"\bthanks a lot\b",
    r"\bhow lovely\b", r"\bbrilliant[\.\.\.]+\b", r"\bgenius[\.\.\.]+\b",
    r"\boh joy\b", r"\bshocking\b", r"\bwho would have thought\b",
    r"\bimagine that\b", r"\bclearly\b", r"\bof course\b",
    r"\bnaturally\b", r"\bwow really\b", r"\bsurprise surprise\b",
]

SUPPORTIVE_PATTERNS = [
    r"\bsupport\b", r"\bgreat work\b", r"\blove this\b", r"\bagree\b",
    r"\bamazing\b", r"\bexcellent\b", r"\bfantastic\b", r"\bwell done\b",
    r"\bcongratulations\b", r"\bcongrats\b", r"\bkeep it up\b",
    r"\bthumbs up\b", r"\bappreciate\b", r"\bbravo\b", r"\bincredible\b",
]

AGAINST_PATTERNS = [
    r"\bthis is wrong\b", r"\bterrible\b", r"\bagainst\b", r"\bdisagree\b",
    r"\bhorrible\b", r"\bawful\b", r"\bdisaster\b", r"\bfail\b",
    r"\bfailure\b", r"\bworst\b", r"\brubbish\b", r"\bnonsense\b",
    r"\bwaste\b", r"\buseless\b", r"\bstupid\b", r"\bpathetic\b",
    r"\bdenounce\b", r"\boppose\b", r"\bunacceptable\b",
]

import os
import torch

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
        print(f"Loading emotion model ({'CUDA/GPU' if device == 0 else 'CPU'})...")
        _pipe = pipeline(
            "text-classification",
            model=EMOTION_MODEL,
            top_k=None,
            device=device,
            batch_size=64,
        )
    return _pipe


def detect_sarcasm(text, sentiment_label):
    if not text:
        return False

    text_lower = text.lower()
    has_pattern = any(re.search(p, text_lower) for p in SARCASM_PATTERNS)

    sentiment_mismatch = False
    positive_words = len(re.findall(
        r"\b(great|amazing|wonderful|love|excellent|fantastic|brilliant|perfect)\b",
        text_lower,
    ))
    negative_words = len(re.findall(
        r"\b(hate|terrible|awful|worst|horrible|disaster|fail|broken)\b",
        text_lower,
    ))

    if sentiment_label == "positive" and negative_words > 0:
        sentiment_mismatch = True
    elif sentiment_label == "negative" and positive_words > 0 and negative_words == 0:
        sentiment_mismatch = True

    exclamation_count = text.count("!")
    ellipsis_match = re.search(r"\.{3,}", text)
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

    emphasis = exclamation_count >= 3 or (ellipsis_match and positive_words > 0)
    caps_heavy = caps_ratio > 0.5 and len(text) > 5

    return has_pattern or sentiment_mismatch or emphasis or caps_heavy


def detect_stance(text, sentiment_label):
    if not text:
        return "neutral"

    text_lower = text.lower()

    supportive_hits = sum(1 for p in SUPPORTIVE_PATTERNS if re.search(p, text_lower))
    against_hits = sum(1 for p in AGAINST_PATTERNS if re.search(p, text_lower))

    if supportive_hits > against_hits:
        return "supportive"
    if against_hits > supportive_hits:
        return "against"

    if sentiment_label == "positive" and supportive_hits == 0 and against_hits == 0:
        return "supportive"
    if sentiment_label == "negative" and supportive_hits == 0 and against_hits == 0:
        return "against"

    return "neutral"


def analyze_emotions(posts, batch_size=64, check_db_cache=True):
    if not posts:
        return []

    cached_emotions = {}
    posts_to_analyze = []

    if check_db_cache:
        try:
            from database.db import get_emotions
            existing = get_emotions()
            existing_map = {e["post_id"]: e for e in existing}
            for p in posts:
                pid = p["id"]
                if pid in existing_map:
                    cached_emotions[pid] = existing_map[pid]
                else:
                    posts_to_analyze.append(p)
        except Exception:
            posts_to_analyze = posts
    else:
        posts_to_analyze = posts

    new_results = []
    if posts_to_analyze:
        pipe = _get_pipeline()
        texts = [p["text"][:256] for p in posts_to_analyze]
        analyzed_at = datetime.now(timezone.utc).isoformat()

        with torch.inference_mode():
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_posts = posts_to_analyze[i:i + batch_size]
                try:
                    raw_results = pipe(batch, batch_size=len(batch))
                except TypeError:
                    raw_results = pipe(batch)

                for post, raw in zip(batch_posts, raw_results):
                    emotion_scores = {}
                    for entry in raw:
                        emotion_scores[entry["label"]] = round(entry["score"], 4)

                    primary = max(emotion_scores, key=emotion_scores.get)
                    sarcasm = detect_sarcasm(post["text"], primary)
                    stance = detect_stance(post["text"], primary)

                    new_results.append({
                        "post_id": post["id"],
                        "primary_emotion": primary,
                        "emotion_json": json.dumps(emotion_scores),
                        "sarcasm_flag": 1 if sarcasm else 0,
                        "stance": stance,
                        "analyzed_at": analyzed_at,
                    })

    all_results = []
    for p in posts:
        pid = p["id"]
        if pid in cached_emotions:
            all_results.append(cached_emotions[pid])
        else:
            matching = [e for e in new_results if e["post_id"] == pid]
            if matching:
                all_results.append(matching[0])

    return all_results
