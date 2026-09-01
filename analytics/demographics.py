import json
import re
from datetime import datetime, timezone


PROFESSIONAL_INTERESTS = {
    "technology": [
        "software", "developer", "programming", "code", "api", "cloud",
        "saas", "tech", "startup", "engineering", "devops", "cybersecurity",
        "blockchain", "web3", "data", "algorithm", "infrastructure", "database",
    ],
    "ai_ml": [
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "neural network", "llm", "gpt", "transformer", "nlp", "model",
        "training", "inference", "diffusion", "generative", "agent", "rag",
        "fine-tuning", "embedding", "vector", "prompt",
    ],
    "finance": [
        "investing", "stock", "crypto", "bitcoin", "ethereum", "defi",
        "trading", "portfolio", "market", "financial", "banking", "fintech",
        "wealth", "fund", "etf", "trader", "bull", "bear",
    ],
    "healthcare": [
        "health", "medical", "doctor", "patient", "clinical", "pharma",
        "biotech", "diagnosis", "therapy", "wellness", "mental health",
        "healthcare", "hospital", "drug", "fda",
    ],
    "education": [
        "education", "learning", "teaching", "course", "university",
        "student", "professor", "academic", "research", "curriculum",
        "tutorial", "training", "mentor", "school", "classroom",
    ],
    "politics": [
        "politics", "election", "government", "policy", "democrat",
        "republican", "congress", "senate", "vote", "legislation",
        "campaign", "political", "diplomat", "regulation",
    ],
    "marketing": [
        "marketing", "seo", "content", "brand", "social media",
        "advertising", "campaign", "engagement", "conversion",
        "analytics", "growth", "funnel", "influencer", "viral",
    ],
    "science": [
        "science", "physics", "chemistry", "biology", "research",
        "experiment", "discovery", "journal", "peer review",
        "hypothesis", "quantum", "genetic", "climate", "space",
    ],
    "gaming": [
        "gaming", "game", "esports", "streamer", "twitch",
        "playstation", "xbox", "nintendo", "pc gaming", "fps",
        "rpg", "mmo", "virtual reality", "vr", "metaverse",
    ],
    "entrepreneurship": [
        "entrepreneur", "founder", "startup", "seed", "series a",
        "venture", "pitch", "mvp", "bootstrapped", "yc",
        "accelerator", "fundraising", "pivot", "scale",
    ],
    "environment": [
        "climate", "sustainability", "renewable", "solar", "carbon",
        "green", "eco", "environment", "conservation", "pollution",
        "biodiversity", "emissions", "clean energy",
    ],
    "legal": [
        "law", "legal", "attorney", "lawyer", "court", "litigation",
        "compliance", "regulation", "intellectual property", "patent",
        "trademark", "contract", "lawsuit",
    ],
    "sports": [
        "sports", "football", "basketball", "soccer", "nba", "nfl",
        "fifa", "olympics", "athlete", "championship", "tournament",
        "coach", "team", "match",
    ],
    "entertainment": [
        "movie", "film", "music", "netflix", "spotify", "podcast",
        "concert", "album", "streaming", "celebrity", "hollywood",
        "anime", "series", "show",
    ],
}

GEO_PATTERNS = [
    (r"\b(?:new york|nyc|manhattan|brooklyn)\b", "New York"),
    (r"\b(?:san francisco|sf|bay area)\b", "San Francisco"),
    (r"\b(?:los angeles|la|hollywood)\b", "Los Angeles"),
    (r"\b(?:london|uk|united kingdom|england|british)\b", "London/UK"),
    (r"\b(?:india|indian|mumbai|delhi|bangalore|bengaluru|hyderabad)\b", "India"),
    (r"\b(?:china|chinese|beijing|shanghai|shenzhen)\b", "China"),
    (r"\b(?:germany|german|berlin|münchen)\b", "Germany"),
    (r"\b(?:france|french|paris)\b", "France"),
    (r"\b(?:japan|japanese|tokyo|osaka)\b", "Japan"),
    (r"\b(?:korea|korean|seoul)\b", "South Korea"),
    (r"\b(?:canada|canadian|toronto|vancouver|montreal)\b", "Canada"),
    (r"\b(?:australia|australian|sydney|melbourne)\b", "Australia"),
    (r"\b(?:brazil|brazilian|são paulo|rio)\b", "Brazil"),
    (r"\b(?:nigeria|nigerian|lagos|abuja)\b", "Nigeria"),
    (r"\b(?:singapore|sg)\b", "Singapore"),
    (r"\b(?:dubai|uae|emirates)\b", "Dubai/UAE"),
    (r"\b(?:pakistan|pakistani|lahore|karachi)\b", "Pakistan"),
    (r"\b(?:israel|israeli|tel aviv)\b", "Israel"),
    (r"\b(?:amsterdam|netherlands|dutch)\b", "Netherlands"),
    (r"\b(?:usa|united states|america|american)\b", "USA"),
]

try:
    from langdetect import detect as _langdetect_detect
    from langdetect.lang_detect_exception import LangDetectException

    def _detect_language(text):
        if not text:
            return "unknown"
        try:
            return _langdetect_detect(text)
        except LangDetectException:
            return "unknown"

except ImportError:
    _langdetect = None

    def _detect_language(text):
        return "unknown"


def extract_geo_hint(text, author_handle=None):
    text = text or ""
    author_handle = author_handle or ""
    combined = f"{text} {author_handle}".strip()
    if not combined:
        return None

    combined_lower = combined.lower()
    for pattern, geo in GEO_PATTERNS:
        if re.search(pattern, combined_lower):
            return geo
    return None


def infer_interests(text):
    text = text or ""
    text_lower = text.lower()
    found = []

    for category, keywords in PROFESSIONAL_INTERESTS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits >= 2:
            found.append(category)
        elif hits == 1 and len(text_lower.split()) < 15:
            found.append(category)

    return found[:3] if found else ["general"]


def analyze_demographics(posts):
    if not posts:
        return []

    inferred_at = datetime.now(timezone.utc).isoformat()
    results = []

    for post in posts:
        text = post.get("text", "")
        handle = post.get("author_handle", "")

        language = _detect_language(text)
        geo = extract_geo_hint(text, handle)
        interests = infer_interests(text)

        results.append({
            "post_id": post["id"],
            "language": language,
            "geo_hint": geo,
            "interests_json": json.dumps(interests),
            "inferred_at": inferred_at,
        })

    return results
