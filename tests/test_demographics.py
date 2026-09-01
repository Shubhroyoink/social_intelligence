import json

import pytest

from analytics.demographics import (
    analyze_demographics,
    extract_geo_hint,
    infer_interests,
)


class TestLanguageDetection:
    def test_english(self):
        from analytics.demographics import _detect_language
        assert _detect_language(
            "The quick brown fox jumps over the lazy dog many times today"
        ) == "en"

    def test_french(self):
        from analytics.demographics import _detect_language
        assert _detect_language(
            "Bonjour tout le monde, comment allez-vous aujourd'hui mon ami"
        ) == "fr"

    def test_spanish(self):
        from analytics.demographics import _detect_language
        assert _detect_language(
            "Hola amigos, hoy vamos a aprender mucho sobre tecnología avanzada"
        ) == "es"

    def test_garbage_returns_unknown(self):
        from analytics.demographics import _detect_language
        assert _detect_language("12345 ==== ####") == "unknown"

    def test_empty_returns_unknown(self):
        from analytics.demographics import _detect_language
        assert _detect_language("") == "unknown"


class TestGeoHint:
    @pytest.mark.parametrize("text,expected", [
        ("I am based in New York", "New York"),
        ("Living in NYC for 5 years", "New York"),
        ("Check out my London office", "London/UK"),
        ("Team is expanding in India", "India"),
        ("From Mumbai originally", "India"),
        ("Working remotely in Singapore", "Singapore"),
        ("Tokyoo is a city", None),
    ])
    def test_detect(self, text, expected):
        assert extract_geo_hint(text) == expected

    def test_empty_text(self):
        assert extract_geo_hint("") is None

    def test_none_text(self):
        assert extract_geo_hint(None) is None

    def test_geo_from_author_handle(self):
        assert extract_geo_hint("uk based firm", "@london_dev") == "London/UK"

    def test_no_geo_present(self):
        assert extract_geo_hint("just a plain sentence about code") is None


class TestInterests:
    def test_ai_ml_detected(self):
        interests = infer_interests("talking about llm gpt models and transformers")
        assert "ai_ml" in interests

    def test_finance_detected(self):
        interests = infer_interests("investing stocks trading and crypto markets")
        assert "finance" in interests

    def test_general_when_no_keywords(self):
        assert infer_interests("completely unrelated everyday chatter") == ["general"]

    def test_returns_max_three(self):
        text = (
            "software developer building ai models with api and cloud "
            "infrastructure and investing in crypto and defi markets"
        )
        assert len(infer_interests(text)) <= 3

    def test_empty_text(self):
        assert infer_interests("") == ["general"]

    def test_emoji_and_unicode(self):
        result = infer_interests("café déjà vu foo bar baz qux")
        assert isinstance(result, list)


class TestAnalyzeDemographics:
    def test_empty(self):
        assert analyze_demographics([]) == []

    def test_expected_keys(self, sample_posts):
        results = analyze_demographics(sample_posts)
        assert len(results) == len(sample_posts)
        keys = {"post_id", "language", "geo_hint", "interests_json", "inferred_at"}
        assert set(results[0].keys()) == keys

    def test_interests_json_serializable(self, sample_posts):
        for r in analyze_demographics(sample_posts):
            parsed = json.loads(r["interests_json"])
            assert isinstance(parsed, list)
            assert all(isinstance(i, str) for i in parsed)

    def test_missing_author_ok(self):
        posts = [{
            "id": "noid",
            "text": "no author handle here at all",
            "author_handle": None,
        }]
        results = analyze_demographics(posts)
        assert len(results) == 1
        assert results[0]["post_id"] == "noid"

    def test_language_and_geo_populated(self):
        posts = [{
            "id": "a",
            "text": "Great progress happening London based team",
            "author_handle": "eg",
        }]
        results = analyze_demographics(posts)
        assert results[0]["language"] == "en"
        assert results[0]["geo_hint"] == "London/UK"