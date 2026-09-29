"""Relevance-filter tests.

The fixtures reproduce the three profiles a real "AI Agents" discovery returned
(giveaway/token accounts) alongside genuine commentators, so the filter is
pinned to the failure it was built for rather than to invented inputs.
"""
import pytest

import collectors.x_collector as x_collector
from collectors.x_collector import (
    filter_profiles, is_promo_profile, is_promo_tweet, matches_topic,
    split_promo_posts, topic_terms,
)


# --- real profiles from the 2026-09-29 "AI Agents" run ---------------------
REAL_SPAM = [
    {"handle": "gametyio", "displayName": "G-AGENTS AI?"},
    {"handle": "AAAPadSF",
     "displayName": "Autonomous Ai Agents PAD by PaloAlto Research Lab"},
    {"handle": "AiWhitebridge", "displayName": "WhiteBridge: AI Agents Network"},
]

REAL_LEGIT = [
    {"handle": "simonw", "displayName": "Simon Willison",
     "description": "AI engineer, LLMs and agents"},
    {"handle": "swyx", "displayName": "swyx",
     "description": "AI Engineer / #AI / agents / inference"},
]

# Their profile cards are clean; the giveaway is only in the tweets. This is
# the case that a name/bio filter provably cannot catch.
REAL_SPAM_TWEETS = [
    {"text": "Win a $1,000 USDT giveaway! Follow and RT to enter",
     "raw_text": "Win a $1,000 USDT giveaway! Follow and RT to enter"},
    {"text": "Claim your free airdrop, whitelist spots open now",
     "raw_text": "Claim your free airdrop, whitelist spots open now"},
    {"text": "Presale is live, join our Telegram for the drop",
     "raw_text": "Presale is live, join our Telegram for the drop"},
]

REAL_LEGIT_TWEETS = [
    {"text": "Tool calling still breaks on long agentic loops",
     "raw_text": "Tool calling still breaks on long agentic loops"},
    {"text": "Comparing MCP against plain function calls",
     "raw_text": "Comparing MCP against plain function calls"},
]


def _with_bio(handle, name, bio):
    return {"handle": handle, "displayName": name, "description": bio}


def _raw_tweet(tid, text):
    """A provider-shaped tweet, as the timeline route returns it."""
    return {"id": f"t{tid}", "text": text,
            "author": {"handle": "alice", "platformUserId": "u1"}}


class TestTopicTerms:
    def test_reduces_query_to_stems(self):
        assert topic_terms("AI Agents") == ["ai", "agent"]

    def test_singularises_simple_plurals(self):
        assert topic_terms("LLMs") == ["llm"]
        assert topic_terms("agents") == ["agent"]

    def test_drops_stopwords_and_short_noise(self):
        assert "the" not in topic_terms("the best AI news")
        assert "news" not in topic_terms("the best AI news")

    def test_empty_query_yields_no_terms(self):
        assert topic_terms("") == []
        # No terms means nothing to require, so everything matches.
        assert matches_topic({"displayName": "anything"}, []) is True


class TestTopicMatching:
    def test_matches_name_or_bio(self):
        assert matches_topic({"displayName": "AI Agents Network"}, ["ai", "agent"])
        assert matches_topic(
            {"displayName": "Some Name", "description": "building agents"},
            ["ai", "agent"],
        )

    def test_word_anchored_so_substrings_do_not_match(self):
        """'ai' must not match 'email', 'chain' or 'maintain'."""
        assert not matches_topic({"displayName": "email marketing"}, ["ai"])
        assert not matches_topic({"displayName": "supply chain news"}, ["ai"])

    def test_stem_matches_inflections(self):
        assert matches_topic({"displayName": "Autonomous agentic systems"},
                             ["agent"])

    def test_unrelated_profile_is_rejected(self):
        assert not matches_topic(
            {"displayName": "Coffee Roastery", "description": "beans"},
            ["ai", "agent"],
        )


class TestPromoDetection:
    def test_promo_phrases_in_a_profile_are_caught(self):
        assert is_promo_profile(_with_bio("t", "Giveaway Post", "win $500"))
        assert is_promo_profile(_with_bio("t", "Token", "$WBAI is moving"))

    def test_does_not_flag_legit_accounts(self):
        for p in REAL_LEGIT:
            assert not is_promo_profile(p), f"false positive on {p['handle']}"

    def test_short_ticker_does_not_trip(self):
        # "$AI" is only two letters; too weak a signal on its own.
        assert not is_promo_profile(_with_bio("shop", "Shop", "we sell $AI art"))

    def test_known_limit_clean_cards_hide_promo(self):
        """Documents the real gap: the live giveaway accounts had clean
        display names, so this check cannot see them. Guarded so a future
        attempt to claim otherwise is caught here."""
        for p in REAL_SPAM:
            assert not is_promo_profile(p), (
                f"{p['handle']} now trips the name check -- if this changed, "
                "re-check the tweet-level filter still exists"
            )


