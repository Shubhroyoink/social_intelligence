import pytest

import collectors.youtube_collector as youtube_collector
from database.db import (
    get_fetched_youtube_video_ids,
    upsert_youtube_video,
)


TOPIC = "AI Agents"


def _video(video_id, title=None):
    return {
        "video_id": video_id,
        "title": title or f"Video {video_id}",
        "channel": "Some Channel",
        "description": "desc",
        "published_at": "2026-08-01T10:00:00+00:00",
    }


def _fake_comment_post(video_id):
    return {
        "id": f"yt_{video_id}_c1",
        "platform": "youtube",
        "author_id": "u1",
        "author_handle": "@viewer",
        "text": f"comment on {video_id}",
        "created_at": "2026-08-01T11:00:00+00:00",
        "collected_at": "2026-08-01T12:00:00+00:00",
        "parent_id": None,
        "topic_query": TOPIC,
        "reactions": 1,
        "shares": 0,
        "replies": 0,
        "views": None,
    }


class FakeExtractor:
    """Records how many comment-fetches a topic run attempts."""

    def __init__(self):
        self.calls = []

    def __call__(self, video_id, topic_query, limit=100, api_key=None):
        self.calls.append(video_id)
        return [_fake_comment_post(video_id)]


@pytest.fixture
def fake_extractor(monkeypatch):
    extractor = FakeExtractor()
    monkeypatch.setattr(
        youtube_collector, "_collect_comments_for_video", extractor
    )
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    return extractor


class TestCollectYouTubeTopic:
    def test_first_run_fetches_all_new_videos(self, monkeypatch, fake_extractor):
        monkeypatch.setattr(
            youtube_collector, "search_videos",
            lambda *a, **k: [_video("V1"), _video("V2"), _video("V3")],
        )
        posts = youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        assert len(posts) == 3
        assert fake_extractor.calls == ["V1", "V2", "V3"]
        assert set(get_fetched_youtube_video_ids(TOPIC)) == {"V1", "V2", "V3"}

    def test_second_run_skips_cached_videos(self, monkeypatch, fake_extractor):
        videos = [_video("V1"), _video("V2"), _video("V3")]
        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: videos)

        youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        assert fake_extractor.calls == ["V1", "V2", "V3"]

        posts = youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        assert posts == []
        assert fake_extractor.calls == ["V1", "V2", "V3"]
        assert set(get_fetched_youtube_video_ids(TOPIC)) == {"V1", "V2", "V3"}

    def test_only_new_video_is_fetched_next_run(self, monkeypatch, fake_extractor):
        first = [_video("V1"), _video("V2")]
        later = [_video("V1"), _video("V2"), _video("V4")]

        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: first)
        youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)

        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: later)
        posts = youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)

        assert fake_extractor.calls == ["V1", "V2", "V4"]
        assert [p["id"] for p in posts] == ["yt_V4_c1"]
        assert set(get_fetched_youtube_video_ids(TOPIC)) == {"V1", "V2", "V4"}

    def test_refresh_refetches_cached_videos(self, monkeypatch, fake_extractor):
        videos = [_video("V1"), _video("V2")]
        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: videos)

        youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        posts = youtube_collector.collect_youtube_topic(
            TOPIC, max_videos=3, refresh=True
        )
        assert len(posts) == 2
        assert fake_extractor.calls == ["V1", "V2", "V1", "V2"]

    def test_budget_exhausted_skips_search(self, monkeypatch, fake_extractor):
        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: [_video("V1")])
        monkeypatch.setattr(youtube_collector, "quota_remaining", lambda: 0)

        posts = youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        assert posts == []
        assert fake_extractor.calls == []

    def test_failed_fetch_is_not_marked_cached(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
        videos = [_video("V1"), _video("V2")]
        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: videos)

        calls = []

        def flaky(video_id, topic_query, limit=100, api_key=None):
            calls.append(video_id)
            if video_id == "V2":
                raise RuntimeError("boom")
            return [_fake_comment_post(video_id)]

        monkeypatch.setattr(youtube_collector, "_collect_comments_for_video", flaky)
        posts = youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        assert [p["id"] for p in posts] == ["yt_V1_c1"]
        assert calls == ["V1", "V2"]
        assert get_fetched_youtube_video_ids(TOPIC) == ["V1"]

        posts = youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        assert posts == []
        assert calls == ["V1", "V2", "V2"]
        assert get_fetched_youtube_video_ids(TOPIC) == ["V1"]

    def test_quota_exceeded_aborts_remaining(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
        videos = [_video("V1"), _video("V2"), _video("V3")]
        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: videos)

        def quota_bomb(video_id, topic_query, limit=100, api_key=None):
            raise youtube_collector.YouTubeQuotaExceededError("used up")

        monkeypatch.setattr(youtube_collector, "_collect_comments_for_video", quota_bomb)
        posts = youtube_collector.collect_youtube_topic(TOPIC, max_videos=3)
        assert posts == []
        assert get_fetched_youtube_video_ids(TOPIC) == []

    def test_no_videos_found_returns_empty(self, monkeypatch, fake_extractor):
        monkeypatch.setattr(youtube_collector, "search_videos", lambda *a, **k: [])
        assert youtube_collector.collect_youtube_topic(TOPIC, max_videos=3) == []

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="YOUTUBE_API_KEY"):
            youtube_collector.collect_youtube_topic(TOPIC)


