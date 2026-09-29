"""Integration test: the full collection->normalize->save->analyze->network path.

This guards against the influence-network bug where the normalizer stripped
@mentions before storage, leaving build_graph() with no mention edges on
real pipeline-produced data.
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from normalizer.normalizer import normalize_posts, dedupe
from analytics.network import analyze_network
import database.db as db


RAW_POSTS = [
    {
        "id": "x_1",
        "platform": "x",
        "author_id": "u1",
        "author_handle": "@alice",
        "text": "AI agents are the future. Great review @bob https://example.com/review",
        "created_at": "2026-08-01T10:00:00+00:00",
        "collected_at": "2026-08-01T11:00:00+00:00",
        "parent_id": None,
        "topic_query": "AI Agents",
        "reactions": 10,
        "shares": 2,
        "replies": 1,
        "views": 50,
    },
    {
        "id": "x_2",
        "platform": "x",
        "author_id": "u2",
        "author_handle": "@bob",
        "text": "Thanks alice, glad you liked the writeup",
        "created_at": "2026-08-02T10:00:00+00:00",
        "collected_at": "2026-08-02T11:00:00+00:00",
        "parent_id": None,
        "topic_query": "AI Agents",
        "reactions": 0,
        "shares": 0,
        "replies": None,
        "views": None,
    },
]


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_social.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_file))
    db.create_database()


def test_mention_edge_survives_full_pipeline():
    normalized = normalize_posts(RAW_POSTS)
    normalized = dedupe(normalized, key="id")
    assert len(normalized) == 2

    db.save_posts(normalized)
    stored = db.get_posts(topic_query="AI Agents")
    assert len(stored) == 2

    network = analyze_network(stored, "AI Agents")
    handles = {n["handle"] for n in network["nodes"]}
    assert "@alice" in handles
    assert "@bob" in handles

    edge = next(
        (e for e in network["edges"]
         if e["source_handle"] == "@alice" and e["target_handle"] == "@bob"),
        None,
    )
    assert edge is not None, (
        "Expected @alice -> @bob mention edge; normalizer likely stripped "
        "@mentions before network analysis."
    )
    assert edge["weight"] == 1


def test_cleaned_text_stored_without_mentions_but_raw_kept():
    normalized = normalize_posts(RAW_POSTS)[0]
    assert "@bob" not in normalized["text"]
    assert "@bob" in normalized["raw_text"]


def test_no_collect_runs_network_and_narrative_on_full_corpus(mock_sentiment, mock_emotions):
    import run_pipeline

    multi_posts = [
        {
            "id": "tg_1", "platform": "telegram", "author_id": "c1", "author_handle": "@aipost",
            "text": "Telegram post about AI agents", "raw_text": "Telegram post about AI agents",
            "created_at": "2026-08-01T10:00:00+00:00", "collected_at": "2026-08-01T11:00:00+00:00",
            "parent_id": None, "topic_query": "AI Agents", "reactions": 5, "shares": 1,
            "replies": 0, "views": 100,
        },
        {
            "id": "yt_1", "platform": "youtube", "author_id": "u_yt", "author_handle": "@youtuber",
            "text": "YouTube comment on AI agents cc @aipost", "raw_text": "YouTube comment on AI agents cc @aipost",
            "created_at": "2026-08-01T12:00:00+00:00", "collected_at": "2026-08-01T13:00:00+00:00",
            "parent_id": None, "topic_query": "AI Agents", "reactions": 2, "shares": 0,
            "replies": 0, "views": 0,
        },
        {
            "id": "x_1", "platform": "x", "author_id": "u_x", "author_handle": "@twitteruser",
            "text": "X post about AI agents cc @youtuber", "raw_text": "X post about AI agents cc @youtuber",
            "created_at": "2026-08-01T14:00:00+00:00", "collected_at": "2026-08-01T15:00:00+00:00",
            "parent_id": None, "topic_query": "AI Agents", "reactions": 10, "shares": 2,
            "replies": 1, "views": 500,
        },
    ]
    db.save_posts(multi_posts)

    posts = run_pipeline.run(
        topic_query="AI Agents",
        do_collect=False,
        do_analyze=True,
    )
    assert len(posts) == 3
    nodes = db.get_network_nodes(topic_query="AI Agents")
    assert len(nodes) == 3
    narratives = db.get_narratives(topic_query="AI Agents")
    assert len(narratives) >= 1
    report = narratives[0]["report_markdown"]
    assert "telegram" in report
    assert "youtube" in report
    assert "x" in report