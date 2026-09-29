import os
import sys
import threading
from typing import Optional, List
from dotenv import load_dotenv
from fastapi import FastAPI, Query, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv()

from database.db import (
    create_database, get_posts, get_sentiments, get_trends, get_emotions,
    get_demographics_summary, get_demographics, get_network_nodes, get_network_edges,
    get_narratives
)
from task_queue.job_manager import get_job_manager

app = FastAPI(
    title="Social Intelligence API",
    description="REST API serving social media analytics, sentiments, emotions, network graphs, and AI narratives",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_database()

# Active job tracker reference
job_manager = get_job_manager()


class PipelineRunRequest(BaseModel):
    topic: str = "AI Agents"
    channels: Optional[List[str]] = ["@aipost", "@KDnuggets", "@theaiexecutive"]
    x_queries: Optional[List[str]] = None
    youtube_urls: Optional[List[str]] = None
    youtube_search: bool = True
    yt_max_videos: int = 5
    yt_comments: int = 100
    telegram_limit: int = 100
    x_limit: int = 20
    do_collect: bool = True
    do_analyze: bool = True
    skip_emotions: bool = False
    skip_demographics: bool = False
    skip_network: bool = False
    skip_narrative: bool = False


@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "Social Intelligence API",
        "redis_active": job_manager.is_redis_active
    }


@app.get("/api/topics")
def list_topics():
    posts = get_posts()
    topics = sorted(list(set(p["topic_query"] for p in posts if p.get("topic_query"))))
    return {"topics": topics}


@app.get("/api/overview")
def get_overview(topic: Optional[str] = None):
    t = topic if topic and topic != "All" else None
    posts = get_posts(topic_query=t)
    sentiments = get_sentiments(topic_query=t)
    emotions = get_emotions(topic_query=t)
    nodes = get_network_nodes(topic_query=t)
    trends = get_trends(topic_query=t, limit=10)

    total_posts = len(posts)
    total_analyzed = len(sentiments)

    pos_count = sum(1 for s in sentiments if s.get("label") == "positive")
    neu_count = sum(1 for s in sentiments if s.get("label") == "neutral")
    neg_count = sum(1 for s in sentiments if s.get("label") == "negative")

    pos_pct = round(pos_count * 100.0 / total_analyzed, 1) if total_analyzed else 0.0
    neu_pct = round(neu_count * 100.0 / total_analyzed, 1) if total_analyzed else 0.0
    neg_pct = round(neg_count * 100.0 / total_analyzed, 1) if total_analyzed else 0.0

    sarcasm_count = sum(1 for e in emotions if e.get("sarcasm_flag") == 1)
    sarcasm_pct = round(sarcasm_count * 100.0 / len(emotions), 1) if emotions else 0.0

    kol_count = sum(1 for n in nodes if n.get("is_kol") == 1)

    platforms = {}
    for p in posts:
        plat = p.get("platform", "unknown")
        platforms[plat] = platforms.get(plat, 0) + 1

    top_keyword = trends[0]["keyword"] if trends else None

    emotion_counts = {}
    for e in emotions:
        emo = e.get("primary_emotion")
        if emo:
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
    dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"

    return {
        "total_posts": total_posts,
        "total_analyzed": total_analyzed,
        "positive_pct": pos_pct,
        "neutral_pct": neu_pct,
        "negative_pct": neg_pct,
        "sarcasm_pct": sarcasm_pct,
        "kol_count": kol_count,
        "top_keyword": top_keyword,
        "dominant_emotion": dominant_emotion,
        "platform_counts": platforms
    }


