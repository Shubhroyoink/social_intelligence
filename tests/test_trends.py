from analytics.trends import detect_trends, extract_keywords, rising_terms


class TestExtractKeywords:
    def test_empty(self):
        assert extract_keywords([]) == []

    def test_empty_texts(self):
        assert extract_keywords([{"text": ""}, {"text": "###"}]) == []

    def test_returns_ranked_pairs(self):
        posts = [
            {"text": "AI agents are great and ml models matter a lot here"},
            {"text": "agents and models together drive this industry forward"},
        ]
        keywords = extract_keywords(posts, top_n=5)
        assert keywords
        for kw, score in keywords:
            assert isinstance(kw, str)
            assert isinstance(score, float)
        # sorted descending by score
        scores = [s for _, s in keywords]
        assert scores == sorted(scores, reverse=True)


class TestDetectTrends:
    def test_empty(self):
        assert detect_trends([], "AI Agents") == []

    def test_single_post(self):
        posts = [{
            "text": "AI agents are the future of machine learning",
            "created_at": "2026-08-01T10:00:00+00:00",
        }]
        result = detect_trends(posts, "AI Agents")
        assert result

    def test_returns_schema_rows(self):
        posts = [{
            "text": "AI agents agents agents are trending",
            "created_at": "2026-08-01T10:00:00+00:00",
        }]
        row = detect_trends(posts, "AI Agents", top_n=3)[0]
        assert set(row.keys()) == {
            "topic_query", "keyword", "frequency",
            "window_start", "window_end", "analyzed_at",
        }
        assert row["topic_query"] == "AI Agents"


class TestRisingTerms:
    def test_empty(self):
        assert rising_terms([]) == []

    def test_returns_terms(self):
        posts = [
            {"text": "alpha term here", "created_at": "2026-08-01T10:00:00+00:00"},
            {"text": "beta term there", "created_at": "2026-08-02T10:00:00+00:00"},
        ]
        terms = rising_terms(posts, window_size_hours=1, top_n=5)
        assert isinstance(terms, list)

    def test_existing_posts_non_mutating(self):
        posts = [{"text": "stable", "created_at": "2026-08-01T10:00:00+00:00"}]
        copy = list(posts)
        rising_terms(posts)
        assert posts == copy