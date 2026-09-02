"""Collector-level tests that are free of live network calls.

Post IDs built from platform ids are validated for determinism across
re-collection and for the absence of the old `x_None`/salted-hash bugs.
"""
import sys
from types import SimpleNamespace

import pytest

import collectors.x_collector as x_collector
import collectors.youtube_collector as youtube_collector
from normalizer.normalizer import normalize_posts, normalize_timestamp


class TestXCollectorIds:
    def test_missing_id_gets_stable_content_hash(self, monkeypatch):
        class FakeNitter:
            def get_tweets(self, query, mode, number):
                return {"tweets": [
                    {"text": "tweet one about AI agents"},
                    {"id": None, "text": "tweet two about AI agents"},
                    {"id": 123, "text": "tweet three about AI agents"},
                    {"id": "", "text": "tweet four about AI agents"},
                ]}

        monkeypatch.setattr(x_collector, "Nitter", FakeNitter)
        posts = x_collector.collect_x_search("AI Agents", "AI Agents")

        ids = [p["id"] for p in posts]
        assert len(ids) == 4
        # Never a literal "None" id (the old collapse-to-one-row bug).
        assert all("None" not in i for i in ids)
        # Falsey platform ids fall back to content hash; platform prefix kept.
        assert ids[1].startswith("x_")
        assert ids[3].startswith("x_")
        # Truthy platform id used verbatim.
        assert ids[2] == "x_123"
        # Same content -> same id across independent collectors.
        other = x_collector.collect_x_search("AI Agents", "AI Agents")
        assert other[1]["id"] == ids[1]
        assert other[3]["id"] == ids[3]

    def test_distinct_texts_receive_distinct_ids(self, monkeypatch):
        class FakeNitter:
            def get_tweets(self, query, mode, number):
                return {"tweets": [
                    {"text": "unique text alpha"},
                    {"text": "unique text beta"},
                ]}

        monkeypatch.setattr(x_collector, "Nitter", FakeNitter)
        posts = x_collector.collect_x_search("AI Agents", "AI Agents")
        assert len({p["id"] for p in posts}) == 2


class TestYouTubeCollectorIds:
    def _install_fake_ytdlp(self, monkeypatch):
        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=True):
                return {
                    "id": "VID123",
                    "comments": [
                        {"id": "c1", "text": "first comment", "author": "alice",
                         "timestamp": 1783000000},
                        {"id": None, "text": "second comment", "author": "bob",
                         "timestamp": "2026-08-01 10:00:00"},
                        {"text": "dup comment", "author": "carol"},
                        {"text": "dup comment", "author": "carol"},
                    ],
                }

        monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYDL))

    def test_timestamps_parsed_by_shared_normalizer(self, monkeypatch):
        self._install_fake_ytdlp(monkeypatch)
        posts = youtube_collector.collect_youtube_comments(
            "https://www.youtube.com/watch?v=VID123", "AI Agents"
        )
        # Space-separated naive timestamps must parse to UTC, not fall back to "now".
        assert posts[0]["created_at"] == normalize_timestamp(1783000000)
        assert posts[1]["created_at"] == "2026-08-01T10:00:00+00:00"

    def test_missing_comment_id_gets_stable_hash(self, monkeypatch):
        self._install_fake_ytdlp(monkeypatch)
        posts = youtube_collector.collect_youtube_comments(
            "https://www.youtube.com/watch?v=VID123", "AI Agents"
        )
        ids = [p["id"] for p in posts]
        assert len(ids) == 4
        assert all("None" not in i for i in ids)
        assert ids[0] == "yt_c1"
        assert ids[1].startswith("yt_")
        assert len(ids[1]) == 3 + 16

    def test_duplicate_content_collapses_to_same_id(self, monkeypatch):
        self._install_fake_ytdlp(monkeypatch)
        posts = youtube_collector.collect_youtube_comments(
            "https://www.youtube.com/watch?v=VID123", "AI Agents"
        )
        assert posts[2]["id"] == posts[3]["id"]


class TestXCollectorTimestamps:
    def test_created_at_uses_shared_normalizer(self, monkeypatch):
        class FakeNitter:
            def get_tweets(self, query, mode, number):
                return {"tweets": [
                    {"text": "a tweet", "timestamp": 1783000000,
                     "user": {"name": "alice"}},
                    {"text": "another tweet", "timestamp": "2026-08-01 10:00:00",
                     "user": {"name": "bob"}},
                ]}

        monkeypatch.setattr(x_collector, "Nitter", FakeNitter)
        posts = x_collector.collect_x_search("AI Agents", "AI Agents")
        assert posts[0]["created_at"] == normalize_timestamp(1783000000)
        assert posts[1]["created_at"] == "2026-08-01T10:00:00+00:00"


class TestYouTubeUrlValidation:
    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/abc123",
    ])
    def test_accepts_valid_urls(self, url):
        assert youtube_collector._validate_youtube_url(url) is None

    @pytest.mark.parametrize("url", [
        "file:///etc/passwd",
        "ftp://youtube.com/watch?v=x",
        "https://evil.example.com/watch?v=x",
        "https://localhost:8000/watch?v=x",
        "https://192.168.1.1/watch?v=x",
        "not a url at all",
        "youtube.com/watch?v=x",  # no scheme
    ])
    def test_rejects_invalid_urls(self, url):
        with pytest.raises(ValueError):
            youtube_collector._validate_youtube_url(url)

    def test_collect_rejects_invalid_url_before_extraction(self, monkeypatch):
        # Validation must run before yt-dlp is reached; force it to explode
        # if it ever gets there.
        def _fail_url(*args, **kwargs):
            raise AssertionError("yt-dlp should never see a non-YouTube URL")

        monkeypatch.setitem(
            sys.modules, "yt_dlp",
            SimpleNamespace(YoutubeDL=_fail_url),
        )
        with pytest.raises(ValueError):
            youtube_collector.collect_youtube_comments("file:///etc/passwd", "AI Agents")


class TestTelegramNormalization:
    def test_raw_json_key_dropped_and_text_cleaned(self):
        raw = {
            "id": "@chan_1",
            "platform": "telegram",
            "author_id": "u1",
            "author_handle": "@chan",
            "text": "Amazing stuff @bob https://example.com",
            "created_at": "2026-08-01T10:00:00+00:00",
            "collected_at": "2026-08-01T11:00:00+00:00",
            "parent_id": None,
            "topic_query": "AI Agents",
            "reactions": 12, "shares": 3, "replies": None, "views": 5,
            "raw_json": '{"unused": true}',
        }
        normalized = normalize_posts([raw])[0]
        assert "raw_json" not in normalized
        assert normalized["raw_text"] == raw["text"]
        assert "@bob" not in normalized["text"]
        assert "https://example.com" not in normalized["text"]


class TestTelegramCredentials:
    def test_missing_env_raises_clear_error(self, monkeypatch):
        import collectors.telegram_collector as tg_collector

        monkeypatch.delenv("TG_API_ID", raising=False)
        monkeypatch.delenv("TG_API_HASH", raising=False)
        with pytest.raises(RuntimeError, match="TG_API_ID"):
            tg_collector._credentials()

    def test_present_env_returns_values(self, monkeypatch):
        import collectors.telegram_collector as tg_collector

        monkeypatch.setenv("TG_API_ID", "12345")
        monkeypatch.setenv("TG_API_HASH", "hashvalue")
        assert tg_collector._credentials() == ("12345", "hashvalue")