@app.get("/api/posts")
def list_posts(
    topic: Optional[str] = None,
    platform: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: Optional[int] = 100,
    search: Optional[str] = None
):
    t = topic if topic and topic != "All" else None
    plat = platform if platform and platform != "All" else None
    posts = get_posts(topic_query=t, platform=plat, limit=limit)

    sentiments_map = {s["post_id"]: s for s in get_sentiments(topic_query=t)}
    emotions_map = {e["post_id"]: e for e in get_emotions(topic_query=t)}

    enriched = []
    for p in posts:
        pid = p["id"]
        s = sentiments_map.get(pid, {})
        e = emotions_map.get(pid, {})
        post_obj = {
            **p,
            "sentiment": s.get("label"),
            "sentiment_score": s.get("score"),
            "primary_emotion": e.get("primary_emotion"),
            "stance": e.get("stance"),
            "sarcasm_flag": e.get("sarcasm_flag", 0)
        }
        
        if sentiment and sentiment != "All" and post_obj.get("sentiment") != sentiment:
            continue
            
        if search:
            s_lower = search.lower()
            text_match = s_lower in post_obj.get("text", "").lower()
            author_match = s_lower in (post_obj.get("author_handle") or "").lower()
            if not (text_match or author_match):
                continue

        enriched.append(post_obj)

    return {"posts": enriched, "count": len(enriched)}


@app.get("/api/sentiments")
def list_sentiments(topic: Optional[str] = None):
    t = topic if topic and topic != "All" else None
    sentiments = get_sentiments(topic_query=t)

    dist = {"positive": 0, "neutral": 0, "negative": 0}
    by_platform = {}
    by_date = {}

    for s in sentiments:
        lbl = s.get("label", "neutral")
        dist[lbl] = dist.get(lbl, 0) + 1
        plat = s.get("platform") or "unknown"
        if plat not in by_platform:
            by_platform[plat] = {"positive": 0, "neutral": 0, "negative": 0}
        by_platform[plat][lbl] = by_platform[plat].get(lbl, 0) + 1

        created = s.get("created_at") or s.get("analyzed_at")
        if created:
            date_str = str(created)[:10]
            if date_str not in by_date:
                by_date[date_str] = {"positive": 0, "neutral": 0, "negative": 0, "count": 0}
            by_date[date_str][lbl] = by_date[date_str].get(lbl, 0) + 1
            by_date[date_str]["count"] += 1

    timeline = []
    for d in sorted(by_date.keys()):
        cnt = by_date[d]["count"]
        timeline.append({
            "date": d,
            "positive": round(by_date[d]["positive"] * 100.0 / cnt, 1) if cnt else 0,
            "neutral": round(by_date[d]["neutral"] * 100.0 / cnt, 1) if cnt else 0,
            "negative": round(by_date[d]["negative"] * 100.0 / cnt, 1) if cnt else 0,
            "count": cnt,
        })

    return {
        "sentiments": sentiments,
        "distribution": dist,
        "by_platform": by_platform,
        "timeline": timeline,
        "count": len(sentiments)
    }


@app.get("/api/emotions")
def list_emotions(topic: Optional[str] = None):
    t = topic if topic and topic != "All" else None
    emotions = get_emotions(topic_query=t)

    emotion_counts = {}
    stance_counts = {}
    sarcasm_count = 0
    by_date = {}

    for e in emotions:
        emo = e.get("primary_emotion", "neutral")
        emotion_counts[emo] = emotion_counts.get(emo, 0) + 1

        stn = e.get("stance", "neutral")
        stance_counts[stn] = stance_counts.get(stn, 0) + 1

        if e.get("sarcasm_flag") == 1:
            sarcasm_count += 1

        created = e.get("created_at") or e.get("analyzed_at")
        if created:
            date_str = str(created)[:10]
            if date_str not in by_date:
                by_date[date_str] = {"count": 0}
            by_date[date_str][emo] = by_date[date_str].get(emo, 0) + 1
            by_date[date_str]["count"] += 1

    timeline = []
    for d in sorted(by_date.keys()):
        cnt = by_date[d]["count"]
        entry = {"date": d, "count": cnt}
        for emo_name in ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]:
            entry[emo_name] = round(by_date[d].get(emo_name, 0) * 100.0 / cnt, 1) if cnt else 0
        timeline.append(entry)

    total = len(emotions)
    sarcasm_pct = round(sarcasm_count * 100.0 / total, 1) if total else 0.0

    return {
        "emotions": emotions,
        "emotion_counts": emotion_counts,
        "stance_counts": stance_counts,
        "sarcasm_pct": sarcasm_pct,
        "timeline": timeline,
        "count": total
    }


