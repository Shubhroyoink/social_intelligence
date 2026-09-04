import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import dotenv

import database.db as db_module

SECRET_ENV_KEYS = ("YOUTUBE_API_KEY", "TG_API_ID", "TG_API_HASH", "LLM_API_KEY")


def pytest_configure(config):
    """Force all temp test data under D:\\social-intelligence\\.test_tmp.

    pytest's default tmp dir is the OS temp dir (C: drive on this machine);
    this hook keeps every test artifact on the D: drive.
    """
    config.option.basetemp = os.path.join(PROJECT_ROOT, ".test_tmp")

    # Durable env-isolation for the whole session. Collectors call
    # load_dotenv() at module import, and lazy imports in run_pipeline mean a
    # collector can first be imported mid-test (re-reading .env with real
    # secrets). No-oping load_dotenv before any test module is collected, plus
    # scrubbing the known secret names, stops every such leak at once.
    dotenv.load_dotenv = lambda *a, **k: False
    for key in SECRET_ENV_KEYS:
        os.environ.pop(key, None)


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """Point every test at an isolated SQLite DB under D:\\.test_tmp.

    Never touches the real social.db and keeps all storage on the D: drive
    (pytest basetemp is configured to .test_tmp in pytest.ini).
    """
    db_file = tmp_path / "test_social.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file))
    db_module.create_database()
    return db_module


@pytest.fixture(autouse=True)
def _ledger_isolated(tmp_path, monkeypatch):
    """Route the YouTube quota ledger to .test_tmp so tests never touch
    (or write) the real youtube_quota.json in the repo root."""
    from collectors import youtube_collector

    monkeypatch.setattr(
        youtube_collector, "LEDGER_PATH", str(tmp_path / "youtube_quota.json")
    )


@pytest.fixture
def sample_posts():
    """Canonical dataset covering many edge cases at once."""
    return [
        {
            "id": "tg_1",
            "platform": "telegram",
            "author_id": "u1",
            "author_handle": "@alice",
            "text": "AI agents are transforming the industry. Love this new framework @bob",
            "created_at": "2026-08-01T10:00:00+00:00",
            "collected_at": "2026-08-01T11:00:00+00:00",
            "parent_id": None,
            "topic_query": "AI Agents",
            "reactions": 12,
            "shares": 3,
            "replies": 2,
            "views": 100,
        },
        {
            "id": "tg_2",
            "platform": "telegram",
            "author_id": "u2",
            "author_handle": "@bob",
            "text": "Replying with more details about LLM agents",
            "created_at": "2026-08-02T10:00:00+00:00",
            "collected_at": "2026-08-02T11:00:00+00:00",
            "parent_id": "tg_1",
            "topic_query": "AI Agents",
            "reactions": 0,
            "shares": 0,
            "replies": None,
            "views": None,
        },
        {
            "id": "x_1",
            "platform": "x",
            "author_id": "u3",
            "author_handle": "@carol",
            "text": "Terrible rollout. Against this approach entirely. Horrible performance.",
            "created_at": 1783000000,
            "collected_at": "2026-08-03T11:00:00+00:00",
            "parent_id": None,
            "topic_query": "AI Agents",
            "reactions": 5,
            "shares": 1,
            "replies": 0,
            "views": None,
        },
    ]


class FakeSentimentModel:
    """Mimics HF text-classification pipeline output (top_k=None)."""

    def __init__(self, label="positive", score=0.9):
        self.label = label
        self.score = score

    def _result(self):
        labels = ["positive", "neutral", "negative"]
        other = (1.0 - self.score) / 2.0
        out = {lbl: other for lbl in labels}
        out[self.label] = self.score
        return [{"label": k, "score": v} for k, v in out.items()]

    def __call__(self, inputs):
        if isinstance(inputs, str):
            inputs = [inputs]
        return [self._result() for _ in inputs]


class FakeEmotionModel:
    """Mimics HF emotion pipeline output (top_k=None)."""

    EMOTIONS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]

    def __init__(self, label="joy", score=0.9):
        self.label = label
        self.score = score

    def _result(self):
        other = (1.0 - self.score) / (len(self.EMOTIONS) - 1)
        out = {lbl: other for lbl in self.EMOTIONS}
        out[self.label] = self.score
        return [{"label": k, "score": v} for k, v in out.items()]

    def __call__(self, inputs):
        if isinstance(inputs, str):
            inputs = [inputs]
        return [self._result() for _ in inputs]


@pytest.fixture
def mock_sentiment(monkeypatch):
    def _make(label="positive", score=0.9):
        model = FakeSentimentModel(label=label, score=score)
        monkeypatch.setattr("analytics.sentiment._pipe", model)
        return model

    return _make


@pytest.fixture
def mock_emotions(monkeypatch):
    def _make(label="joy", score=0.9):
        model = FakeEmotionModel(label=label, score=score)
        monkeypatch.setattr("analytics.emotions._pipe", model)
        return model

    return _make