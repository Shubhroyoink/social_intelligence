"""Social Fetch credit-metering, budget-guard and profile-cache tests.

`requests` is faked at the transport layer so the real `_get` code path runs --
that is where the credit ledger is written, so mocking it away would test
nothing. No test here touches the network or the real x_credits.json.
"""
import json

import pytest

import collectors.x_collector as x_collector
from database.db import get_fetched_x_handles, get_x_profiles, upsert_x_profile


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}",
                                     response=self)


@pytest.fixture
def route(monkeypatch):
    """Register canned responses per URL path; returns the call log."""
    import requests

    calls = []
    routes = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append({"url": url, "params": params or {}, "headers": headers or {}})
        path = url.replace(x_collector.API_BASE, "")
        for prefix, response in routes.items():
            if path.startswith(prefix):
                if callable(response):
                    response = response(path, params or {}, len(calls))
                if isinstance(response, dict):
                    response = FakeResponse(200, response)
                return response
        raise AssertionError(f"unregistered route: {path}")

    monkeypatch.setattr(requests, "get", fake_get)
    return {"calls": calls, "routes": routes}


def _tweet(tid, text="hello world"):
    return {"id": tid, "text": text, "author": {"handle": "alice",
                                                "platformUserId": "u1"}}


def _person(handle, display_name="AI Agents Fan"):
    """A discovery card that survives the relevance filter.

    Collection defaults to requiring a topic term in the name/bio, so a bare
    `{"handle": ...}` card would be rejected before it could be collected.
    """
    return {"handle": handle, "displayName": display_name}


def _timeline(tweets=None, lookup_status="found"):
    return {
        "data": {
            "lookupStatus": lookup_status,
            "profile": {"handle": "alice"},
            "tweets": tweets if tweets is not None else [],
            "page": {"hasMore": False, "nextCursor": None},
        },
        "meta": {"creditsCharged": 1, "cached": False},
    }


