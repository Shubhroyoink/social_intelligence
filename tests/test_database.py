import os
import sqlite3

import pytest

import database.db as db


class TestStorageLocation:
    def test_db_points_at_test_file_not_social(self, test_db, tmp_path):
        path = os.path.abspath(test_db.DB_PATH)
        assert path != os.path.abspath("social.db")
        assert ".test_tmp" in path

    def test_tmp_is_on_d_drive(self, tmp_path):
        drive, _ = os.path.splitdrive(str(tmp_path))
        assert drive.lower() == "d:"


class TestSchema:
    def test_all_tables_exist(self, test_db):
        conn = sqlite3.connect(test_db.DB_PATH)
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        expected = {"posts", "sentiments", "trends", "emotions",
                    "demographics", "network_nodes", "network_edges"}
        assert expected.issubset(tables)

    def test_posts_has_raw_text_column(self, test_db):
        conn = sqlite3.connect(test_db.DB_PATH)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
        conn.close()
        assert "raw_text" in cols

    def test_raw_text_migrated_on_preexisting_db(self, test_db):
        conn = sqlite3.connect(test_db.DB_PATH)
        conn.execute("ALTER TABLE posts DROP COLUMN raw_text")
        conn.commit()
        conn.close()
        test_db.create_database()
        conn = sqlite3.connect(test_db.DB_PATH)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
        conn.close()
        assert "raw_text" in cols


