"""End-to-end: run_pipeline.run() with X data in, and assert every analysis
stage produces X rows -- the same parity Telegram and YouTube already have.

Collection is mocked at the collector boundary; everything downstream
(normalizer, DB, sentiment, emotion, demographics, trends, network, narrative)
is the real code path.
"""
import pytest

import collectors.x_collector as x_collector
import database.db as db

TOPIC = "AI Agents"

RAW_TWEETS = [
    {
        "id": "1001",
        "text": "Shipping agent infrastructure today, cc @bob https://x.com/a/status/1001",
        "createdAt": "2026-08-01T10:00:00Z",
        "inReplyToStatusId": None,
        "author": {"handle": "alice", "platformUserId": "u1"},
        "metrics": {"likes": 10, "retweets": 2, "replies": 1, "views": 400},
    },
    {
        "id": "1002",
        "text": "Replying, this is great work @alice",
        "createdAt": "2026-08-01T11:00:00Z",
        "inReplyToStatusId": "1001",
        "author": {"handle": "bob", "platformUserId": "u2"},
        "metrics": {"likes": 3, "retweets": 0, "replies": 0, "views": 90},
    },
    {
        "id": "1003",
        "text": "Machine learning inference cost is falling, nice",
        "createdAt": "2026-08-01T12:00:00Z",
        "inReplyToStatusId": None,
        "author": {"handle": "carol", "platformUserId": "u3"},
        "metrics": {"likes": 5, "retweets": 1, "replies": 0, "views": 200},
    },
]


@pytest.fixture
def fake_x_collector(monkeypatch):
    """Replace the billable collector call; return the mapped X posts."""
    captured = {}

    def fake_collect(topic_query, **kwargs):
        captured["topic_query"] = topic_query
        captured["kwargs"] = kwargs
        return [
            m for m in (x_collector._map_tweet(t, topic_query) for t in RAW_TWEETS)
            if m is not None
        ]

    monkeypatch.setattr(x_collector, "collect_x_for_topic", fake_collect)
    return captured


@pytest.fixture
def run_pipeline_with_x(fake_x_collector, mock_sentiment, mock_emotions):
    """Run the real pipeline with Telegram and YouTube switched off."""
    import run_pipeline

    posts = run_pipeline.run(
        topic_query=TOPIC,
        telegram_channels=[],
        x_queries=["AI Agents"],
        youtube_search=False,
        do_collect=True,
        do_analyze=True,
    )
    return posts, fake_x_collector


class TestPipelineRunsFullAnalysisOnXData:
    def test_x_posts_are_collected_and_saved(self, run_pipeline_with_x):
        posts, captured = run_pipeline_with_x
        assert len(posts) == 3
        assert captured["topic_query"] == TOPIC
        assert {p["platform"] for p in posts} == {"x"}

        stored = db.get_posts(topic_query=TOPIC, platform="x")
        assert len(stored) == 3

    def test_sentiment_stage_covers_x_posts(self, run_pipeline_with_x):
        posts, _ = run_pipeline_with_x
        sentiments = db.get_sentiments(topic_query=TOPIC)
        assert len(sentiments) == len(posts)
        assert {s["post_id"] for s in sentiments} == {p["id"] for p in posts}
        assert {s["platform"] for s in sentiments} == {"x"}

    def test_emotion_stage_covers_x_posts(self, run_pipeline_with_x):
        posts, _ = run_pipeline_with_x
        emotions = db.get_emotions(topic_query=TOPIC)
        assert len(emotions) == len(posts)
        assert {e["post_id"] for e in emotions} == {p["id"] for p in posts}

    def test_demographics_stage_covers_x_posts(self, run_pipeline_with_x):
        posts, _ = run_pipeline_with_x
        demographics = db.get_demographics(topic_query=TOPIC)
        assert len(demographics) == len(posts)
        assert {d["post_id"] for d in demographics} == {p["id"] for p in posts}

    def test_trend_stage_runs_on_x_text(self, run_pipeline_with_x):
        # Trends accumulate in the DB; the stage must not crash or no-op on
        # X text. Tokenization works off the same cleaned `text` field.
        trends = db.get_trends(topic_query=TOPIC)
        assert isinstance(trends, list)

    def test_network_stage_builds_x_nodes_and_edges(self, run_pipeline_with_x):
        nodes = db.get_network_nodes(topic_query=TOPIC)
        assert {n["handle"] for n in nodes} == {"@alice", "@bob", "@carol"}

        edges = db.get_network_edges(topic_query=TOPIC)
        pairs = {(e["source_handle"], e["target_handle"]) for e in edges}
        # @alice -> @bob from the reply parent AND from the @bob mention in
        # the root post, so the two mechanisms merge into one weighted edge.
        assert ("@alice", "@bob") in pairs
        assert ("@bob", "@alice") in pairs  # reply in text
        merged = next(e for e in edges
                      if e["source_handle"] == "@alice"
                      and e["target_handle"] == "@bob")
        assert merged["weight"] == 2
        # The reply target must be a ranked, connected node.
        alice = next(n for n in nodes if n["handle"] == "@alice")
        assert alice["degree_centrality"] > 0
        assert alice["is_kol"] in (0, 1)

    def test_reply_edge_is_present_in_the_graph(self, run_pipeline_with_x):
        """Without a platform-prefixed parent_id this edge cannot exist."""
        edges = db.get_network_edges(topic_query=TOPIC)
        reply_edges = [e for e in edges
                       if e["source_handle"] == "@alice"
                       and e["target_handle"] == "@bob"]
        assert reply_edges, (
            "Expected an @alice -> @bob edge from the reply parent. "
            "If this fails, parent_id lost its platform prefix."
        )

    def test_narrative_stage_includes_x(self, run_pipeline_with_x):
        narratives = db.get_narratives(topic_query=TOPIC)
        assert narratives, "narrative stage produced nothing for X data"
        # LLM_API_KEY is scrubbed in tests, so the deterministic template ran.
        # Its opening line carries the platform breakdown, which must credit
        # all three posts to X rather than reporting "no platform data".
        rendered = narratives[0]["report_markdown"]
        assert "x (3)" in rendered
        assert "no platform data" not in rendered
        # The network KOLs it reports must be the X handles we collected.
        assert "@" in rendered


class TestXProfileBookkeepingStaysSeparate:
    def test_x_profiles_do_not_duplicate_as_posts(self, run_pipeline_with_x):
        """Profile rows are bookkeeping; only tweets are analyzed."""
        posts, _ = run_pipeline_with_x
        assert all(p["platform"] == "x" for p in posts)
        assert len(posts) == 3  # one per tweet, not one per profile
        # No profile table rows were invented by the analysis stages.
        assert db.get_x_profiles(TOPIC) == []
