import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.5-flash"
ENV_API_KEY = "LLM_API_KEY"
ENV_MODEL = "LLM_MODEL"

REPORT_SECTIONS = [
    "Executive Summary",
    "Sentiment",
    "Emotion & Stance",
    "Trends",
    "Demographics",
    "Network & Influence",
    "Bottom Line",
]


def _pct(count, total):
    return round(count * 100.0 / total, 1) if total else 0.0


def _pick_top(counter, top_n=5):
    return [w for w, _ in counter.most_common(top_n)]


def build_report_data(posts, sentiments=None, emotions=None, demographics=None,
                      trends=None, network=None, topic_query=None):
    """Aggregate every analytics stage into one compact, prompt-sized dict.

    Only aggregates (counts, percentages, top lists) are kept — raw post text
    never enters the narrative so prompts stay small and deterministic.
    """
    posts = posts or []
    sentiments = sentiments or []
    emotions = emotions or []
    demographics = demographics or []
    trends = trends or []
    network = network or {}

    total = len(posts)
    platform_counts = Counter(p.get("platform", "unknown") for p in posts)

    sentiment_counts = Counter(s.get("label") for s in sentiments)
    sentiment_rates = {
        label: _pct(sentiment_counts.get(label, 0), len(sentiments))
        for label in ("positive", "neutral", "negative")
    }
    by_platform_sentiment = {}
    for platform in set(s.get("platform") for s in sentiments):
        labels = Counter(
            s.get("label") for s in sentiments if s.get("platform") == platform
        )
        by_platform_sentiment[platform] = {
            label: _pct(labels.get(label, 0), sum(labels.values()))
            for label in ("positive", "neutral", "negative")
        }

    emotion_counts = Counter(e.get("primary_emotion") for e in emotions)
    stance_counts = Counter(e.get("stance") for e in emotions)
    sarcasm_pct = _pct(
        sum(1 for e in emotions if e.get("sarcasm_flag")), len(emotions)
    )

    language_counts = Counter(d.get("language") for d in demographics)
    geo_counts = Counter(d.get("geo_hint") for d in demographics if d.get("geo_hint"))
    interest_counter = Counter()
    for d in demographics:
        try:
            interests = json.loads(d.get("interests_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            interests = []
        if isinstance(interests, list):
            interest_counter.update(interests)

    top_keywords = []
    if trends:
        latest_window = max((t.get("window_start") or "") for t in trends)
        latest_rows = [t for t in trends if t.get("window_start") == latest_window]
        latest_rows.sort(key=lambda t: t.get("frequency", 0), reverse=True)
        top_keywords = [
            {"keyword": t.get("keyword"), "frequency": t.get("frequency", 0)}
            for t in latest_rows[:10]
        ]

    rising = []
    try:
        from analytics.trends import rising_terms
        rising = [kw for kw, _ in rising_terms(posts, top_n=5)]
    except Exception:
        rising = []

    nodes = network.get("nodes") or []
    edges = network.get("edges") or []
    kol_handles = sorted(
        n.get("handle") for n in nodes if n.get("is_kol")
    )
    communities = sorted({n.get("community_id") for n in nodes if n.get("community_id") is not None})

    return {
        "topic_query": topic_query or (posts[0].get("topic_query") if posts else None),
        "total_posts": total,
        "platforms": dict(platform_counts),
        "sentiment": {
            "counts": dict(sentiment_counts),
            "rates": sentiment_rates,
            "by_platform": by_platform_sentiment,
        },
        "emotions": {
            "counts": dict(emotion_counts),
            "stance_counts": dict(stance_counts),
            "sarcasm_pct": sarcasm_pct,
        },
        "trends": {
            "top_keywords": top_keywords,
            "rising": rising,
        },
        "demographics": {
            "languages": dict(language_counts),
            "geo": dict(geo_counts),
            "interests": dict(interest_counter),
        },
        "network": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "kol_handles": kol_handles,
            "community_count": len(communities),
        },
    }


def make_prompt(data):
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    sections = "\n".join(f"- {s}" for s in REPORT_SECTIONS)
    return (
        "You are a social-media intelligence analyst. Write an executive "
        "narrative report in Markdown about the topic given by these aggregated "
        "analytics results.\n\n"
        f"Required sections (use these exact headings):\n{sections}\n\n"
        "Rules:\n"
        "- Base every claim strictly on the data provided; do not invent numbers.\n"
        "- Be concrete: name the leading sentiment, emotion, trending keywords, "
        "top languages/regions/interests, and key opinion leaders.\n"
        "- Keep it tight: 300-450 words, skimmable, use short paragraphs and "
        "bullets where helpful.\n\n"
        "DATA:\n"
        f"{payload}"
    )


def _call_gemini(prompt, api_key, model=None):
    import time

    import requests

    model = model or os.environ.get(ENV_MODEL) or DEFAULT_MODEL
    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(3):
        try:
            resp = requests.post(url, json=body, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            msg = str(e).replace(api_key, "[REDACTED]")
            transient = (
                isinstance(e, requests.exceptions.HTTPError)
                and e.response is not None
                and e.response.status_code >= 500
            )
            if not transient or attempt == 2:
                raise RuntimeError(f"Gemini request failed: {msg}") from e
            time.sleep(1)


def _exec_summary(data):
    rates = data["sentiment"]["rates"]
    dominant = max(rates, key=lambda k: rates[k]) if any(rates.values()) else "neutral"
    emotions = data["emotions"]["counts"]
    top_emotion = max(emotions, key=emotions.get) if emotions else "neutral"
    kws = data["trends"]["top_keywords"]
    top_kw = kws[0]["keyword"] if kws else "n/a"

    lines = [
        f"This report covers **{data['total_posts']} posts** across "
        f"_{', '.join(f'{k} ({v})' for k, v in data['platforms'].items()) or 'no platform data'}_ "
        f"for the topic {'**' + str(data['topic_query']) + '**' if data['topic_query'] else '(unknown)'}.",
        "",
        f"Overall sentiment skews **{dominant}** "
        f"(positive {rates['positive']}% / neutral {rates['neutral']}% / "
        f"negative {rates['negative']}%), with **{top_emotion}** as the leading emotion. "
        f"The top keyword this window is **{top_kw}**.",
    ]
    kols = data["network"]["kol_handles"]
    if kols:
        lines.append(
            f"{len(kols)} key opinion leader(s) were identified "
            f"({', '.join(kols[:5])})."
        )
    return "\n".join(lines)


def _sentiment_section(data):
    rates = data["sentiment"]["rates"]
    counts = data["sentiment"]["counts"]
    lines = [
        f"- Positive: **{rates['positive']}%** ({counts.get('positive', 0)})",
        f"- Neutral: **{rates['neutral']}%** ({counts.get('neutral', 0)})",
        f"- Negative: **{rates['negative']}%** ({counts.get('negative', 0)})",
    ]
    by_platform = data["sentiment"]["by_platform"]
    if by_platform:
        lines.append("")
        lines.append("By platform:")
        for platform, r in sorted(by_platform.items()):
            lines.append(
                f"- **{platform}**: positive {r['positive']}% / "
                f"neutral {r['neutral']}% / negative {r['negative']}%"
            )
    return "\n".join(lines)


def _emotion_section(data):
    counts = data["emotions"]["counts"]
    stance = data["emotions"]["stance_counts"]
    lines = [
        f"- Sarcasm rate: **{data['emotions']['sarcasm_pct']}%** of analyzed posts",
    ]
    if counts:
        lines.append("- Primary emotions:")
        for emotion, count in Counter(counts).most_common():
            lines.append(f"  - {emotion}: {count}")
    if stance:
        lines.append("- Stance:")
        for label, count in Counter(stance).most_common():
            lines.append(f"  - {label}: {count}")
    return "\n".join(lines)


def _trends_section(data):
    kws = data["trends"]["top_keywords"]
    rising = data["trends"]["rising"]
    lines = []
    if kws:
        lines.append("Top keywords this window:")
        lines.extend(f"- **{k['keyword']}**: {k['frequency']} mentions" for k in kws)
    if rising:
        lines.append("")
        lines.append(f"Currently rising terms: {', '.join(rising)}.")
    if not lines:
        lines.append("No trend data available.")
    return "\n".join(lines)


def _demographics_section(data):
    langs = data["demographics"]["languages"]
    geo = data["demographics"]["geo"]
    interests = data["demographics"]["interests"]
    lines = []
    if langs:
        lines.append(f"- Top languages: {', '.join(_pick_top(Counter(langs)))}")
    if geo:
        lines.append(f"- Top regions: {', '.join(_pick_top(Counter(geo)))}")
    if interests:
        lines.append(f"- Top interests: {', '.join(_pick_top(Counter(interests)))}")
    if not lines:
        lines.append("No demographic data available.")
    return "\n".join(lines)


def _network_section(data):
    net = data["network"]
    lines = [
        f"- {net['node_count']} handles, {net['edge_count']} mention/reply edges, "
        f"{net['community_count']} community group(s)."
    ]
    if net["kol_handles"]:
        lines.append(f"- Key opinion leaders: {', '.join(net['kol_handles'])}")
    else:
        lines.append("- No key opinion leaders identified (insufficient interaction data).")
    return "\n".join(lines)


def _bottom_line(data):
    rates = data["sentiment"]["rates"]
    stance = data["emotions"]["stance_counts"]
    supportive = stance.get("supportive", 0)
    against = stance.get("against", 0)

    tone = "support is broadly positive" if (
        rates["positive"] > rates["negative"] or supportive > against
    ) else "reception carries notable negative or mixed signals"
    body = [
        f"Recommendation: the audience for this topic shows that {tone}. "
    ]
    if data["trends"]["rising"]:
        body.append(
            f"Lean into the rising conversation around "
            f"{', '.join(data['trends']['rising'][:3])} to stay ahead of the curve."
        )
    kols = data["network"]["kol_handles"]
    if kols:
        body.append(
            f"Engage the identified key opinion leaders "
            f"({', '.join(kols[:3])}) for amplification."
        )
    return "\n".join(body)


def _template_report(data):
    sections = {
        "Executive Summary": _exec_summary(data),
        "Sentiment": _sentiment_section(data),
        "Emotion & Stance": _emotion_section(data),
        "Trends": _trends_section(data),
        "Demographics": _demographics_section(data),
        "Network & Influence": _network_section(data),
        "Bottom Line": _bottom_line(data),
    }
    parts = []
    for name in REPORT_SECTIONS:
        parts.append(f"## {name}\n")
        parts.append(sections[name] + "\n")
    return "\n".join(parts).strip() + "\n"


def generate_narrative(posts, sentiments=None, emotions=None, demographics=None,
                       trends=None, network=None, topic_query=None, model=None):
    """Produce a narrative report; Gemini-backed when LLM_API_KEY is set,
    otherwise a deterministic template report.

    Returns a dict ready for the narratives table, or None when there are no posts.
    """
    data = build_report_data(posts, sentiments, emotions, demographics, trends,
                             network, topic_query=topic_query)
    if not data["total_posts"]:
        return None

    api_key = os.environ.get(ENV_API_KEY)
    backend = "template"
    used_model = None
    report = None

    if api_key:
        try:
            prompt = make_prompt(data)
            report = _call_gemini(prompt, api_key, model=model)
            backend = "gemini"
            used_model = model or os.environ.get(ENV_MODEL) or DEFAULT_MODEL
        except Exception as e:
            print(f"[Narrative] Gemini call failed, using template fallback: {e}")

    if report is None:
        report = _template_report(data)

    return {
        "topic_query": topic_query or data.get("topic_query") or "unknown",
        "backend": backend,
        "model": used_model,
        "stats_json": json.dumps(data, indent=2, ensure_ascii=False),
        "report_markdown": report,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report_file(topic_query, markdown, created_at=None, output_dir=None):
    """Persist the report as a timestamped markdown file. Returns the path."""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports"
        )
    os.makedirs(output_dir, exist_ok=True)

    slug = re.sub(r"[^a-z0-9]+", "-", (topic_query or "report").lower()).strip("-") or "report"
    if created_at:
        stamp = re.sub(r"[^0-9]", "", created_at)[:14]
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    path = os.path.join(output_dir, f"{slug}_{stamp}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(markdown)
    return path