class TestCreditLedger:
    def test_charges_are_recorded_from_response_metadata(self, route):
        route["routes"]["/v1/twitter/search"] = {
            "data": {"people": [_person("alice")]},
            "meta": {"creditsCharged": 1},
        }
        assert x_collector.credits_spent() == 0
        x_collector.discover_x_profiles("AI Agents", api_key="k")
        assert x_collector.credits_spent() == 1

    def test_ledger_accumulates_across_calls(self, route):
        route["routes"]["/v1/twitter/profiles/"] = _timeline([_tweet("1")])
        x_collector.collect_x_profile_tweets("alice", "AI", api_key="k")
        x_collector.collect_x_profile_tweets("bob", "AI", api_key="k")
        assert x_collector.credits_spent() == 2

    def test_ledger_does_not_reset_next_day(self, route):
        """Credits are prepaid and never refill, so the ledger is
        lifetime-cumulative -- a date-keyed ledger would silently reset."""
        route["routes"]["/v1/twitter/profiles/"] = _timeline([_tweet("1")])
        x_collector.collect_x_profile_tweets("alice", "AI", api_key="k")

        with open(x_collector.LEDGER_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        assert "date" not in data
        assert data["credits_spent"] == 1

    def test_meta_credits_is_source_of_truth(self, route):
        # Cache hits still bill; the provider reports the real number.
        route["routes"]["/v1/twitter/profiles/"] = {
            "data": {"lookupStatus": "found", "tweets": [],
                     "page": {"hasMore": False}},
            "meta": {"creditsCharged": 2, "cached": True},
        }
        x_collector.collect_x_profile_tweets("alice", "AI", api_key="k")
        assert x_collector.credits_spent() == 2

    def test_balance_route_is_free(self, route):
        route["routes"]["/v1/balance"] = {"data": {"balance": 96}}
        before = x_collector.credits_spent()
        assert x_collector.fetch_credit_balance("k")["balance"] == 96
        # Reading the balance must not bill.
        assert x_collector.credits_spent() == before

    def test_remaining_falls_back_to_signup_grant(self):
        assert x_collector.remaining_credits() == x_collector.FREE_SIGNUP_CREDITS
        x_collector.spend_credits(4)
        assert x_collector.remaining_credits() == x_collector.FREE_SIGNUP_CREDITS - 4
        # Never negative.
        x_collector.spend_credits(9999)
        assert x_collector.remaining_credits() == 0


class TestRetrySemantics:
    def test_503_is_retried_and_not_charged(self, route):
        attempts = {"n": 0}

        def flaky(path, params, call_index):
            attempts["n"] += 1
            if attempts["n"] < 3:
                return FakeResponse(503)
            return FakeResponse(200, _timeline([_tweet("1")]))

        route["routes"]["/v1/twitter/profiles/"] = flaky
        route["routes"]["/v1/twitter/search"] = _timeline([])
        monkey = pytest.MonkeyPatch()
        monkey.setattr(x_collector.time, "sleep", lambda *a: None)
        try:
            posts, _, _ = x_collector.collect_x_profile_tweets(
                "alice", "AI", api_key="k"
            )
        finally:
            monkey.undo()

        assert len(posts) == 1
        # Two failed 503s plus one success, but only the success bills.
        assert x_collector.credits_spent() == 1

    def test_persistent_503_raises_without_spending(self, route):
        route["routes"]["/v1/twitter/profiles/"] = FakeResponse(503)
        monkey = pytest.MonkeyPatch()
        monkey.setattr(x_collector.time, "sleep", lambda *a: None)
        try:
            with pytest.raises(RuntimeError, match="not charged"):
                x_collector.collect_x_profile_tweets("alice", "AI", api_key="k")
        finally:
            monkey.undo()
        assert x_collector.credits_spent() == 0

    def test_private_profile_still_bills(self, route):
        """Provider bills private/not_found lookups; the cache must remember
        them so a re-run does not pay again."""
        route["routes"]["/v1/twitter/profiles/"] = _timeline(
            [], lookup_status="private"
        )
        posts, status, _ = x_collector.collect_x_profile_tweets(
            "secretco", "AI Agents", api_key="k"
        )
        assert posts == []
        assert status == "private"
        assert x_collector.credits_spent() == 1

    def test_insufficient_credits_raises(self, route):
        route["routes"]["/v1/twitter/profiles/"] = FakeResponse(
            402, {"error": {"code": "insufficient_credits"}}
        )
        with pytest.raises(x_collector.XCreditsExceededError,
                           match="insufficient_credits"):
            x_collector.collect_x_profile_tweets("alice", "AI", api_key="k")
        assert x_collector.credits_spent() == 0

    def test_x402_challenge_is_distinguished_from_empty_balance(self, route):
        route["routes"]["/v1/twitter/profiles/"] = FakeResponse(
            402, {"error": {"code": "x402_payment_required"}}
        )
        with pytest.raises(x_collector.XCreditsExceededError, match="x402"):
            x_collector.collect_x_profile_tweets("alice", "AI", api_key="k")

    def test_401_surfaces_as_http_error(self, route):
        route["routes"]["/v1/twitter/profiles/"] = FakeResponse(401)
        with pytest.raises(Exception):
            x_collector.collect_x_profile_tweets("alice", "AI", api_key="k")


class TestPlanCost:
    def test_default_prototype_plan_is_four_credits(self):
        assert x_collector.plan_credit_cost(
            x_collector.DEFAULT_MAX_PROFILES, x_collector.DEFAULT_MAX_PAGES
        ) == 4

    def test_discovery_plus_profiles_plus_pages(self):
        # 1 discovery + 3 profiles x 2 pages
        assert x_collector.plan_credit_cost(3, 2, discovery_queries=1) == 7

    def test_multiple_discovery_queries_each_cost_a_credit(self):
        # 2 discovery credits + 3 profiles x 1 page
        assert x_collector.plan_credit_cost(3, 1, discovery_queries=2) == 5

    def test_zero_profiles_is_just_the_discovery(self):
        assert x_collector.plan_credit_cost(0, 1) == 1

    def test_documented_yield_is_100_tweets_per_credit(self):
        assert x_collector.TWEETS_PAGE_LIMIT == 100
        assert x_collector.REQUEST_COST == 1


class TestProfileCache:
    def test_fetched_handles_are_remembered_per_topic(self):
        upsert_x_profile({"handle": "alice", "display_name": "Alice"}, "AI Agents")
        upsert_x_profile({"handle": "bob", "display_name": "Bob"}, "AI Agents")
        upsert_x_profile({"handle": "carol", "display_name": "Carol"}, "LLM")

        assert set(get_fetched_x_handles("AI Agents")) == {"alice", "bob"}
        assert get_fetched_x_handles("LLM") == ["carol"]

    def test_private_handles_are_cached_too(self):
        upsert_x_profile(
            {"handle": "secretco"}, "AI Agents", lookup_status="private"
        )
        assert "secretco" in get_fetched_x_handles("AI Agents")

    def test_reinsert_updates_without_duplicating(self):
        upsert_x_profile(
            {"handle": "alice", "metrics": {"tweets": 5}}, "AI Agents",
            tweets_collected=5,
        )
        upsert_x_profile(
            {"handle": "alice", "metrics": {"tweets": 9}}, "AI Agents",
            tweets_collected=9,
        )
        rows = get_x_profiles("AI Agents")
        assert len(rows) == 1
        assert rows[0]["tweets_collected"] == 9

    def test_display_name_is_stored_not_the_handle(self):
        upsert_x_profile(
            x_collector._profile_row({
                "handle": "@alice", "displayName": "Alice Smith",
                "metrics": {"followers": 10, "tweets": 20},
            }),
            "AI Agents",
        )
        row = get_x_profiles("AI Agents")[0]
        assert row["handle"] == "alice"  # "@" stripped for the primary key
        assert row["display_name"] == "Alice Smith"
        assert row["followers"] == 10
        assert row["tweets_count"] == 20

    def test_first_seen_survives_rediscovery(self):
        upsert_x_profile({"handle": "alice"}, "AI Agents")
        first_seen = get_x_profiles("AI Agents")[0]["first_seen_at"]
        upsert_x_profile({"handle": "alice", "display_name": "New Name"},
                         "AI Agents")
        row = get_x_profiles("AI Agents")[0]
        assert row["first_seen_at"] == first_seen
        assert row["display_name"] == "New Name"


class TestCollectionGuards:
    def test_dry_run_spends_nothing(self, route):
        route["routes"]["/v1/balance"] = {"data": {"balance": 100}}
        posts = x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", dry_run=True
        )
        assert posts == []
        assert x_collector.credits_spent() == 0
        assert route["calls"] == []

    def test_per_run_budget_blocks_before_any_request(self, route):
        route["routes"]["/v1/balance"] = {"data": {"balance": 100}}
        with pytest.raises(x_collector.XCreditsExceededError,
                           match="exceeds the per-run budget"):
            x_collector.collect_x_for_topic(
                "AI Agents", api_key="k", max_profiles=10, budget_credits=4
            )
        assert x_collector.credits_spent() == 0

    def test_insufficient_balance_blocks_before_any_request(self, route):
        route["routes"]["/v1/balance"] = {"data": {"balance": 2}}
        with pytest.raises(x_collector.XCreditsExceededError,
                           match="available"):
            x_collector.collect_x_for_topic(
                "AI Agents", api_key="k", max_profiles=3, budget_credits=None
            )
        assert x_collector.credits_spent() == 0

    def test_max_profiles_is_respected(self, route):
        route["routes"]["/v1/balance"] = {"data": {"balance": 100}}
        route["routes"]["/v1/twitter/search"] = {
            "data": {"people": [_person(h) for h in
                               ("alice", "bob", "carol", "dan")]},
            "meta": {"creditsCharged": 1},
        }
        route["routes"]["/v1/twitter/profiles/"] = _timeline([_tweet("1")])

        x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=2, budget_credits=None
        )
        fetched = get_fetched_x_handles("AI Agents")
        assert len(fetched) == 2
        # 1 discovery + 2 profiles
        assert x_collector.credits_spent() == 3

    def test_already_collected_handles_are_skipped_on_rerun(self, route):
        upsert_x_profile({"handle": "alice"}, "AI Agents")
        route["routes"]["/v1/balance"] = {"data": {"balance": 100}}
        route["routes"]["/v1/twitter/search"] = {
            "data": {"people": [_person("alice"), _person("bob")]},
            "meta": {"creditsCharged": 1},
        }
        route["routes"]["/v1/twitter/profiles/"] = _timeline([_tweet("1")])

        x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=3, budget_credits=None
        )
        # Only bob was paid for; discovery still cost 1.
        assert x_collector.credits_spent() == 2
        assert set(get_fetched_x_handles("AI Agents")) == {"alice", "bob"}

    def test_refresh_recollects_known_handles(self, route):
        upsert_x_profile({"handle": "alice"}, "AI Agents")
        route["routes"]["/v1/balance"] = {"data": {"balance": 100}}
        route["routes"]["/v1/twitter/search"] = {
            "data": {"people": [_person("alice")]},
            "meta": {"creditsCharged": 1},
        }
        route["routes"]["/v1/twitter/profiles/"] = _timeline([_tweet("1")])

        x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=3, budget_credits=None,
            refresh=True,
        )
        assert x_collector.credits_spent() == 2

    def test_cache_uses_the_billed_handle_not_the_cards(self, route):
        """The timeline's profile card must not be able to poison the cache:
        a mismatched card would collapse several handles into one row."""
        route["routes"]["/v1/balance"] = {"data": {"balance": 100}}
        route["routes"]["/v1/twitter/search"] = {
            "data": {"people": [_person("alice"), _person("bob"),
                               _person("carol")]},
            "meta": {"creditsCharged": 1},
        }
        # Every response wrongly claims the card belongs to alice.
        route["routes"]["/v1/twitter/profiles/"] = {
            "data": {
                "lookupStatus": "found",
                "profile": {"handle": "alice", "displayName": "Alice"},
                "tweets": [],
                "page": {"hasMore": False, "nextCursor": None},
            },
            "meta": {"creditsCharged": 1},
        }

        x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=3, budget_credits=None
        )
        assert set(get_fetched_x_handles("AI Agents")) == {"alice", "bob", "carol"}

    def test_collected_tweets_are_normalized_and_saved(self, route):
        from database.db import get_posts

        route["routes"]["/v1/balance"] = {"data": {"balance": 100}}
        route["routes"]["/v1/twitter/search"] = {
            "data": {"people": [_person("alice", "Alice A (AI Agents fan)")]},
            "meta": {"creditsCharged": 1},
        }
        route["routes"]["/v1/twitter/profiles/"] = _timeline([
            {"id": "1", "text": "great post about agents https://x.com/a/status/1",
             "author": {"handle": "alice", "platformUserId": "u1"}},
            {"id": "2", "text": "hey @bob check this out",
             "author": {"handle": "alice", "platformUserId": "u1"}},
        ])

        x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=1, budget_credits=None
        )

        stored = {p["id"]: p for p in get_posts(topic_query="AI Agents")}
        assert len(stored) == 2
        # raw_text preserved for the mention-edge builder; text is cleaned.
        url_post = stored["x_1"]
        assert "x.com" not in url_post["text"]
        assert "x.com" in url_post["raw_text"]
        # Mentions survive in raw_text so the network builder can find them.
        assert "@bob" in stored["x_2"]["raw_text"]
        assert stored["x_2"]["author_handle"] == "@alice"

    def test_query_defaults_to_topic(self, route, monkeypatch):
        seen = {}

        def fake_discover(q, limit=20, api_key=None):
            seen["q"] = q
            return []

        monkeypatch.setattr(x_collector, "discover_x_profiles", fake_discover)
        monkeypatch.setattr(x_collector, "fetch_credit_balance",
                            lambda k: {"balance": 100})
        x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", budget_credits=None
        )
        assert seen["q"] == "AI Agents"

    def test_explicit_query_overrides_topic(self, route, monkeypatch):
        seen = {}

        def fake_discover(q, limit=20, api_key=None):
            seen["q"] = q
            return []

        monkeypatch.setattr(x_collector, "discover_x_profiles", fake_discover)
        monkeypatch.setattr(x_collector, "fetch_credit_balance",
                            lambda k: {"balance": 100})
        x_collector.collect_x_for_topic(
            "AI Agents", query="LLM agents", api_key="k", budget_credits=None
        )
        assert seen["q"] == "LLM agents"

    def test_empty_query_raises(self):
        with pytest.raises(ValueError, match="discovery query"):
            x_collector.collect_x_for_topic("   ")
