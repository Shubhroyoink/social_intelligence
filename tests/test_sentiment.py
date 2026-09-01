import pytest

from analytics.sentiment import LABELS, _map_label, analyze_posts, analyze_text


class TestLabelMapping:
    def test_legacy_labels_mapped(self):
        assert _map_label("LABEL_0") == "negative"
        assert _map_label("LABEL_1") == "neutral"
        assert _map_label("LABEL_2") == "positive"

    def test_human_labels_passthrough(self):
        assert _map_label("positive") == "positive"
        assert _map_label("negative") == "negative"
        assert _map_label("neutral") == "neutral"

    def test_unknown_label_defaults_neutral(self):
        assert _map_label("something_else") == "neutral"

    def test_labels_cover_expected_keys(self):
        for key in ("LABEL_0", "LABEL_1", "LABEL_2", "positive", "neutral", "negative"):
            assert key in LABELS


class TestAnalyzeText:
    def test_returns_label_and_scores(self, mock_sentiment):
        mock_sentiment(label="positive", score=0.9)
        result = analyze_text("I love this framework")
        assert result["label"] == "positive"
        assert result["positive_score"] == pytest.approx(0.9, abs=1e-6)

    def test_scores_sum_to_one(self, mock_sentiment):
        mock_sentiment(label="negative", score=0.8)
        result = analyze_text("This is terrible")
        total = (
            result["positive_score"]
            + result["neutral_score"]
            + result["negative_score"]
        )
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_neutral_dominant(self, mock_sentiment):
        mock_sentiment(label="neutral", score=0.85)
        result = analyze_text("The weather today")
        assert result["label"] == "neutral"


class TestAnalyzePosts:
    def test_empty_posts(self, mock_sentiment):
        mock_sentiment()
        assert analyze_posts([]) == []

    def test_returns_expected_dicts(self, mock_sentiment, sample_posts):
        mock_sentiment(label="positive", score=0.9)
        results = analyze_posts(sample_posts)
        assert len(results) == len(sample_posts)
        keys = {"post_id", "platform", "created_at", "topic_query",
                "label", "positive_score", "neutral_score",
                "negative_score", "analyzed_at"}
        assert set(results[0].keys()) == keys

    def test_post_ids_align(self, mock_sentiment, sample_posts):
        mock_sentiment()
        results = analyze_posts(sample_posts)
        assert {r["post_id"] for r in results} == {p["id"] for p in sample_posts}

    def test_batching_multiple_posts(self, mock_sentiment, sample_posts):
        mock_sentiment()
        results = analyze_posts(sample_posts, batch_size=1)
        assert len(results) == len(sample_posts)

    def test_scores_normalized_in_batch(self, mock_sentiment, sample_posts):
        mock_sentiment(label="positive", score=0.7)
        results = analyze_posts(sample_posts)
        for r in results:
            total = r["positive_score"] + r["neutral_score"] + r["negative_score"]
            assert total == pytest.approx(1.0, abs=1e-6)

    def test_extremely_long_text_does_not_crash(self, mock_sentiment):
        mock_sentiment(label="positive")
        long_text = "word " * 600
        posts = [{"id": "long", "text": long_text}]
        results = analyze_posts(posts)
        assert len(results) == 1
        assert results[0]["post_id"] == "long"

    def test_unicode_non_english_text(self, mock_sentiment):
        mock_sentiment()
        posts = [{"id": "fr", "text": "Fran\u00e7ais: j'utilise beaucoup l'IA"}]
        results = analyze_posts(posts)
        assert len(results) == 1