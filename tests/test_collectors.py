"""Collector-level tests that are free of live network calls.

Post IDs built from platform ids are validated for determinism across
re-collection and for the absence of the old `x_None`/salted-hash bugs.
"""
import sys
from types import SimpleNamespace

import pytest

import collectors.x_collector as x_collector
import collectors.youtube_collector as youtube_collector
from normalizer.normalizer import normalize_posts


def _fake_tweets_payload(tweets, lookup_status="found", next_cursor=None):
    """Minimal Social Fetch timeline envelope."""
    return {
        "data": {
            "lookupStatus": lookup_status,
            "profile": {"handle": "alice", "displayName": "Alice"},
            "tweets": tweets,
            "page": {"hasMore": bool(next_cursor), "nextCursor": next_cursor},
        },
        "meta": {"creditsCharged": 1},
    }


class TestXCollectorIds:
    """Social Fetch returns real tweet ids, but the mapper must still fall back
    to a deterministic content hash when one is missing."""

    def test_missing_id_gets_stable_content_hash(self, monkeypatch):
        tweets = [
            {"id": "1", "text": "tweet one about AI agents"},
            {"id": None, "text": "tweet two about AI agents"},
            {"id": 123, "text": "tweet three about AI agents"},
            {"id": "", "text": "tweet four about AI agents"},
        ]
        for t in tweets:
            t["author"] = {"handle": "alice", "platformUserId": "u1"}

        monkeypatch.setattr(
            x_collector, "_get", lambda *a, **k: _fake_tweets_payload(tweets)
        )
        posts, status, _ = x_collector.collect_x_profile_tweets("alice", "AI Agents", api_key="k")

        assert status == "found"
        ids = [p["id"] for p in posts]
        assert len(ids) == 4
        # Never a literal "None" id (the old collapse-to-one-row bug).
        assert all("None" not in i for i in ids)
        # Falsey platform ids fall back to content hash; platform prefix kept.
        assert ids[1].startswith("x_")
        assert ids[3].startswith("x_")
        # Truthy platform id used verbatim.
        assert ids[2] == "x_123"
        # Same content -> same id across independent collections.
        other, _, _ = x_collector.collect_x_profile_tweets("alice", "AI Agents", api_key="k")
        assert other[1]["id"] == ids[1]
        assert other[3]["id"] == ids[3]

    def test_distinct_texts_receive_distinct_ids(self, monkeypatch):
        tweets = [
            {"id": None, "text": "unique text alpha",
             "author": {"handle": "alice"}},
            {"id": None, "text": "unique text beta",
             "author": {"handle": "alice"}},
        ]
        monkeypatch.setattr(
            x_collector, "_get", lambda *a, **k: _fake_tweets_payload(tweets)
        )
        posts, _, _ = x_collector.collect_x_profile_tweets("alice", "AI Agents", api_key="k")
        assert len({p["id"] for p in posts}) == 2

    def test_blank_tweets_are_dropped(self, monkeypatch):
        tweets = [
            {"id": "1", "text": "keep me", "author": {"handle": "alice"}},
            {"id": "2", "text": "   ", "author": {"handle": "alice"}},
            {"id": "3", "text": "no author", "author": {}},
        ]
        monkeypatch.setattr(
            x_collector, "_get", lambda *a, **k: _fake_tweets_payload(tweets)
        )
        posts, _, _ = x_collector.collect_x_profile_tweets("alice", "AI Agents", api_key="k")
        assert [p["id"] for p in posts] == ["x_1"]


