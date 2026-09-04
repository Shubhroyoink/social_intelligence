"""Tests for the narrative-report stage: data assembly, Gemini wiring,
template fallback, DB persistence and markdown file output."""
import json
import os
import re
from types import SimpleNamespace

import pytest

import database.db as db
from analytics import narrative


def _sentiments():
    return [
        {"post_id": "tg_1", "platform": "telegram", "label": "positive",
         "positive_score": 0.8, "neutral_score": 0.1, "negative_score": 0.1,
         "created_at": "2026-08-01T10:00:00+00:00", "topic_query": "AI Agents",
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
        {"post_id": "tg_2", "platform": "telegram", "label": "neutral",
         "positive_score": 0.1, "neutral_score": 0.8, "negative_score": 0.1,
         "created_at": "2026-08-02T10:00:00+00:00", "topic_query": "AI Agents",
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
        {"post_id": "x_1", "platform": "x", "label": "negative",
         "positive_score": 0.1, "neutral_score": 0.1, "negative_score": 0.8,
         "created_at": "2026-08-03T10:00:00+00:00", "topic_query": "AI Agents",
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
    ]


def _emotions():
    return [
        {"post_id": "tg_1", "primary_emotion": "joy", "stance": "supportive",
         "sarcasm_flag": 0, "emotion_json": '{"joy": 0.9}',
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
        {"post_id": "tg_2", "primary_emotion": "neutral", "stance": "neutral",
         "sarcasm_flag": 0, "emotion_json": '{"neutral": 0.9}',
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
        {"post_id": "x_1", "primary_emotion": "anger", "stance": "against",
         "sarcasm_flag": 1, "emotion_json": '{"anger": 0.9}',
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
    ]


def _demographics():
    return [
        {"post_id": "tg_1", "language": "en", "geo_hint": "India",
         "interests_json": '["ai_ml", "technology"]',
         "inferred_at": "2026-08-03T12:00:00+00:00"},
        {"post_id": "tg_2", "language": "en", "geo_hint": None,
         "interests_json": '["ai_ml"]', "inferred_at": "2026-08-03T12:00:00+00:00"},
        {"post_id": "x_1", "language": "en", "geo_hint": "USA",
         "interests_json": '["general"]', "inferred_at": "2026-08-03T12:00:00+00:00"},
    ]


def _trends():
    return [
        {"topic_query": "AI Agents", "keyword": "agent", "frequency": 5,
         "window_start": "2026-08-01T00:00:00+00:00",
         "window_end": "2026-08-02T00:00:00+00:00",
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
        {"topic_query": "AI Agents", "keyword": "llm", "frequency": 4,
         "window_start": "2026-08-01T00:00:00+00:00",
         "window_end": "2026-08-02T00:00:00+00:00",
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
        {"topic_query": "AI Agents", "keyword": "agent", "frequency": 1,
         "window_start": "2026-07-31T00:00:00+00:00",
         "window_end": "2026-08-01T00:00:00+00:00",
         "analyzed_at": "2026-08-03T12:00:00+00:00"},
    ]


def _network():
    return {
        "nodes": [
            {"handle": "@alice", "is_kol": 1, "community_id": 0,
             "eigenvector_centrality": 0.9},
            {"handle": "@bob", "is_kol": 0, "community_id": 0,
             "eigenvector_centrality": 0.1},
            {"handle": "@carol", "is_kol": 1, "community_id": 1,
             "eigenvector_centrality": 0.8},
        ],
        "edges": [{"source_handle": "@alice", "target_handle": "@bob", "weight": 1}],
        "kols": ["@alice", "@carol"],
    }


class TestBuildReportData:
    def test_aggregates_every_stage(self, sample_posts):
        data = narrative.build_report_data(
            sample_posts, sentiments=_sentiments(), emotions=_emotions(),
            demographics=_demographics(), trends=_trends(), network=_network(),
            topic_query="AI Agents",
        )
        assert data["total_posts"] == 3
        assert data["platforms"] == {"telegram": 2, "x": 1}
        assert data["topic_query"] == "AI Agents"

        assert data["sentiment"]["counts"] == {"positive": 1, "neutral": 1, "negative": 1}
        assert data["sentiment"]["rates"]["positive"] == round(1 / 3 * 100, 1)
        assert data["sentiment"]["by_platform"]["x"] == {"positive": 0.0, "neutral": 0.0,
                                                         "negative": 100.0}

        assert data["emotions"]["counts"] == {"joy": 1, "neutral": 1, "anger": 1}
        assert data["emotions"]["stance_counts"] == {"supportive": 1, "neutral": 1,
                                                     "against": 1}
        assert data["emotions"]["sarcasm_pct"] == round(1 / 3 * 100, 1)

        assert data["trends"]["top_keywords"][0] == {"keyword": "agent", "frequency": 5}
        assert data["demographics"]["languages"] == {"en": 3}
        assert data["demographics"]["interests"]["ai_ml"] == 2

        assert data["network"]["node_count"] == 3
        assert data["network"]["edge_count"] == 1
        assert data["network"]["kol_handles"] == ["@alice", "@carol"]

    def test_empty_inputs_do_not_crash(self):
        data = narrative.build_report_data([], topic_query="AI Agents")
        assert data["total_posts"] == 0
        assert data["platforms"] == {}
        assert data["sentiment"]["rates"] == {"positive": 0.0, "neutral": 0.0,
                                              "negative": 0.0}
        assert data["network"]["kol_handles"] == []


class TestTemplateReport:
    def test_contains_all_section_headings(self, sample_posts):
        data = narrative.build_report_data(
            sample_posts, sentiments=_sentiments(), emotions=_emotions(),
            demographics=_demographics(), trends=_trends(), network=_network(),
            topic_query="AI Agents",
        )
        report = narrative._template_report(data)
        for section in narrative.REPORT_SECTIONS:
            assert f"## {section}" in report

    def test_works_with_only_posts(self, sample_posts):
        data = narrative.build_report_data(sample_posts, topic_query="AI Agents")
        report = narrative._template_report(data)
        assert report.strip()


class TestGenerateNarrative:
    def test_returns_none_without_posts(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        result = narrative.generate_narrative([], topic_query="AI Agents")
        assert result is None

    def test_template_fallback_when_no_key(self, sample_posts, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        result = narrative.generate_narrative(sample_posts, topic_query="AI Agents")
        assert result["backend"] == "template"
        assert result["model"] is None
        assert result["topic_query"] == "AI Agents"
        assert "## Bottom Line" in result["report_markdown"]
        assert result["stats_json"] and json.loads(result["stats_json"])["total_posts"] == 3

    def test_gemini_success_path(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "fake-key")
        monkeypatch.delenv("LLM_MODEL", raising=False)

        import requests

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": "GEMINI REPORT"}]}}]}

        calls = {}

        def fake_post(url, json, timeout):
            calls["url"] = url
            calls["body"] = json
            return FakeResponse()

        monkeypatch.setattr(requests, "post", fake_post)
        result = narrative.generate_narrative([{
            "id": "p1", "platform": "x", "author_id": "u", "author_handle": "@a",
            "text": "example post", "created_at": "2026-08-01T10:00:00+00:00",
            "topic_query": "AI Agents",
        }], topic_query="AI Agents")

        assert result["backend"] == "gemini"
        assert result["model"] == narrative.DEFAULT_MODEL
        assert result["report_markdown"] == "GEMINI REPORT"
        assert narrative.DEFAULT_MODEL in calls["url"]
        assert "contents" in calls["body"]

    def test_gemini_failure_falls_back_to_template(self, sample_posts, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "fake-key")

        import requests

        def explode(*args, **kwargs):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(requests, "post", explode)
        result = narrative.generate_narrative(sample_posts, topic_query="AI Agents")
        assert result["backend"] == "template"
        assert result["model"] is None
        assert "## Executive Summary" in result["report_markdown"]


class TestPersistence:
    def test_save_and_get_latest_first(self, test_db):
        early = "2026-09-05T10:00:00+00:00"
        late = "2026-09-05T11:00:00+00:00"
        first = {
            "topic_query": "AI Agents", "backend": "template", "model": None,
            "stats_json": "{}", "report_markdown": "first report",
            "created_at": early,
        }
        second = {**first, "report_markdown": "second report", "created_at": late}
        db.save_narrative(first)
        db.save_narrative(second)

        loaded = db.get_narratives(topic_query="AI Agents")
        assert len(loaded) == 2
        assert [r["report_markdown"] for r in loaded] == ["second report", "first report"]

        assert db.get_narratives(topic_query="Other") == []
        assert db.get_narratives(limit=1)[0]["report_markdown"] == "second report"

    def test_write_report_file(self, tmp_path):
        path = narrative.write_report_file(
            "AI Agents!", "# report", created_at="2026-09-05T12:00:00+00:00",
            output_dir=str(tmp_path),
        )
        assert os.path.basename(path) == "ai-agents_20260905120000.md"
        assert os.path.isfile(path)
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == "# report"


class TestCallGemini:
    def test_error_messages_redact_api_key(self, monkeypatch):
        import requests

        secret = "SUPER-SECRET-KEY"

        def explode(*args, **kwargs):
            raise requests.exceptions.ConnectionError(
                f"failed for url: "
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/gemini-2.5-flash:generateContent?key={secret}"
            )

        monkeypatch.setattr(requests, "post", explode)
        with pytest.raises(RuntimeError, match=r"\[REDACTED\]"):
            narrative._call_gemini("prompt", secret)
        with pytest.raises(RuntimeError) as excinfo:
            narrative._call_gemini("prompt", secret)
        assert secret not in str(excinfo.value)

    def test_retries_then_succeeds_on_transient_5xx(self, monkeypatch):
        import requests
        from requests.exceptions import HTTPError

        monkeypatch.setattr("time.sleep", lambda s: None)
        calls = {"n": 0}

        def flaky(url, json, timeout):
            calls["n"] += 1
            if calls["n"] < 3:
                err = HTTPError("Server Error")
                err.response = SimpleNamespace(status_code=500)
                raise err
            resp = SimpleNamespace()
            resp.raise_for_status = lambda: None
            resp.json = lambda: {"candidates": [{"content": {"parts": [{"text": "OK RETRY"}]}}]}
            return resp

        monkeypatch.setattr(requests, "post", flaky)
        assert narrative._call_gemini("prompt", "key") == "OK RETRY"
        assert calls["n"] == 3

    def test_gives_up_after_three_5xx(self, monkeypatch):
        import requests
        from requests.exceptions import HTTPError

        monkeypatch.setattr("time.sleep", lambda s: None)
        calls = {"n": 0}

        def fail(url, json, timeout):
            calls["n"] += 1
            err = HTTPError("Server Error")
            err.response = SimpleNamespace(status_code=503)
            raise err

        monkeypatch.setattr(requests, "post", fail)
        with pytest.raises(RuntimeError, match="Gemini request failed"):
            narrative._call_gemini("prompt", "key")
        assert calls["n"] == 3

    def test_non_5xx_errors_do_not_retry(self, monkeypatch):
        import requests

        monkeypatch.setattr("time.sleep", lambda s: None)
        calls = {"n": 0}

        def fail(url, json, timeout):
            calls["n"] += 1
            raise requests.exceptions.HTTPError("400 Client Error")

        monkeypatch.setattr(requests, "post", fail)
        with pytest.raises(RuntimeError):
            narrative._call_gemini("prompt", "key")
        assert calls["n"] == 1


class TestMakePrompt:
    def test_prompt_contains_data_and_section_rules(self):
        data = {"total_posts": 5, "topic_query": "AI Agents"}
        prompt = narrative.make_prompt(data)
        assert "total_posts" in prompt
        assert "Executive Summary" in prompt
        assert re.search(r"Your are|You are", prompt)