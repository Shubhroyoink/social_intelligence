import json

import pytest

from analytics.emotions import detect_sarcasm, detect_stance


class TestSarcasm:
    @pytest.mark.parametrize("text,sentiment,expected", [
        ("Oh great, another outage. Just wonderful.", "negative", True),
        ("Sure... what a surprise, it failed again.", "negative", True),
        ("Great, thanks a lot for breaking the API.", "negative", True),
        ("This is the worst implementation ever seen.", "negative", False),
        ("I love this feature, it works perfectly!", "positive", False),
        ("The report was submitted on time.", "neutral", False),
        ("", "neutral", False),
        (None, "neutral", False),
    ])
    def test_detect(self, text, sentiment, expected):
        assert detect_sarcasm(text, sentiment) is expected

    def test_non_english_no_crash(self):
        assert detect_sarcasm("C'est magnifique, vraiment génial !", "positive") is False


class TestStance:
    @pytest.mark.parametrize("text,sentiment,expected", [
        ("I fully support this great decision", "positive", "supportive"),
        ("Love this, amazing work!", "positive", "supportive"),
        ("This is wrong and totally terrible", "negative", "against"),
        ("I disagree and oppose this rollout", "negative", "against"),
        ("The weather is fine today", "neutral", "neutral"),
    ])
    def test_detect(self, text, sentiment, expected):
        assert detect_stance(text, sentiment) == expected

    def test_falls_back_on_sentiment_when_no_keywords(self):
        assert detect_stance("Just a statement with no cues", "positive") == "supportive"
        assert detect_stance("Just a statement with no cues", "negative") == "against"

    def test_empty_text(self):
        assert detect_stance("", "neutral") == "neutral"

    def test_non_english_no_crash(self):
        result = detect_stance("Je ne suis pas d'accord avec cela", "negative")
        assert result in {"supportive", "against", "neutral"}


class TestAnalyzeEmotions:
    def test_empty_posts(self, mock_emotions):
        mock_emotions()
        from analytics.emotions import analyze_emotions
        assert analyze_emotions([]) == []

    def test_returns_expected_dicts(self, mock_emotions, sample_posts):
        mock_emotions(label="joy", score=0.9)
        from analytics.emotions import analyze_emotions
        results = analyze_emotions(sample_posts)
        assert len(results) == len(sample_posts)
        keys = {"post_id", "primary_emotion", "emotion_json",
                "sarcasm_flag", "stance", "analyzed_at"}
        assert set(results[0].keys()) == keys

    def test_primary_emotion_is_max_score(self, mock_emotions, sample_posts):
        mock_emotions(label="fear", score=0.95)
        from analytics.emotions import analyze_emotions
        results = analyze_emotions(sample_posts)
        for r in results:
            scores = json.loads(r["emotion_json"])
            assert scores[r["primary_emotion"]] == pytest.approx(0.95, abs=1e-6)

    def test_emotion_json_is_valid(self, mock_emotions, sample_posts):
        mock_emotions()
        from analytics.emotions import analyze_emotions
        for r in analyze_emotions(sample_posts):
            scores = json.loads(r["emotion_json"])
            assert set(scores.keys()) == {
                "anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"
            }

    def test_flags_are_typed(self, mock_emotions, sample_posts):
        mock_emotions()
        from analytics.emotions import analyze_emotions
        for r in analyze_emotions(sample_posts):
            assert r["sarcasm_flag"] in (0, 1)
            assert r["stance"] in {"supportive", "against", "neutral"}

    def test_extremely_long_text(self, mock_emotions):
        mock_emotions()
        from analytics.emotions import analyze_emotions
        long_text = "excited " * 600
        results = analyze_emotions([{"id": "long", "text": long_text}])
        assert len(results) == 1

    def test_non_english_text(self, mock_emotions):
        mock_emotions(label="neutral")
        from analytics.emotions import analyze_emotions
        results = analyze_emotions([{"id": "de", "text": "Das ist ein deutscher Text"}])
        assert len(results) == 1