class TestPromoTweets:
    def test_catches_the_real_giveaway_posts(self):
        """This is the check that actually protects data quality."""
        for post in REAL_SPAM_TWEETS:
            assert is_promo_tweet(post), f"missed: {post['text']!r}"

    def test_does_not_flag_genuine_discussion(self):
        for post in REAL_LEGIT_TWEETS:
            assert not is_promo_tweet(post), f"false positive: {post['text']!r}"

    @pytest.mark.parametrize("text", [
        "Win a $1,000 USDT giveaway",
        "Free airdrop for all holders",
        "Presale is live now",
        "Join our Telegram chat for rewards",
        "Whitelist spots open",
        "Comment below to enter",
        "DM me to double your coin",
        "Contract address 0xdeadbeef1234",
    ])
    def test_promo_ctas_are_caught(self, text):
        assert is_promo_tweet({"text": text, "raw_text": text})

    def test_falls_back_to_text_when_raw_missing(self):
        assert is_promo_tweet({"text": "a giveaway for sure"})

    def test_splits_posts_and_flags_promo_account(self):
        clean, promo, flagged = split_promo_posts(REAL_SPAM_TWEETS)
        assert clean == []
        assert len(promo) == 3
        assert flagged is True

    def test_majority_promo_account_is_flagged(self):
        """Real case: @gametyio was 11/20 promo, and its other 9 tweets were
        partnership marketing too, so the account is dropped wholesale."""
        promo_texts = [t["text"] for t in REAL_SPAM_TWEETS * 4]      # 12
        clean_texts = [t["text"] for t in REAL_LEGIT_TWEETS * 3]    # 6
        posts = [_raw_tweet(i, t) for i, t in
                 enumerate(promo_texts + clean_texts)]
        clean, promo, flagged = split_promo_posts(posts)
        assert flagged is True
        assert len(clean) == 6
        assert len(promo) == 12

    def test_minority_promo_account_is_not_flagged(self):
        """One giveaway post in an otherwise genuine timeline must not
        disqualify the account."""
        posts = [_raw_tweet(0, REAL_SPAM_TWEETS[0]["text"])] + [
            _raw_tweet(i + 1, t["text"]) for i, t
            in enumerate(REAL_LEGIT_TWEETS * 5)
        ]
        clean, promo, flagged = split_promo_posts(posts)
        assert flagged is False
        assert len(promo) == 1
        assert len(clean) == 10

    def test_mixed_account_is_not_flagged_but_still_drops_promo(self):
        clean, promo, flagged = split_promo_posts(
            REAL_SPAM_TWEETS[:1] + REAL_LEGIT_TWEETS
        )
        assert len(clean) == 2
        assert len(promo) == 1
        assert flagged is False

    def test_empty_input_is_safe(self):
        clean, promo, flagged = split_promo_posts([])
        assert clean == [] and promo == [] and flagged is False


class TestFilterProfiles:
    def test_topic_requirement_drops_unrelated_profiles(self):
        unrelated = _with_bio("coffee", "Bean Co", "we roast coffee beans")
        kept, rejected = filter_profiles([unrelated] + REAL_LEGIT, "AI Agents")
        assert {p["handle"] for p in kept} == {"simonw", "swyx"}
        assert rejected[0][0] == "coffee"

    def test_promo_check_runs_before_the_topic_check(self):
        """A spam account that also matches the topic must still be dropped."""
        spam_that_matches = _with_bio(
            "cointoken", "AI Agents Network", "Giveaway: $NORAH RWA token"
        )
        kept, rejected = filter_profiles([spam_that_matches], "AI Agents")
        assert kept == []
        assert rejected[0][1] == "promo/spam markers"

    def test_topic_requirement_can_be_switched_off(self):
        profiles = [_with_bio("dev", "Some Dev", "I write software")]
        kept, rejected = filter_profiles(profiles, "AI Agents",
                                         require_topic=False)
        assert [p["handle"] for p in kept] == ["dev"]
        assert rejected == []

    def test_promo_filter_can_be_switched_off(self):
        promo = _with_bio("tok", "AI Agents Token", "Giveaway $WBAI")
        kept, rejected = filter_profiles([promo], "AI Agents", allow_promo=True)
        assert [p["handle"] for p in kept] == ["tok"]
        assert rejected == []

    def test_every_rejection_carries_a_reason(self):
        unrelated = _with_bio("coffee", "Bean Co", "roast beans")
        kept, rejected = filter_profiles([unrelated] + REAL_LEGIT, "AI Agents")
        assert kept
        for handle, reason in rejected:
            assert handle and reason