class TestPosts:
    def test_empty_queries(self, test_db):
        assert db.get_posts() == []
        assert db.get_posts(topic_query="AI Agents") == []
        assert db.get_posts(platform="x") == []

    def test_save_and_get_roundtrip(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        loaded = db.get_posts()
        assert len(loaded) == len(sample_posts)

    def test_raw_text_roundtrips(self, test_db):
        post = {
            "id": "rt_1", "platform": "x", "author_id": "uA", "author_handle": "@alice",
            "text": "great work", "raw_text": "great work @bob see http://x.com",
            "created_at": "2026-08-01T10:00:00+00:00", "collected_at": "2026-08-01T11:00:00+00:00",
            "parent_id": None, "topic_query": "AI Agents",
            "reactions": 0, "shares": 0, "replies": None, "views": None,
        }
        db.save_posts([post])
        loaded = db.get_posts()[0]
        assert loaded["raw_text"] == "great work @bob see http://x.com"

    def test_save_stores_null_raw_text_when_missing(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        loaded = db.get_posts()[0]
        assert loaded["raw_text"] is None

    def test_insert_ignore_duplicates(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        db.save_posts(sample_posts[:1])  # same id again
        assert len(db.get_posts()) == len(sample_posts)

    def test_ordered_by_created_at_desc(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        loaded = db.get_posts()
        assert loaded[0]["id"] == "tg_2"

    def test_filter_by_platform_and_topic(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        assert len(db.get_posts(platform="x")) == 1
        assert len(db.get_posts(platform="telegram")) == 2
        assert len(db.get_posts(topic_query="AI Agents")) == 3
        assert db.get_posts(topic_query="Nope") == []

    def test_limit(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        assert len(db.get_posts(limit=1)) == 1


class TestSentiments:
    def test_roundtrip(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        sentiments = [
            {
                "post_id": p["id"], "platform": p["platform"],
                "created_at": p["created_at"], "topic_query": "AI Agents",
                "label": "positive", "positive_score": 0.8,
                "neutral_score": 0.1, "negative_score": 0.1,
                "analyzed_at": "2026-08-03T12:00:00+00:00",
            } for p in sample_posts
        ]
        db.save_sentiments(sentiments)
        loaded = db.get_sentiments(topic_query="AI Agents")
        assert len(loaded) == len(sample_posts)

    def test_insert_or_replace(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        base = {
            "post_id": "tg_1", "platform": "telegram",
            "created_at": "2026-08-01T10:00:00+00:00",
            "topic_query": "AI Agents", "label": "positive",
            "positive_score": 0.8, "neutral_score": 0.1,
            "negative_score": 0.1, "analyzed_at": "2026-08-03T12:00:00+00:00",
        }
        db.save_sentiments([{**base, "label": "positive"}])
        db.save_sentiments([{**base, "label": "negative"}])
        loaded = db.get_sentiments()
        assert len(loaded) == 1
        assert loaded[0]["label"] == "negative"


class TestTrends:
    def test_roundtrip_and_accumulate(self, test_db):
        row = {
            "topic_query": "AI Agents", "keyword": "llm",
            "frequency": 5, "window_start": "2026-08-01T00:00:00+00:00",
            "window_end": "2026-08-02T00:00:00+00:00",
            "analyzed_at": "2026-08-03T12:00:00+00:00",
        }
        db.save_trends([row])
        db.save_trends([row])
        loaded = db.get_trends(topic_query="AI Agents")
        assert len(loaded) == 2  # plain INSERT accumulates


class TestEmotions:
    def test_roundtrip_requires_post_and_sentiment(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        db.save_sentiments([{
            "post_id": "tg_1", "platform": "telegram",
            "created_at": "2026-08-01T10:00:00+00:00",
            "topic_query": "AI Agents", "label": "positive",
            "positive_score": 0.8, "neutral_score": 0.1,
            "negative_score": 0.1, "analyzed_at": "2026-08-03T12:00:00+00:00",
        }])
        db.save_emotions([{
            "post_id": "tg_1", "primary_emotion": "joy",
            "emotion_json": '{"joy": 0.9}', "sarcasm_flag": 0,
            "stance": "supportive", "analyzed_at": "2026-08-03T12:00:00+00:00",
        }])
        loaded = db.get_emotions(topic_query="AI Agents")
        assert len(loaded) == 1
        assert loaded[0]["primary_emotion"] == "joy"

    def test_emotion_without_post_is_not_returned(self, test_db):
        db.save_emotions([{
            "post_id": "ghost", "primary_emotion": "neutral",
            "emotion_json": "{}", "sarcasm_flag": 0,
            "stance": "neutral", "analyzed_at": "2026-08-03T12:00:00+00:00",
        }])
        assert db.get_emotions("AI Agents") == []


class TestDemographics:
    def test_roundtrip_and_summary(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        db.save_demographics([{
            "post_id": p["id"], "language": "en",
            "geo_hint": "India", "interests_json": '["ai_ml", "technology"]',
            "inferred_at": "2026-08-03T12:00:00+00:00",
        } for p in sample_posts])

        summary = db.get_demographics_summary(topic_query="AI Agents")
        assert summary["languages"] == {"en": 3}
        assert summary["geo"] == {"India": 3}
        assert summary["interests"] == {"ai_ml": 3, "technology": 3}

    def test_summary_empty(self, test_db):
        assert db.get_demographics_summary() == {
            "languages": {}, "geo": {}, "interests": {}
        }

    def test_insert_or_replace(self, test_db, sample_posts):
        db.save_posts(sample_posts)
        row = {
            "post_id": "tg_1", "language": "en", "geo_hint": "India",
            "interests_json": '["ai_ml"]', "inferred_at": "2026-08-03T12:00:00+00:00",
        }
        db.save_demographics([row])
        db.save_demographics([{**row, "language": "fr"}])
        loaded = db.get_demographics()
        assert len(loaded) == 1
        assert loaded[0]["language"] == "fr"


class TestNetworkTables:
    def test_nodes_roundtrip_and_replace(self, test_db):
        node = {
            "handle": "alice", "topic_query": "AI Agents",
            "degree_centrality": 0.5, "betweenness_centrality": 0.2,
            "eigenvector_centrality": 0.9, "community_id": 0,
            "is_kol": 1, "computed_at": "2026-08-03T12:00:00+00:00",
        }
        db.save_network_nodes([node])
        db.save_network_nodes([{**node, "eigenvector_centrality": 0.95}])
        loaded = db.get_network_nodes(topic_query="AI Agents")
        assert len(loaded) == 1
        assert loaded[0]["eigenvector_centrality"] == 0.95

    def test_edges_accumulate(self, test_db):
        edge = {
            "source_handle": "alice", "target_handle": "bob", "weight": 1,
            "sentiment_shift": '{"from": "positive", "to": "neutral"}',
            "topic_query": "AI Agents", "computed_at": "2026-08-03T12:00:00+00:00",
        }
        db.save_network_edges([edge])
        db.save_network_edges([edge])
        assert len(db.get_network_edges(topic_query="AI Agents")) == 2

    def test_empty_queries(self, test_db):
        assert db.get_network_nodes() == []
        assert db.get_network_edges() == []
        assert db.get_demographics() == []


class TestEndToEndFlow:
    def test_full_analysis_survives_db(self, test_db, sample_posts):
        db.save_posts(sample_posts)

        db.save_sentiments([{
            "post_id": p["id"], "platform": p["platform"],
            "created_at": p["created_at"], "topic_query": "AI Agents",
            "label": "positive", "positive_score": 0.8,
            "neutral_score": 0.1, "negative_score": 0.1,
            "analyzed_at": "2026-08-03T12:00:00+00:00",
        } for p in sample_posts])

        db.save_emotions([{
            "post_id": p["id"], "primary_emotion": "joy",
            "emotion_json": "{}", "sarcasm_flag": 0,
            "stance": "supportive", "analyzed_at": "2026-08-03T12:00:00+00:00",
        } for p in sample_posts])

        db.save_demographics([{
            "post_id": p["id"], "language": "en", "geo_hint": None,
            "interests_json": '["ai_ml"]', "inferred_at": "2026-08-03T12:00:00+00:00",
        } for p in sample_posts])

        assert len(db.get_sentiments()) == 3
        assert len(db.get_emotions()) == 3
        assert len(db.get_demographics()) == 3