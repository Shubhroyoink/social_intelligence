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

_pipe = None


def _get_pipeline():
    global _pipe
    if _pipe is None:
        print("Loading emotion model...")
        _pipe = pipeline(
            "text-classification",
            model=EMOTION_MODEL,
            top_k=None,
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


def analyze_emotions(posts, batch_size=32):
    if not posts:
        return []

    pipe = _get_pipeline()
    texts = [p["text"][:512] for p in posts]
    analyzed_at = datetime.now(timezone.utc).isoformat()
    results = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_posts = posts[i:i + batch_size]
        raw_results = pipe(batch)

        for post, raw in zip(batch_posts, raw_results):
            emotion_scores = {}
            for entry in raw:
                emotion_scores[entry["label"]] = round(entry["score"], 4)

            primary = max(emotion_scores, key=emotion_scores.get)
            sarcasm = detect_sarcasm(post["text"], primary)
            stance = detect_stance(post["text"], primary)

            results.append({
                "post_id": post["id"],
                "primary_emotion": primary,
                "emotion_json": json.dumps(emotion_scores),
                "sarcasm_flag": 1 if sarcasm else 0,
                "stance": stance,
                "analyzed_at": analyzed_at,
            })

    return results
