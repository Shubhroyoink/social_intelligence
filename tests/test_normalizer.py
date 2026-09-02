import os
import subprocess
import sys
from datetime import datetime

import pytest

from normalizer.normalizer import (
    clean_text,
    dedupe,
    normalize_posts,
    normalize_timestamp,
    stable_post_id,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_iso(value):
    try:
        datetime.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


class TestCleanText:
    def test_strips_urls_mentions_hashtags(self):
        text = (
            "Check https://example.com/page and follow @someone "
            "for #AI news"
        )
        cleaned = clean_text(text)
        assert "http" not in cleaned
        assert "@someone" not in cleaned
        assert "#" not in cleaned
        assert "Check" in cleaned
        assert "news" in cleaned

    def test_preserves_core_words(self):
        cleaned = clean_text("  Multiple   spaces   collapse  ")
        assert cleaned == "Multiple spaces collapse"

    def test_empty_and_none(self):
        assert clean_text(None) == ""
        assert clean_text("") == ""
        assert clean_text("   \n\t ") == ""

    def test_only_url_becomes_empty(self):
        assert clean_text("https://example.com ONLY_URL www.foo.com") == "ONLY_URL"

    def test_preserves_unicode_non_english(self):
        original = "Bonjour, j'adore l'intelligence artificielle! 日本語テキスト"
        cleaned = clean_text(original)
        assert "Bonjour" in cleaned
        assert "日本語テキスト" in cleaned


class TestNormalizeTimestamp:
    def test_none_returns_valid_iso(self):
        result = normalize_timestamp(None)
        assert _is_iso(result)

    def test_numeric_epoch(self):
        result = normalize_timestamp(1783000000)
        assert _is_iso(result)
        assert datetime.fromisoformat(result).year == 2026

    def test_float_epoch(self):
        assert _is_iso(normalize_timestamp(0.0))

    def test_iso_with_z(self):
        result = normalize_timestamp("2026-08-01T10:00:00Z")
        assert result == "2026-08-01T10:00:00+00:00"

    def test_iso_with_offset(self):
        result = normalize_timestamp("2026-08-01T10:00:00+02:00")
        assert result == "2026-08-01T10:00:00+02:00"

    def test_datetime_string_format(self):
        result = normalize_timestamp("2026-08-01 10:00:00")
        assert result == "2026-08-01T10:00:00+00:00"

    def test_malformed_string_falls_back(self):
        result = normalize_timestamp("not-a-date::garbage")
        assert _is_iso(result)

    def test_aware_datetime_object(self):
        dt = datetime(2026, 8, 1, 10, 0, 0)
        result = normalize_timestamp(dt)
        assert result.startswith("2026-08-01T10:00:00") and "+00:00" in result

    def test_naive_datetime_object(self):
        from datetime import timezone

        dt = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert normalize_timestamp(dt) == "2026-08-01T10:00:00+00:00"


class TestNormalizePosts:
    def test_empty_list(self):
        assert normalize_posts([]) == []

    def test_drops_deleted_content_after_cleaning(self):
        posts = [
            {"id": "a", "text": "http://example.com", "platform": "x"},
            {"id": "b", "text": "   ", "platform": "x"},
            {"id": "c", "text": "", "platform": "x"},
        ]
        assert normalize_posts(posts) == []

    def test_preserves_raw_text(self):
        posts = [{
            "id": "a",
            "text": "Great work @bob check https://example.com for details",
            "platform": "x",
            "author_handle": "@alice",
        }]
        result = normalize_posts(posts)[0]
        assert result["raw_text"] == "Great work @bob check https://example.com for details"
        assert "@bob" not in result["text"]
        assert "@bob" in result["raw_text"]

    def test_raw_text_absent_uses_original(self):
        posts = [{"id": "a", "text": "plain text", "platform": "x"}]
        result = normalize_posts(posts)[0]
        assert result["raw_text"] == "plain text"

    def test_keeps_placeholder_deleted_text(self):
        posts = [{"id": "a", "text": "[deleted]", "platform": "x"}]
        result = normalize_posts(posts)
        assert len(result) == 1
        assert result[0]["text"] == "[deleted]"

    def test_missing_author_preserved_as_none(self):
        posts = [{"id": "a", "text": "hello world", "platform": "x"}]
        result = normalize_posts(posts)
        assert result[0]["author_handle"] is None
        assert result[0]["author_id"] is None

    def test_zero_reactions_coerced(self):
        posts = [{"id": "a", "text": "hello", "platform": "x"}]
        result = normalize_posts(posts)
        assert result[0]["reactions"] == 0
        assert result[0]["shares"] == 0

    def test_string_counts_coerced_to_int(self):
        posts = [{
            "id": "a",
            "text": "hello",
            "platform": "x",
            "reactions": "42",
            "shares": "7",
        }]
        result = normalize_posts(posts)
        assert result[0]["reactions"] == 42
        assert result[0]["shares"] == 7

    def test_non_english_text_survives(self):
        posts = [{"id": "a", "text": "日本語のテキストです", "platform": "x"}]
        result = normalize_posts(posts)
        assert result[0]["text"] == "日本語のテキストです"

    def test_uniform_schema_fields(self):
        posts = [{
            "id": "tg_1",
            "platform": "telegram",
            "author_id": "u1",
            "author_handle": "@alice",
            "text": "AI agents are transforming the industry @bob",
            "created_at": "2026-08-01T10:00:00+00:00",
            "collected_at": None,
            "parent_id": None,
            "topic_query": "AI Agents",
            "reactions": 12,
            "shares": 3,
            "replies": 2,
            "views": 100,
        }]
        result = normalize_posts(posts)[0]
        expected_keys = {
            "id", "platform", "author_id", "author_handle", "text",
            "raw_text", "created_at", "collected_at", "parent_id", "topic_query",
            "reactions", "shares", "replies", "views",
        }
        assert set(result.keys()) == expected_keys
        assert result["created_at"] == "2026-08-01T10:00:00+00:00"


class TestDedupe:
    def test_removes_duplicates_keeps_first(self):
        posts = [
            {"id": "a", "text": "first"},
            {"id": "b", "text": "second"},
            {"id": "a", "text": "duplicate"},
        ]
        result = dedupe(posts, key="id")
        assert len(result) == 2
        assert result[0]["text"] == "first"

    def test_empty_list(self):
        assert dedupe([], key="id") == []

    def test_no_duplicates(self):
        posts = [{"id": str(i)} for i in range(3)]
        assert len(dedupe(posts, key="id")) == 3

    def test_missing_key_dedupe(self):
        posts = [{"id": "a"}, {"id": None}, {"id": "a"}]
        result = dedupe(posts, key="id")
        assert len(result) == 2


class TestStablePostId:
    def test_deterministic_within_process(self):
        a = stable_post_id("x", None, "hello @bob https://example.com")
        b = stable_post_id("x", None, "hello @bob https://example.com")
        assert a == b

    def test_uses_platform_prefix(self):
        assert stable_post_id("x", None, "t").startswith("x_")
        assert stable_post_id("yt", None, "t").startswith("yt_")

    def test_keeps_truthy_raw_id_verbatim(self):
        assert stable_post_id("x", 123, "text") == "x_123"
        assert stable_post_id("yt", "c1", "text") == "yt_c1"

    def test_falsey_raw_id_falls_back_to_content_hash(self):
        for falsey in (None, "", 0):
            pid = stable_post_id("x", falsey, "some text")
            assert pid.startswith("x_")
            assert "None" not in pid
            assert len(pid) == 2 + 16  # prefix + 16-char digest

    def test_distinct_texts_get_distinct_ids(self):
        assert stable_post_id("x", None, "first post") != stable_post_id("x", None, "second")

    def test_same_text_same_id_across_platforms_keep_prefix(self):
        assert stable_post_id("x", None, "dup") != stable_post_id("yt", None, "dup")

    def test_unicode_text_handled(self):
        pid = stable_post_id("x", None, "日本語のテキスト émojis 🚀")
        assert pid.startswith("x_")

    def test_stable_across_processes(self):
        code = (
            "from normalizer.normalizer import stable_post_id;"
            "print(stable_post_id('x', None, 'hello @bob https://example.com'))"
        )
        r1 = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, cwd=PROJECT_ROOT)
        r2 = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert r1.returncode == 0 and r2.returncode == 0
        assert r1.stdout == r2.stdout
        assert "None" not in r1.stdout