@app.get("/api/wordcloud")
def get_wordcloud(topic: Optional[str] = None, limit: Optional[int] = 100):
    from normalizer.normalizer import tokenize
    from collections import Counter

    t = topic if topic and topic != "All" else None
    posts = get_posts(topic_query=t)

    counter = Counter()
    for p in posts:
        tokens = tokenize(p.get("text", ""))
        counter.update(tokens)

    words = [{"text": word, "value": count} for word, count in counter.most_common(limit)]
    return {"words": words}


@app.get("/api/demographics")
def list_demographics(topic: Optional[str] = None):
    t = topic if topic and topic != "All" else None
    summary = get_demographics_summary(topic_query=t)
    return summary


@app.get("/api/trends")
def list_trends(topic: Optional[str] = None):
    t = topic if topic and topic != "All" else None
    all_trends = get_trends(topic_query=t)

    if not all_trends:
        return {
            "all_trends": [],
            "latest_trends": [],
            "unique_keywords": [],
            "keyword_timelines": {},
            "count": 0
        }

    # Find latest window_start
    window_starts = [r["window_start"] for r in all_trends if r.get("window_start")]
    latest_window = max(window_starts) if window_starts else None

    # Filter for latest window trends
    if latest_window:
        latest_trends = [r for r in all_trends if r.get("window_start") == latest_window]
    else:
        latest_trends = all_trends

    latest_trends.sort(key=lambda x: x.get("frequency", 0), reverse=True)

    # Unique keywords from latest window (or all)
    seen_kw = set()
    unique_keywords = []
    for r in latest_trends:
        kw = r.get("keyword")
        if kw and kw not in seen_kw:
            seen_kw.add(kw)
            unique_keywords.append(kw)

    # If unique keywords from latest is short, fill with others
    for r in all_trends:
        kw = r.get("keyword")
        if kw and kw not in seen_kw:
            seen_kw.add(kw)
            unique_keywords.append(kw)

    # Build keyword timelines: groupby window_start summing frequency
    keyword_timelines = {}
    for kw in unique_keywords:
        timeline_dict = {}
        for r in all_trends:
            if r.get("keyword") == kw and r.get("window_start"):
                w = r["window_start"]
                timeline_dict[w] = timeline_dict.get(w, 0) + (r.get("frequency") or 0)
        sorted_times = sorted(timeline_dict.items(), key=lambda x: x[0])
        keyword_timelines[kw] = [{"window_start": k, "frequency": v} for k, v in sorted_times]

    return {
        "all_trends": all_trends,
        "latest_window": latest_window,
        "latest_trends": latest_trends[:20],
        "unique_keywords": unique_keywords[:20],
        "keyword_timelines": keyword_timelines,
        "count": len(all_trends)
    }


@app.get("/api/network")
def list_network(topic: Optional[str] = None):
    t = topic if topic and topic != "All" else None
    nodes = get_network_nodes(topic_query=t)
    edges = get_network_edges(topic_query=t)
    
    sorted_nodes = sorted(nodes, key=lambda n: n.get("eigenvector_centrality", 0) or 0, reverse=True)
    kols = [n for n in sorted_nodes if n.get("is_kol") == 1]
    if not kols and sorted_nodes:
        kols = sorted_nodes[:10]

    return {
        "nodes": sorted_nodes,
        "edges": edges,
        "kols": kols,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "kol_count": sum(1 for n in nodes if n.get("is_kol") == 1)
    }


