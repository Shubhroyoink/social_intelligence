"""Analysis parity for X data: the stages must treat X posts exactly like
Telegram and YouTube ones, and the influence graph must actually resolve the
reply edges the collector now populates.

These tests deliberately drive the real analysis functions on posts produced by
the real Social Fetch mapper, so a regression in either layer is caught here.
"""
import pytest

import collectors.x_collector as x_collector
from analytics.network import analyze_network, build_graph
from database.db import get_posts, save_posts
from normalizer.normalizer import dedupe, normalize_posts


def _tweet(tid, handle, text, reply_to=None, uid="u1"):
    return {
        "id": tid,
        "text": text,
        "createdAt": "2026-08-01T10:00:00Z",
        "inReplyToStatusId": reply_to,
        "author": {"handle": handle, "platformUserId": uid},
        "metrics": {"likes": 5, "retweets": 2, "replies": 1, "views": 100},
    }


def _map_all(tweets):
    """Run raw Social Fetch tweets through the real collector mapper."""
    return [m for m in (x_collector._map_tweet(t, "AI Agents") for t in tweets)
            if m is not None]


def _normalized(tweets):
    posts = _map_all(tweets)
    return dedupe(normalize_posts(posts), key="id")


class TestXAnalysisParity:
    def test_x_posts_reach_every_analysis_input(self):
        """Each stage reads `id`, `text` and `author_handle`; X supplies all."""
        posts = _normalized([
            _tweet("1", "alice", "Shipping agent infrastructure today"),
            _tweet("2", "bob", "LLM inference is getting cheaper fast"),
        ])
        assert len(posts) == 2
        for p in posts:
            assert p["platform"] == "x"
            assert p["topic_query"] == "AI Agents"
            assert p["id"] and p["text"] and p["author_handle"]

    def test_sentiment_and_emotions_accept_x_posts(self):
        posts = _normalized([_tweet("1", "alice", "love this, works great")])
        from analytics.sentiment import analyze_posts
        from analytics.emotions import analyze_emotions

        sentiments = analyze_posts(posts)
        assert len(sentiments) == 1
        assert sentiments[0]["platform"] == "x"
        assert sentiments[0]["post_id"] == posts[0]["id"]

        emotions = analyze_emotions(posts)
        assert len(emotions) == 1
        assert emotions[0]["post_id"] == posts[0]["id"]

    def test_demographics_and_trends_accept_x_posts(self):
        posts = _normalized([
            _tweet("1", "alice", "python machine learning model in the cloud"),
            _tweet("2", "bob", "agent rag inference pipeline"),
        ])
        from analytics.demographics import analyze_demographics
        from analytics.trends import detect_trends, rising_terms

        demos = analyze_demographics(posts)
        assert len(demos) == 2
        assert {d["post_id"] for d in demos} == {p["id"] for p in posts}

        trends = detect_trends(posts, "AI Agents", window_size_hours=24)
        assert isinstance(trends, list)
        assert isinstance(rising_terms(posts, window_size_hours=24), list)


class TestXNetworkAnalysis:
    def test_reply_edges_resolve_through_parent_id(self):
        """Regression guard: parent_id must be platform-prefixed to match the
        post id, or the influence graph degrades to a 1-edge star."""
        posts = _normalized([
            _tweet("1", "alice", "Anyone building agents? ask me"),
            _tweet("2", "bob", "Yes, shipping now", reply_to="1"),
            _tweet("3", "carol", "same here", reply_to="1"),
        ])
        G = build_graph(posts)

        assert G.has_node("@alice") and G.has_node("@bob")
        assert G.has_edge("@alice", "@bob")
        assert G.has_edge("@alice", "@carol")
        assert G["@alice"]["@bob"]["weight"] == 1

    def test_parent_id_matches_the_prefixed_post_id(self):
        posts = _normalized([
            _tweet("1", "alice", "root of the thread"),
            _tweet("2", "bob", "a reply", reply_to="1"),
        ])
        by_id = {p["id"]: p for p in posts}
        reply = by_id["x_2"]
        # The parent must be findable in the same collection.
        assert reply["parent_id"] in by_id

    def test_mention_edges_resolve_across_x_and_telegram(self):
        """X handles are stored '@'-prefixed, matching Telegram channels, so a
        mention in either direction links the two platforms' authors."""
        posts = _normalized([
            _tweet("1", "alice", "great thread from @aipost"),
        ]) + [{
            "id": "aipost_10",
            "platform": "telegram",
            "author_handle": "@aipost",
            "text": "thanks for reading",
            "raw_text": "thanks for reading",
            "parent_id": None,
            "topic_query": "AI Agents",
        }]
        G = build_graph(posts)
        assert G.has_edge("@alice", "@aipost")

    def test_full_analyze_network_runs_on_x_data(self):
        posts = _normalized([
            _tweet("1", "alice", "root post about agents", uid="1"),
            _tweet("2", "bob", "replying, great point", reply_to="1", uid="2"),
            _tweet("3", "carol", "cc @bob and @alice", reply_to="1", uid="3"),
        ])
        sentiments = [
            {"post_id": p["id"], "platform": "x", "label": "positive",
             "created_at": p["created_at"], "topic_query": "AI Agents"}
            for p in posts
        ]

        result = analyze_network(posts, "AI Agents", sentiments)

        assert len(result["nodes"]) == 3
        assert len(result["edges"]) >= 2
        assert all(n["topic_query"] == "AI Agents" for n in result["nodes"])
        # The KOL stage ran and ranked real X handles (which one wins depends
        # on the graph shape, not on the platform).
        assert result["kols"]
        assert set(result["kols"]) <= {"@alice", "@bob", "@carol"}
        # Reply edges give the thread root outgoing influence, and the
        # mentions give it incoming -- so it must not be isolated.
        alice = next(n for n in result["nodes"] if n["handle"] == "@alice")
        assert alice["degree_centrality"] > 0
        for edge in result["edges"]:
            assert edge["topic_query"] == "AI Agents"
            assert edge["weight"] >= 1


class TestXPersistedForAnalysis:
    def test_x_posts_round_trip_through_the_db(self, test_db):
        """The --no-collect path re-reads posts from the DB, so X data has to
        survive storage with the fields the analysis stages need."""
        posts = _normalized([
            _tweet("1", "alice", "shipping agents, cc @bob", reply_to=None),
            _tweet("2", "bob", "nice work", reply_to="1"),
        ])
        save_posts(posts)

        stored = {p["id"]: p for p in get_posts(topic_query="AI Agents",
                                               platform="x")}

        assert len(stored) == 2
        root, reply = stored["x_1"], stored["x_2"]
        assert root["author_handle"] == "@alice"
        assert root["text"] and root["raw_text"]
        assert "@bob" in root["raw_text"]
        assert reply["parent_id"] == "x_1"
        # Engagement metrics survive so nothing downstream sees nulls.
        assert reply["reactions"] == 5
        assert reply["views"] == 100