class TestFilterRunsBeforeSpending:
    def test_rejected_profiles_cost_nothing(self, monkeypatch):
        """Filtering early is only useful if rejects never bill.

        Asserts on requests issued, not on the ledger: replacing `_get`
        bypasses the ledger update, and the invariant under test is that no
        timeline request is ever made for a rejected handle.
        """
        requested = []

        def fake_get(path, params, api_key):
            requested.append(path)
            return {
                "data": {"people": [_with_bio("coffee", "Bean Co",
                                             "we roast coffee beans")]},
                "meta": {"creditsCharged": 1},
            }

        monkeypatch.setattr(x_collector, "_get", fake_get)
        monkeypatch.setattr(x_collector, "fetch_credit_balance",
                            lambda k: {"balance": 100})

        posts = x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=3, budget_credits=None
        )
        assert posts == []
        assert requested == ["/v1/twitter/search"], (
            "the rejected handle must never be requested"
        )

    def test_promo_tweets_are_dropped_and_handle_still_cached(self, monkeypatch):
        """The account is paid for once, then never re-billed.

        The profile card is deliberately clean -- exactly like the real
        giveaway accounts -- so this exercises the tweet-level filter rather
        than the cheaper pre-spend name check.
        """
        from database.db import get_fetched_x_handles

        requested = []

        def fake_get(path, params, api_key):
            requested.append(path)
            if "search" in path:
                return {"data": {"people": [
                    _with_bio("giveawaybot", "WhiteBridge: AI Agents Network",
                              "building the agents network")
                ]}, "meta": {"creditsCharged": 1}}
            return {
                "data": {
                    "lookupStatus": "found",
                    "tweets": [_raw_tweet(i, t["text"])
                               for i, t in enumerate(REAL_SPAM_TWEETS)],
                    "page": {"hasMore": False, "nextCursor": None},
                },
                "meta": {"creditsCharged": 1},
            }

        monkeypatch.setattr(x_collector, "_get", fake_get)
        monkeypatch.setattr(x_collector, "fetch_credit_balance",
                            lambda k: {"balance": 100})

        posts = x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=1, budget_credits=None
        )
        assert posts == [], "every promo tweet must be dropped"
        assert "giveawaybot" in get_fetched_x_handles("AI Agents"), (
            "promo handle must be cached so it is never re-billed"
        )

        # A re-run must not re-request the cached handle.
        before = len(requested)
        x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=1, budget_credits=None
        )
        assert requested[before:] == ["/v1/twitter/search"]

    def test_mixed_profile_keeps_clean_tweets(self, monkeypatch):
        tweets = [_raw_tweet(0, REAL_SPAM_TWEETS[0]["text"])] + [
            _raw_tweet(i + 1, t["text"]) for i, t in enumerate(REAL_LEGIT_TWEETS)
        ]

        def fake_get(path, params, api_key):
            if "search" in path:
                return {"data": {"people": [
                    _with_bio("mixed", "AI Agents Daily", "agents and llms")
                ]}, "meta": {"creditsCharged": 1}}
            return {
                "data": {"lookupStatus": "found", "tweets": tweets,
                         "page": {"hasMore": False, "nextCursor": None}},
                "meta": {"creditsCharged": 1},
            }

        monkeypatch.setattr(x_collector, "_get", fake_get)
        monkeypatch.setattr(x_collector, "fetch_credit_balance",
                            lambda k: {"balance": 100})

        posts = x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=1, budget_credits=None
        )
        # 3 tweets, 1 promo -> below the majority bar, so the account is kept
        # and only the giveaway post is dropped.
        assert len(posts) == 2, "clean tweets must survive the promo filter"

    def test_majority_promo_profile_contributes_nothing(self, monkeypatch):
        from database.db import get_fetched_x_handles

        tweets = [_raw_tweet(i, t["text"]) for i, t in
                  enumerate(REAL_SPAM_TWEETS + REAL_LEGIT_TWEETS)]

        def fake_get(path, params, api_key):
            if "search" in path:
                return {"data": {"people": [
                    _with_bio("spammer", "AI Agents Network", "agents")
                ]}, "meta": {"creditsCharged": 1}}
            return {
                "data": {"lookupStatus": "found", "tweets": tweets,
                         "page": {"hasMore": False, "nextCursor": None}},
                "meta": {"creditsCharged": 1},
            }

        monkeypatch.setattr(x_collector, "_get", fake_get)
        monkeypatch.setattr(x_collector, "fetch_credit_balance",
                            lambda k: {"balance": 100})

        posts = x_collector.collect_x_for_topic(
            "AI Agents", api_key="k", max_profiles=1, budget_credits=None
        )
        assert posts == [], "a promo account must contribute no tweets at all"
        # Paid once, then never re-billed.
        assert "spammer" in get_fetched_x_handles("AI Agents")