@app.get("/api/narratives")
def list_narratives(topic: Optional[str] = None):
    t = topic if topic and topic != "All" else None
    narratives = get_narratives(topic_query=t)
    return {"narratives": narratives, "latest": narratives[0] if narratives else None}


@app.post("/api/pipeline/run")
def trigger_pipeline_run(req: PipelineRunRequest):
    # Check if there is already an active running job for the same topic
    recent_jobs = job_manager.list_jobs(limit=5)
    for j in recent_jobs:
        if j.get("status") in ("running", "queued") and j.get("topic") == req.topic:
            return {
                "job_id": j.get("job_id"),
                "status": j.get("status"),
                "message": f"Pipeline already running for topic '{req.topic}'",
                "topic": req.topic,
                "percent": j.get("percent", 0),
                "redis_active": job_manager.is_redis_active,
            }

    from run_pipeline import run
    pipeline_kwargs = {
        "topic_query": req.topic,
        "telegram_channels": req.channels,
        "x_queries": req.x_queries if req.x_queries is not None else [req.topic],
        "youtube_urls": req.youtube_urls,
        "telegram_limit": req.telegram_limit,
        "x_limit": req.x_limit,
        "youtube_search": req.youtube_search,
        "yt_max_videos": req.yt_max_videos,
        "yt_comments": req.yt_comments,
        "do_collect": req.do_collect,
        "do_analyze": req.do_analyze,
        "skip_emotions": req.skip_emotions,
        "skip_demographics": req.skip_demographics,
        "skip_network": req.skip_network,
        "skip_narrative": req.skip_narrative,
    }

    job_id = job_manager.submit_pipeline_job(
        topic=req.topic,
        run_pipeline_fn=run,
        kwargs=pipeline_kwargs,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Pipeline started in background for topic '{req.topic}'",
        "topic": req.topic,
        "percent": 0,
        "redis_active": job_manager.is_redis_active,
    }


@app.get("/api/pipeline/status")
def get_pipeline_status(job_id: Optional[str] = None):
    """Backward-compatible status endpoint returning live progress percentage and step."""
    if job_id:
        job = job_manager.get_job(job_id)
        if job:
            return {
                "is_running": job.get("status") in ("running", "queued"),
                "last_run": job.get("updated_at"),
                "current_topic": job.get("topic"),
                "status_message": job.get("message", "Idle"),
                "error": job.get("error"),
                "job_id": job.get("job_id"),
                "status": job.get("status"),
                "percent": job.get("percent", 0),
                "current_step": job.get("current_step", "Idle"),
                "redis_active": job_manager.is_redis_active,
            }

    # If no specific job_id, inspect latest job
    recent = job_manager.list_jobs(limit=1)
    if recent:
        latest = recent[0]
        return {
            "is_running": latest.get("status") in ("running", "queued"),
            "last_run": latest.get("updated_at"),
            "current_topic": latest.get("topic"),
            "status_message": latest.get("message", "Idle"),
            "error": latest.get("error"),
            "job_id": latest.get("job_id"),
            "status": latest.get("status"),
            "percent": latest.get("percent", 0),
            "current_step": latest.get("current_step", "Idle"),
            "redis_active": job_manager.is_redis_active,
        }

    return {
        "is_running": False,
        "last_run": None,
        "current_topic": None,
        "status_message": "Idle",
        "error": None,
        "job_id": None,
        "status": "idle",
        "percent": 0,
        "current_step": "Idle",
        "redis_active": job_manager.is_redis_active,
    }


@app.get("/api/jobs")
def list_pipeline_jobs(limit: Optional[int] = 20):
    """Retrieve list of recent pipeline runs."""
    jobs = job_manager.list_jobs(limit=limit or 20)
    return {"jobs": jobs, "count": len(jobs), "redis_active": job_manager.is_redis_active}


@app.get("/api/jobs/{job_id}")
def get_pipeline_job(job_id: str):
    """Retrieve detailed state and progress of a single pipeline job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
