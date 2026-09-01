import json

import pytest

from analytics.network import (
    analyze_network,
    build_graph,
    detect_communities,
    identify_kols,
    compute_centrality,
)


def _post(pid, handle, text, parent_id=None):
    return {
        "id": pid,
        "author_handle": handle,
        "text": text,
        "created_at": "2026-08-01T10:00:00+00:00",
        "parent_id": parent_id,
        "platform": "x",
    }


class TestBuildGraph:
    def test_empty_returns_empty_graph(self):
        G = build_graph([])
        assert len(G.nodes()) == 0
        assert len(G.edges()) == 0

    def test_missing_author_skipped(self):
        G = build_graph([_post("a", None, "no author")])
        assert len(G.nodes()) == 0

    def test_mentions_create_edge(self):
        G = build_graph([
            _post("1", "alice", "Great work @bob"),
            _post("2", "bob", "Thanks alice"),
        ])
        assert G.has_edge("alice", "bob")
        assert G["alice"]["bob"]["weight"] == 1

    def test_repeated_mentions_increment_weight(self):
        G = build_graph([
            _post("1", "alice", "Great work @bob"),
            _post("2", "alice", "Also wanted to tag @bob again"),
            _post("3", "bob", "Hi"),
        ])
        assert G["alice"]["bob"]["weight"] == 2

    def test_parent_reply_creates_edge_from_parent_author(self):
        G = build_graph([
            _post("1", "alice", "original post"),
            _post("2", "bob", "replying to alice", parent_id="1"),
        ])
        assert G.has_edge("alice", "bob")

    def test_self_mention_ignored(self):
        G = build_graph([_post("1", "alice", "Hi @alice nice to meet me")])
        assert not G.has_edge("alice", "alice")
        assert len(G.edges()) == 0

    def test_missing_mention_target_ignored(self):
        G = build_graph([_post("1", "alice", "Greetings @ghost")])
        assert len(G.edges()) == 0

    def test_node_post_count_attr(self):
        G = build_graph([_post("1", "alice", "one"), _post("2", "alice", "two")])
        assert G.nodes["alice"]["post_count"] == 2


class TestCentrality:
    def test_empty_graph(self):
        assert compute_centrality(build_graph([])) == {}

    def test_single_node(self):
        G = build_graph([_post("1", "solo", "alone in the wilderness")])
        c = compute_centrality(G)
        assert "solo" in c
        for value in c["solo"].values():
            assert isinstance(value, float)

    def test_returns_all_metrics(self, sample_posts):
        G = build_graph(sample_posts)
        c = compute_centrality(G)
        for handle, metrics in c.items():
            assert set(metrics.keys()) == {
                "degree_centrality", "betweenness_centrality", "eigenvector_centrality"
            }


class TestCommunities:
    def test_empty_graph(self):
        assert detect_communities(build_graph([])) == {}

    def test_every_node_has_community(self, sample_posts):
        G = build_graph(sample_posts)
        communities = detect_communities(G)
        assert set(communities.keys()) == set(G.nodes())


class TestKols:
    def test_empty_map(self):
        assert identify_kols({}) == set()

    def test_returns_top_percent(self):
        metrics = {
            "a": {"eigenvector_centrality": 0.9},
            "b": {"eigenvector_centrality": 0.5},
            "c": {"eigenvector_centrality": 0.1},
        }
        kols = identify_kols(metrics, top_pct=0.34)
        assert kols == {"a"}


class TestAnalyzeNetwork:
    def test_empty_input(self):
        result = analyze_network([], "AI Agents")
        assert result == {"nodes": [], "edges": [], "kols": []}

    def test_single_node_no_crash(self):
        result = analyze_network([_post("1", "solo", "lonely post")], "AI Agents")
        assert len(result["nodes"]) == 1
        assert result["edges"] == []

    def test_no_relationships_no_edges(self):
        posts = [_post("1", "a", "topic one"), _post("2", "b", "topic two")]
        result = analyze_network(posts, "AI Agents")
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 0
        assert len(result["kols"]) == 1

    def test_commonly_cited_author_is_kol(self):
        posts = [
            _post("1", "alice", "original"),
            _post("2", "bob", "I agree with @alice entirely"),
            _post("3", "carol", "@alice is also right about this"),
            _post("4", "dave", "@alice summed it up best"),
        ]
        result = analyze_network(posts, "topic")
        assert "alice" in result["kols"]

    def test_sentiment_shift_recorded(self, sample_posts):
        sentiments = [
            {"post_id": "tg_1", "label": "positive"},
            {"post_id": "tg_2", "label": "neutral"},
        ]
        result = analyze_network(sample_posts, "AI Agents", sentiments)
        edge = next(
            e for e in result["edges"]
            if e["source_handle"] == "@alice" and e["target_handle"] == "@bob"
        )
        shift = json.loads(edge["sentiment_shift"])
        assert shift == {"from": "positive", "to": "neutral"}

    def test_node_fields_present(self, sample_posts):
        result = analyze_network(sample_posts, "AI Agents")
        keys = {"handle", "topic_query", "degree_centrality",
                "betweenness_centrality", "eigenvector_centrality",
                "community_id", "is_kol", "computed_at"}
        assert set(result["nodes"][0].keys()) == keys

    def test_edge_fields_present(self, sample_posts):
        result = analyze_network(sample_posts, "AI Agents")
        keys = {"source_handle", "target_handle", "weight",
                "sentiment_shift", "topic_query", "computed_at"}
        assert set(result["edges"][0].keys()) == keys