class TestXCollectorSchemaMapping:
    def test_fields_map_onto_uniform_schema(self, monkeypatch):
        tweets = [{
            "id": "1800000000000000001",
            "text": "Shipping agents with @bob today",
            "createdAt": "2026-08-01T10:00:00Z",
            "inReplyToStatusId": "1700000000000000009",
            "author": {"handle": "alice", "platformUserId": "999"},
            "metrics": {"likes": 12, "retweets": 3, "replies": 1, "views": 500},
        }]
        monkeypatch.setattr(
            x_collector, "_get", lambda *a, **k: _fake_tweets_payload(tweets)
        )
        posts, _, _ = x_collector.collect_x_profile_tweets("@alice", "AI Agents", api_key="k")

        post = posts[0]
        assert post["id"] == "x_1800000000000000001"
        assert post["platform"] == "x"
        # Bare handle, "@"-prefixed -- never the display name.
        assert post["author_handle"] == "@alice"
        assert post["author_id"] == "999"
        assert post["created_at"] == "2026-08-01T10:00:00+00:00"
        # Real reply parent, platform-prefixed so it resolves against post
        # `id` in analytics/network.py, same convention as yt_/channel_.
        assert post["parent_id"] == "x_1700000000000000009"
        assert post["topic_query"] == "AI Agents"
        assert post["reactions"] == 12
        assert post["shares"] == 3
        assert post["replies"] == 1
        assert post["views"] == 500

    def test_include_replies_is_requested_by_default(self, monkeypatch):
        seen = {}

        def fake_get(path, params, api_key):
            seen.update(params)
            return _fake_tweets_payload([])

        monkeypatch.setattr(x_collector, "_get", fake_get)
        x_collector.collect_x_profile_tweets("alice", "AI Agents", api_key="k")

        assert seen["includeReplies"] == "true"
        assert seen["limit"] == 100

    def test_limit_is_capped_at_api_maximum(self, monkeypatch):
        seen = {}

        def fake_get(path, params, api_key):
            seen.update(params)
            return _fake_tweets_payload([])

        monkeypatch.setattr(x_collector, "_get", fake_get)
        x_collector.collect_x_profile_tweets(
            "alice", "AI Agents", limit=5000, api_key="k"
        )
        assert seen["limit"] == 100

    def test_follows_cursor_across_pages(self, monkeypatch):
        pages = [
            _fake_tweets_payload(
                [{"id": "1", "text": "page one", "author": {"handle": "alice"}}],
                next_cursor="cur2",
            ),
            _fake_tweets_payload(
                [{"id": "2", "text": "page two", "author": {"handle": "alice"}}],
            ),
        ]
        cursors = []

        def fake_get(path, params, api_key):
            cursors.append(params.get("cursor"))
            return pages[len(cursors) - 1]

        monkeypatch.setattr(x_collector, "_get", fake_get)
        posts, _, _ = x_collector.collect_x_profile_tweets(
            "alice", "AI Agents", max_pages=2, api_key="k"
        )

        assert [p["id"] for p in posts] == ["x_1", "x_2"]
        assert cursors == [None, "cur2"]

    def test_max_pages_caps_requests(self, monkeypatch):
        calls = []

        def fake_get(path, params, api_key):
            calls.append(path)
            return _fake_tweets_payload(
                [{"id": "1", "text": "t", "author": {"handle": "alice"}}],
                next_cursor="more",
            )

        monkeypatch.setattr(x_collector, "_get", fake_get)
        x_collector.collect_x_profile_tweets(
            "alice", "AI Agents", max_pages=2, api_key="k"
        )
        assert len(calls) == 2

    def test_private_profile_yields_nothing_but_reports_status(self, monkeypatch):
        monkeypatch.setattr(
            x_collector, "_get",
            lambda *a, **k: _fake_tweets_payload([], lookup_status="private"),
        )
        posts, status, _ = x_collector.collect_x_profile_tweets(
            "secretco", "AI Agents", api_key="k"
        )
        # Paid for, empty -- the caller caches it so it is never re-billed.
        assert posts == []
        assert status == "private"

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("SOCIALFETCH_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="SOCIALFETCH_API_KEY"):
            x_collector.discover_x_profiles("AI Agents")



class TestYouTubeCollectorIds:
    def _install_fake_fetch(self, monkeypatch):
        comments = [
            {"id": "c1", "text": "first comment", "author": "alice",
             "author_id": "u1", "created_at": "2026-08-01T10:00:00+00:00",
             "like_count": 3, "reply_count": 0, "parent_id": None},
            {"id": None, "text": "second comment", "author": "bob",
             "author_id": "u2", "created_at": "2026-08-01 11:00:00",
             "like_count": 0, "reply_count": 1, "parent_id": None},
            {"id": None, "text": "dup comment", "author": "carol",
             "author_id": "u3", "created_at": "2026-08-01 12:00:00",
             "like_count": 0, "reply_count": 0, "parent_id": None},
            {"id": None, "text": "dup comment", "author": "carol",
             "author_id": "u3", "created_at": "2026-08-01 12:00:00",
             "like_count": 0, "reply_count": 0, "parent_id": None},
        ]
        monkeypatch.setattr(
            youtube_collector, "_fetch_comment_threads", lambda *a, **k: comments
        )

    def test_timestamps_parsed_by_shared_normalizer(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
        self._install_fake_fetch(monkeypatch)
        posts = youtube_collector.collect_youtube_comments(
            "https://www.youtube.com/watch?v=VID123", "AI Agents"
        )
        # Space-separated naive timestamps must parse to UTC, not fall back to "now".
        assert posts[0]["created_at"] == "2026-08-01T10:00:00+00:00"
        assert posts[1]["created_at"] == "2026-08-01T11:00:00+00:00"

    def test_missing_comment_id_gets_stable_hash(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
        self._install_fake_fetch(monkeypatch)
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
        monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
        self._install_fake_fetch(monkeypatch)
        posts = youtube_collector.collect_youtube_comments(
            "https://www.youtube.com/watch?v=VID123", "AI Agents"
        )
        assert posts[2]["id"] == posts[3]["id"]

    def test_missing_api_key_raises_clear_error(self, monkeypatch):
        monkeypatch.setattr(youtube_collector, "_fetch_comment_threads", lambda *a, **k: [])
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="YOUTUBE_API_KEY"):
            youtube_collector.collect_youtube_comments(
                "https://www.youtube.com/watch?v=VID123", "AI Agents"
            )


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

    def test_collect_rejects_invalid_url_before_api(self, monkeypatch):
        # Validation must run before the API is ever hit; force it to
        # explode if it ever gets there.
        def _fail_fetch(*args, **kwargs):
            raise AssertionError("API should never see a non-YouTube URL")

        monkeypatch.setattr(youtube_collector, "_fetch_comment_threads", _fail_fetch)
        with pytest.raises(ValueError):
            youtube_collector.collect_youtube_comments("file:///etc/passwd", "AI Agents")


class TestYouTubeCommentThreadPagination:
    def _item(self, comment_id, author, text):
        return {
            "id": comment_id,
            "snippet": {
                "totalReplyCount": 2,
                "topLevelComment": {
                    "snippet": {
                        "textDisplay": text,
                        "authorDisplayName": author,
                        "authorChannelId": {"value": f"{author}_chan"},
                        "publishedAt": "2026-08-01T10:00:00+00:00",
                        "likeCount": 5,
                    }
                },
            },
        }

    def _install_api(self, monkeypatch, pages):
        """pages: list of payload dicts returned for successive API calls."""

        class FakeResponse:
            def __init__(self, payload, status_code=200):
                self._payload = payload
                self.status_code = status_code

            def raise_for_status(self):
                pass

            def json(self):
                return self._payload

        iterator = iter(pages)

        def fake_get(url, params, timeout):
            return FakeResponse(next(iterator))

        import requests

        monkeypatch.setattr(requests, "get", fake_get)

    def test_collects_all_comments_single_page(self, monkeypatch):
        payload = {
            "items": [
                self._item("c1", "alice", "first"),
                self._item("c2", "bob", "second"),
                self._item("c3", "carol", "third"),
            ]
        }
        self._install_api(monkeypatch, [payload])
        comments = youtube_collector._fetch_comment_threads("k", "VID123", limit=100)
        assert [c["id"] for c in comments] == ["c1", "c2", "c3"]

    def test_paginates_until_next_page_token_missing(self, monkeypatch):
        page1 = {
            "items": [self._item("c1", "alice", "first")],
            "nextPageToken": "TOKEN_2",
        }
        page2 = {
            "items": [self._item("c2", "bob", "second")],
        }
        self._install_api(monkeypatch, [page1, page2])
        comments = youtube_collector._fetch_comment_threads("k", "VID123", limit=100)
        assert [c["id"] for c in comments] == ["c1", "c2"]

    def test_caps_at_limit_across_pages(self, monkeypatch):
        page1 = {
            "items": [self._item("c1", "alice", "first"),
                      self._item("c2", "bob", "second")],
            "nextPageToken": "TOKEN_2",
        }
        page2 = {
            "items": [self._item("c3", "carol", "third")],
        }
        self._install_api(monkeypatch, [page1, page2])
        comments = youtube_collector._fetch_comment_threads("k", "VID123", limit=2)
        assert [c["id"] for c in comments] == ["c1", "c2"]

    def test_skips_blank_comments(self, monkeypatch):
        payload = {
            "items": [
                self._item("c1", "alice", "   "),
                self._item("c2", "bob", "real comment"),
            ]
        }
        self._install_api(monkeypatch, [payload])
        comments = youtube_collector._fetch_comment_threads("k", "VID123", limit=100)
        assert [c["id"] for c in comments] == ["c2"]

    def test_empty_items_returns_empty(self, monkeypatch):
        self._install_api(monkeypatch, [{"items": []}])
        comments = youtube_collector._fetch_comment_threads("k", "VID123", limit=100)
        assert comments == []


class TestYouTubeVideoIdExtraction:
    @pytest.mark.parametrize("url,expected", [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/abc123", "abc123"),
    ])
    def test_extracts_known_ids(self, url, expected):
        assert youtube_collector._extract_video_id(url) == expected

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/",
        "https://www.youtube.com/playlist?list=abc",
        "https://www.youtube.com/results?search_query=x",
    ])
    def test_rejects_urls_without_video_id(self, url):
        with pytest.raises(ValueError):
            youtube_collector._extract_video_id(url)


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


