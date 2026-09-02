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