class TestYouTubePipelineIntegration:
    def test_missing_key_warns_and_continues(self, monkeypatch):
        import run_pipeline

        posts = run_pipeline.run(
            topic_query=TOPIC,
            telegram_channels=[],
            x_queries=[],
            youtube_urls=None,
            telegram_limit=1,
            x_limit=1,
            youtube_search=True,
            do_collect=True,
            do_analyze=False,
        )
        assert posts == []

    def test_no_youtube_search_disables_discovery(self, monkeypatch):
        import run_pipeline

        posts = run_pipeline.run(
            topic_query=TOPIC,
            telegram_channels=[],
            x_queries=[],
            youtube_urls=None,
            youtube_search=False,
            do_collect=True,
            do_analyze=False,
        )
        assert posts == []


class TestYouTubeVideoCache:
    def test_upsert_preserves_first_seen_at(self):
        upsert_youtube_video(_video("V1"), TOPIC)
        first_row = self._row("V1")

        upsert_youtube_video(
            _video("V1"), TOPIC,
            last_fetched_at="2099-01-01T00:00:00+00:00", comments_count=7,
        )
        second_row = self._row("V1")

        assert second_row["first_seen_at"] == first_row["first_seen_at"]
        assert second_row["last_fetched_at"] == "2099-01-01T00:00:00+00:00"
        assert second_row["comments_count"] == 7

    def test_upsert_refreshes_discovery_metadata(self):
        import datetime
        from database.db import DB_PATH, sqlite3

        upsert_youtube_video(_video("V1", title="Old"), TOPIC)
        upsert_youtube_video(_video("V1", title="New title"), TOPIC)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM youtube_videos WHERE video_id='V1' AND topic_query=?",
            (TOPIC,),
        ).fetchone()
        conn.close()
        assert row["title"] == "New title"

    @staticmethod
    def _row(video_id):
        from database.db import DB_PATH, sqlite3

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM youtube_videos WHERE video_id=? AND topic_query=?",
            (video_id, TOPIC),
        ).fetchone()
        conn.close()
        return row

    def test_get_fetched_filters_unfetched(self):
        upsert_youtube_video(_video("V1"), TOPIC)
        upsert_youtube_video(
            _video("V2"), TOPIC,
            last_fetched_at="2099-01-01T00:00:00+00:00", comments_count=3,
        )
        assert get_fetched_youtube_video_ids(TOPIC) == ["V2"]