class _FakeApiResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if not 200 <= self.status_code < 300:
            raise _FakeHttpError(self.status_code)

    def json(self):
        return self._payload


class _FakeHttpError(Exception):
    pass


class TestYouTubeQuotaLedger:
    def test_absent_ledger_starts_fresh(self):
        assert youtube_collector._load_ledger() == {
            "date": youtube_collector._today_utc(), "used": 0
        }
        assert youtube_collector.quota_remaining() == youtube_collector.QUOTA_DAILY_LIMIT

    def test_spend_reduces_remaining(self):
        youtube_collector.spend_quota(100)
        youtube_collector.spend_quota(55)
        assert youtube_collector.quota_remaining() == (
            youtube_collector.QUOTA_DAILY_LIMIT - 155
        )

    def test_resets_on_new_utc_day(self, monkeypatch):
        youtube_collector.spend_quota(500)
        monkeypatch.setattr(
            youtube_collector, "_today_utc", lambda: "2099-01-01"
        )
        assert youtube_collector._load_ledger()["used"] == 0
        assert youtube_collector.quota_remaining() == youtube_collector.QUOTA_DAILY_LIMIT


class TestYouTubeVideoSearch:
    def _api(self, monkeypatch, payload):
        def fake_get(url, params, timeout):
            assert url.endswith("/search")
            assert params["q"] == "AI Agents"
            assert params["type"] == "video"
            assert params["maxResults"] == 5
            assert params["key"] == "test-key"
            return _FakeApiResponse(payload)

        import requests
        monkeypatch.setattr(requests, "get", fake_get)

    def test_parses_video_items(self, monkeypatch):
        payload = {"items": [
            {"id": {"videoId": "AAA111"}, "snippet": {
                "title": "Video A", "channelTitle": "Chan A",
                "description": "desc a", "publishedAt": "2026-08-01T10:00:00Z",
            }},
            {"id": {"videoId": "BBB222"}, "snippet": {
                "title": "Video B", "channelTitle": "Chan B",
                "description": "desc b", "publishedAt": "2026-08-02T10:00:00Z",
            }},
        ]}
        self._api(monkeypatch, payload)
        videos = youtube_collector.search_videos("AI Agents", max_results=5, key="test-key")
        assert [v["video_id"] for v in videos] == ["AAA111", "BBB222"]
        assert videos[0]["title"] == "Video A"
        assert videos[0]["channel"] == "Chan A"
        assert len(videos) == 2
        assert youtube_collector._load_ledger()["used"] == 100

    def test_empty_items_returns_empty(self, monkeypatch):
        self._api(monkeypatch, {"items": []})
        assert youtube_collector.search_videos("AI Agents", key="test-key") == []

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="YOUTUBE_API_KEY"):
            youtube_collector.search_videos("AI Agents")


class TestYouTubeQuotaExceeded:
    def _quota_response(self):
        return _FakeApiResponse({
            "error": {
                "errors": [{
                    "reason": "quotaExceeded",
                    "message": "quota exceeded",
                }]
            }
        }, status_code=403)

    def test_comment_fetch_raises_on_quota(self, monkeypatch):
        def fake_get(url, params, timeout):
            return self._quota_response()

        import requests
        monkeypatch.setattr(requests, "get", fake_get)
        with pytest.raises(youtube_collector.YouTubeQuotaExceededError):
            youtube_collector._fetch_comment_threads("k", "VID123", limit=100)

    def test_search_raises_on_quota(self, monkeypatch):
        def fake_get(url, params, timeout):
            return self._quota_response()

        import requests
        monkeypatch.setattr(requests, "get", fake_get)
        with pytest.raises(youtube_collector.YouTubeQuotaExceededError):
            youtube_collector.search_videos("AI Agents", key="test-key")