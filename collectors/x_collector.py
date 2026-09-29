"""X (Twitter) collector backed by the Social Fetch API and Redis Caching.

Mirrors the YouTube collector's two-stage shape:

    DISCOVER  GET /v1/twitter/search?section=people   -> candidate handles
    FETCH     GET /v1/twitter/profiles/{handle}/tweets -> their tweets

The discovered tweets are what get stored and analyzed; the `x_profiles`
table is bookkeeping only, so re-runs never re-pay a credit for a handle
whose timeline was already pulled.

Credit metering & Caching:
--------------------------
* Uses SocialFetch API with credit budgeting and x_credits.json ledger.
* Integrated with Redis query caching (1 hour TTL) to prevent repeated API charges.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

from normalizer.normalizer import dedupe, normalize_posts, normalize_timestamp, stable_post_id

load_dotenv()

API_BASE = "https://api.socialfetch.dev"
ENV_KEY_NAME = "SOCIALFETCH_API_KEY"

REQUEST_COST = 1  # flat cost of any single successful Twitter request

# search caps `limit` at 20; profile-tweets caps it at 100.
PROFILE_DISCOVERY_LIMIT = 20
TWEETS_PAGE_LIMIT = 100

# Prototype defaults: 1 discovery + 3 profiles = 4 credits, ~300 tweets.
FREE_SIGNUP_CREDITS = 100
DEFAULT_MAX_PROFILES = 3
DEFAULT_MAX_PAGES = 1
DEFAULT_BUDGET_CREDITS = 4
DEFAULT_INCLUDE_REPLIES = True

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1

LEDGER_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "x_credits.json")
)

DEFAULT_QUERY_LIMIT = 50


def _get_redis_client():
    """Retrieve Redis client for query caching if available."""
    try:
        from task_queue.job_manager import get_job_manager
        jm = get_job_manager()
        if jm and jm.is_redis_active and jm._redis_client:
            return jm._redis_client
    except Exception:
        pass
    return None


from dotenv import load_dotenv

from normalizer.normalizer import normalize_timestamp, stable_post_id

load_dotenv()

API_BASE = "https://api.socialfetch.dev"
ENV_KEY_NAME = "SOCIALFETCH_API_KEY"

REQUEST_COST = 1  # flat cost of any single successful Twitter request

# search caps `limit` at 20; profile-tweets caps it at 100.
PROFILE_DISCOVERY_LIMIT = 20
TWEETS_PAGE_LIMIT = 100

# Prototype defaults: 1 discovery + 3 profiles = 4 credits, ~300 tweets.
FREE_SIGNUP_CREDITS = 100
DEFAULT_MAX_PROFILES = 3
DEFAULT_MAX_PAGES = 1
DEFAULT_BUDGET_CREDITS = 4
DEFAULT_INCLUDE_REPLIES = True

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1

LEDGER_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "x_credits.json")
)


class XCreditsExceededError(Exception):
    """Raised when the run's credit budget, or the account balance, is gone."""


# --- credit ledger ---------------------------------------------------------
# Lifetime-cumulative on purpose. Credits never refill, so a date-keyed ledger
# (like the YouTube one) would silently reset and let a prototype run drain the
# free grant without ever tripping the guard.


def _load_ledger():
    try:
        with open(LEDGER_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("ledger is not an object")
        return {"credits_spent": int(data.get("credits_spent") or 0)}
    except (OSError, ValueError, TypeError):
        return {"credits_spent": 0}


def _save_ledger(data):
    directory = os.path.dirname(LEDGER_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(LEDGER_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def credits_spent():
    """Total credits billed to this key, across every run."""
    return _load_ledger()["credits_spent"]


def spend_credits(units):
    """Record credits billed. Driven by meta.creditsCharged from the response."""
    data = _load_ledger()
    data["credits_spent"] += max(0, int(units))
    _save_ledger(data)


def remaining_credits(balance=None):
    """Credits left before the provider starts returning 402.

    Prefers the live balance; falls back to the signup grant minus the local
    lifetime counter when no balance is supplied.
    """
    if balance is not None:
        return max(0, int(balance))
    return max(0, FREE_SIGNUP_CREDITS - credits_spent())


def _get_api_key():
    key = os.environ.get(ENV_KEY_NAME)
    if not key:
        raise RuntimeError(
            "Social Fetch API key missing. Set SOCIALFETCH_API_KEY in your "
            ".env file (see .env.example)."
        )
    return key


def _backoff(attempt):
    time.sleep(RETRY_BACKOFF_SECONDS * (2 ** attempt))


def _get(path, params, api_key):
    """Perform one billable GET and reconcile its credit cost.

    Every Twitter route costs credits, so all reconciliation happens here.
    Retries 502/503 (documented as never charged) without touching the ledger.
    Re-raises 402 as XCreditsExceededError; note the provider also uses 402 for
    x402 USDC payment challenges, so only an explicit `insufficient_credits`
    code is reported as an empty balance.
    """
    url = f"{API_BASE}{path}"
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    last_status = None
    for attempt in range(MAX_RETRIES):
        resp = requests.get(url, params=params, headers=headers,
                            timeout=REQUEST_TIMEOUT)

        if resp.status_code == 402:
            code = ""
            try:
                code = (resp.json().get("error") or {}).get("code") or ""
            except ValueError:
                pass
            if code == "insufficient_credits":
                raise XCreditsExceededError(
                    "Social Fetch credits exhausted (402 insufficient_credits). "
                    "Top up at https://app.socialfetch.dev or lower "
                    "--x-max-profiles."
                )
            raise XCreditsExceededError(
                "Social Fetch returned 402 with code "
                f"{code!r}. This is an x402 payment challenge, not an empty "
                "balance -- pay the challenge or supply an x-api-key."
            )

        if resp.status_code in (502, 503):
            # Not charged, so retry without spending.
            last_status = resp.status_code
            _backoff(attempt)
            continue

        resp.raise_for_status()
        payload = resp.json()

        charged = (payload.get("meta") or {}).get("creditsCharged")
        spend_credits(REQUEST_COST if charged is None else charged)
        return payload

    raise RuntimeError(
        f"Social Fetch {path} failed after {MAX_RETRIES} attempts "
        f"(last status {last_status}); not charged."
    )

            if code == "insufficient_credits":
                raise XCreditsExceededError(
                    "Social Fetch credits exhausted (402 insufficient_credits). "
                    "Top up at https://app.socialfetch.dev or lower "
                    "--x-max-profiles."
                )
            raise XCreditsExceededError(
                "Social Fetch returned 402 with code "
                f"{code!r}. This is an x402 payment challenge, not an empty "
                "balance -- pay the challenge or supply an x-api-key."
            )

        if resp.status_code in (502, 503):
            # Not charged, so retry without spending.
            last_status = resp.status_code
            _backoff(attempt)
            continue

        resp.raise_for_status()
        payload = resp.json()

        charged = (payload.get("meta") or {}).get("creditsCharged")
        spend_credits(REQUEST_COST if charged is None else charged)
        return payload

    raise RuntimeError(
        f"Social Fetch {path} failed after {MAX_RETRIES} attempts "
        f"(last status {last_status}); not charged."
    )


def fetch_credit_balance(api_key=None):
    """Read the live credit balance. This route is free -- it costs no credit."""
    import requests

    api_key = api_key or _get_api_key()
    resp = requests.get(
        f"{API_BASE}/v1/balance",
        headers={"x-api-key": api_key, "Accept": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return (resp.json().get("data") or {})


# --- stage 1: discovery ----------------------------------------------------

# Discovery returns accounts that merely *mention* the query, not accounts
# about it. A live run on "AI Agents" surfaced three giveaway/token accounts
# before any real commentator, and they skewed sentiment 37 positive / 3
# negative, so the filter below runs on the free-to-inspect profile cards
# BEFORE any timeline credit is spent.

# Unambiguous promo/spam markers. Kept deliberately narrow: a false positive
# here silently drops a real account, so only terms that are meaningless
# outside a promotion are listed.
PROMO_PATTERNS = (
    r"\bgive\s?away\b", r"\bair\s?drop\b", r"\bpresale\b", r"\bpre-?sale\b",
    r"\bwhitelist\b", r"\breferral\b", r"\brefer\s?a\s?friend\b",
    r"\bcasino\b", r"\bbetting\b", r"\bjackpot\b", r"\bslot machine\b",
    r"\busdt\b", r"\busdc\b", r"\bbnb chain\b", r"\bmeme\s?coin\b",
    r"\bpump\b", r"\bshills?\b", r"\bfomo\b", r"\bico\b", r"\bid0\b",
    r"\bwinner[s]?\b", r"\bprize\s?pool\b", r"\bjoin (?:our|the) (?:telegram|discord|chat)\b",
    r"\bfree\s+money\b", r"\bdouble\s+your\b", r"\bairdrop\b",
    r"\bclaim your\b", r"\bcex\b", r"\bexchange listing\b",
    r"\bliquidity\b", r"\bstaking pool\b", r"\brug\b",
)

# A $TICKER in a name or bio is the single strongest promo tell. Requires 3+
# letters so "$AI" or a bare "$" does not trip it.
TICKER_PATTERN = re.compile(r"\$\s?[A-Z]{3,10}\b")

# Profile cards under-report spam: a live "AI Agents" run returned three
# giveaway accounts whose display names and bios were clean ("WhiteBridge: AI
# Agents Network"), with the promotion only visible in the tweets themselves
# (24 of 62 collected tweets carried giveaway CTAs). So the decisive filter is
# per-tweet, and the profile-level check above is only a cheap pre-spend pass.
PROMO_TWEET_PATTERNS = (
    r"\bgive\s?away\b", r"\bair\s?drop\b", r"\bpre-?sale\b", r"\bwhitelist\b",
    r"\bcasino\b", r"\bbetting\b", r"\bjackpot\b", r"\busdt\b", r"\busdc\b",
    r"\bwinner[s]?\b", r"\bprize\s?pool\b", r"\bclaim your\b",
    r"\bcomment below\b", r"\bfollow (?:and|&) ?rt\b", r"\blike (?:and|&) rt\b",
    r"\bdm me\b", r"\bdm (?:us|me) to\b", r"\bsend (?:us|me) (?:a )?(?:dm|bars)\b",
    r"\bt\.me/\w+", r"\bjoin (?:our|the) (?:telegram|discord|chat|group)\b",
    r"\breferral (?:link|code|bonus)\b", r"\bfree (?:money|crypto|usdt)\b",
    r"\bdouble your\b", r"\bmeme\s?coin\b", r"\brug\b", r"\bape\b",
    r"\bto the moon\b", r"\b100x\b", r"\bx\d{2,}\b", r"\bbuying (?:in|now)\b",
    r"\bcontract address\b", r"\bca:\s*0x", r"\b0x[a-f0-9]{6,}\b",
)

# A profile whose timeline is at least this fraction promo is treated as a
# promo account: its clean tweets are still kept, but the handle is cached so
# re-runs never re-bill it.
PROMO_TWEET_RATIO = 0.5

# Terms that carry no topical signal and would match almost every bio.
_TOPIC_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with",
    "best", "top", "news", "about", "latest", "vs", "by", "is", "are",
    "new", "how", "why", "what", "get", "using", "use",
})


def _profile_text(profile):
    """All human-readable text on a profile card, joined by spaces.

    The bio field name is not guaranteed across provider responses, so the
    common aliases are all read. Whatever is present is used; a profile with
    only a display name is still checkable. Original casing is preserved
    because the $TICKER check is case-sensitive.
    """
    parts = [str(profile.get("handle") or "")]
    for key in ("displayName", "display_name", "description", "bio",
                "profileDescription", "about", "summary"):
        value = profile.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def topic_terms(query):
    """Reduce a query to matchable topic stems, e.g. 'AI Agents' -> ai, agent."""
    terms = []
    for raw in re.split(r"[^a-z0-9+]+", (query or "").lower()):
        if not raw or raw in _TOPIC_STOPWORDS:
            continue
        stem = raw[:-1] if len(raw) > 3 and raw.endswith("s") else raw
        if len(stem) >= 2 and stem not in terms:
            terms.append(stem)
    return terms


def is_promo_profile(profile):
    """True for giveaway/token/affiliate accounts. Used as a hard reject."""
    text = _profile_text(profile)
    for pattern in PROMO_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    # Ticker check is case-sensitive, so it uses the original casing.
    return bool(TICKER_PATTERN.search(text))


def matches_topic(profile, terms):
    """True when a topic stem appears as a whole word in the profile text.

    Word-anchored on purpose: a bare substring test for 'ai' would match
    'email', 'chain' and 'maintain'.
    """
    if not terms:
        return True
    text = _profile_text(profile)
    for term in terms:
        if re.search(rf"\b{re.escape(term)}\w*\b", text, re.IGNORECASE):
            return True
    return False


def filter_profiles(profiles, query, require_topic=True, allow_promo=False):
    """Split discovery results into (kept, rejected) with reasons.

    Runs before any timeline request, so a rejected profile costs nothing --
    that is the whole point: bad handles are dropped at 0 credits, not 1.
    """
    terms = topic_terms(query)
    kept, rejected = [], []

    for profile in profiles:
        handle = profile.get("handle") or "(no handle)"
        if not allow_promo and is_promo_profile(profile):
            rejected.append((handle, "promo/spam markers"))
        elif require_topic and not matches_topic(profile, terms):
            rejected.append((handle, f"no topic term from {', '.join(terms) or query!r}"))
        else:
            kept.append(profile)

    return kept, rejected


def is_promo_tweet(post):
    """True when a post is a giveaway/token/affiliate pitch.

    This is the check that actually matters for data quality: a giveaway
    account's profile card looks clean, its posts do not.
    """
    text = str(post.get("raw_text") or post.get("text") or "")
    for pattern in PROMO_TWEET_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def split_promo_posts(posts):
    """Split a profile's posts into (clean, promo, is_promo_account)."""
    clean, promo = [], []
    for post in posts:
        (promo if is_promo_tweet(post) else clean).append(post)

    total = len(clean) + len(promo)
    ratio = (len(promo) / total) if total else 0.0
    return clean, promo, ratio >= PROMO_TWEET_RATIO



def discover_x_profiles(query, limit=PROFILE_DISCOVERY_LIMIT, api_key=None):
    """Find X profiles related to `query`. Costs 1 credit.

    Uses the search route's `section=people`, which returns profile cards
    instead of tweets. `limit` is capped at 20 by the API.
    """
    api_key = api_key or _get_api_key()
    limit = max(1, min(int(limit), PROFILE_DISCOVERY_LIMIT))

    payload = _get(
        "/v1/twitter/search",
        {"query": query, "section": "people", "limit": limit},
        api_key,
    )

    people = (payload.get("data") or {}).get("people") or []
    return [p for p in people if p.get("handle")]


# --- stage 2: tweets per profile -----------------------------------------


def _map_tweet(tweet, topic_query):
    """Map one Social Fetch tweet onto the uniform posts schema."""
    author = tweet.get("author") or {}
    metrics = tweet.get("metrics") or {}
    handle = (author.get("handle") or "").lstrip("@")
    text = tweet.get("text") or ""

    if not handle or not text.strip():
        return None

    # parent_id must carry the platform prefix so it lines up with `id` --
    # analytics/network.py resolves the reply edge via post_author[parent_id].
    # The other collectors follow the same rule (yt_..., <channel>_...).
    # The old Nitter collector hardcoded None, which is why the influence
    # graph was a 1-edge star regardless of how many tweets were collected.
    reply_to = tweet.get("inReplyToStatusId")

    return {
        "id": stable_post_id("x", tweet.get("id"), text),
        "platform": "x",
        "author_id": author.get("platformUserId"),
        # Bare screen name, "@"-prefixed to match the Telegram collector.
        # The network builder keys nodes on author_handle and matches
        # @mentions either bare or prefixed, so this is what lets mention
        # edges resolve across platforms.
        "author_handle": f"@{handle}",
        "text": text,
        # Already ISO-8601 from the API; normalize_timestamp handles the "Z".
        "created_at": normalize_timestamp(tweet.get("createdAt")),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "parent_id": stable_post_id("x", reply_to, "") if reply_to else None,
        "topic_query": topic_query,
        "reactions": metrics.get("likes") or 0,
        "shares": metrics.get("retweets") or 0,
        "replies": metrics.get("replies") or 0,
        "views": metrics.get("views") or None,
    }


def collect_x_profile_tweets(handle, topic_query, limit=TWEETS_PAGE_LIMIT,
                             max_pages=DEFAULT_MAX_PAGES,
                             include_replies=DEFAULT_INCLUDE_REPLIES,
                             api_key=None, max_posts=None):
    """Fetch up to `max_pages` timeline pages for one handle (1 credit each).

    Returns (posts, lookup_status, profile_card). `lookup_status` is the
    provider's outcome -- `found`, `private` or `not_found` -- and the last two
    still cost a credit while yielding no tweets, which is why the caller
    records them so they are never re-paid for.
    """
    api_key = api_key or _get_api_key()
    clean_handle = (handle or "").lstrip("@")
    if not clean_handle:
        return [], "not_found", None

    limit = max(1, min(int(limit), TWEETS_PAGE_LIMIT))

    posts = []
    profile = None
    lookup_status = "found"
    cursor = None

    for _ in range(max(1, int(max_pages))):
        params = {"limit": limit, "includeReplies": str(bool(include_replies)).lower()}
        if cursor:
            params["cursor"] = cursor

        payload = _get(
            f"/v1/twitter/profiles/{clean_handle}/tweets", params, api_key
        )
        data = payload.get("data") or {}

        lookup_status = data.get("lookupStatus") or lookup_status
        profile = data.get("profile") or profile

        for tweet in data.get("tweets") or []:
            mapped = _map_tweet(tweet, topic_query)
            if mapped:
                posts.append(mapped)

        page = data.get("page") or {}
        cursor = page.get("nextCursor")

        if not page.get("hasMore") or not cursor:
            break
        if max_posts is not None and len(posts) >= max_posts:
            break

    if max_posts is not None:
        posts = posts[:max_posts]

    return posts, lookup_status, profile


# --- orchestration ---------------------------------------------------------


def _profile_row(profile, handle=None):
    """Map a Social Fetch profile card onto the uniform x_profiles shape.

    Kept here, not in `database/db.py`, so the persistence layer never has to
    know that the provider spells this field `displayName`.

    `handle` overrides whatever the card says. The handle we actually billed for
    is the only trustworthy identity -- a card from a different response would
    otherwise poison the cache under the wrong primary key.
    """
    return {
        "handle": (handle or profile.get("handle") or "").lstrip("@"),
        "display_name": profile.get("displayName") or profile.get("display_name"),
        "platformUserId": profile.get("platformUserId"),
        "metrics": {
            "followers": (profile.get("metrics") or {}).get("followers"),
            "tweets": (profile.get("metrics") or {}).get("tweets"),
        },
    }


def _save_collected(posts):
    from database.db import save_posts
    from normalizer.normalizer import dedupe, normalize_posts
    save_posts(dedupe(normalize_posts(posts), key="id"))


def plan_credit_cost(max_profiles, max_pages, discovery_queries=1):
    """Exact credit cost of a run, computed before anything is spent."""
    requests_ = max(0, int(discovery_queries)) + max(0, int(max_profiles)) * max(
        1, int(max_pages)
    )
    return requests_ * REQUEST_COST


def collect_x_for_topic(topic_query, query=None, max_profiles=DEFAULT_MAX_PROFILES,
                        max_pages=DEFAULT_MAX_PAGES,
                        budget_credits=DEFAULT_BUDGET_CREDITS,
                        tweets_per_page=TWEETS_PAGE_LIMIT,
                        include_replies=DEFAULT_INCLUDE_REPLIES,
                        refresh=False, dry_run=False, api_key=None,
                        require_topic=True, allow_promo=False):
    """Discover profiles for a topic, then collect their tweets.

    Credit guards, in order, all before the first billable request:
      1. `dry_run` reports the plan and spends nothing
      2. `budget_credits` caps a single run
      3. the live balance (free to read) caps the account

    Returns posts in the uniform schema. Skips handles already pulled for this
    topic unless `refresh` is set, so re-runs are free.
    """
    from database.db import (
        create_database, get_fetched_x_handles, upsert_x_profile,
    )
    discovery_query = (query or topic_query or "").strip()
    if not discovery_query:
        raise ValueError("X collection needs a topic or discovery query")

    max_profiles = max(0, int(max_profiles))
    max_pages = max(1, int(max_pages))
    # 0 is a real budget (block everything), so only None disables the guard.
    budget = None if budget_credits is None else int(budget_credits)

    already_fetched = [] if refresh else set(get_fetched_x_handles(topic_query))
    planned_cost = plan_credit_cost(max_profiles, max_pages)

    print(f"[X] Topic '{topic_query}' -> discovering profiles for "
          f"'{discovery_query}'")
    print(f"[X] Plan: up to {max_profiles} profile(s) x {max_pages} page(s) "
          f"= {planned_cost} credit(s)")

    if dry_run:
        if already_fetched:
            print(f"[X] Already collected (skipped unless --x-refresh): "
                  f"{len(already_fetched)} handle(s)")
        print("[X] Dry run -- no credits spent.")
        return []

    if budget is not None and planned_cost > budget:
        raise XCreditsExceededError(
            f"Planned cost {planned_cost} credits exceeds the per-run budget "
            f"of {budget}. Lower --x-max-profiles or --x-max-pages."
        )

    api_key = api_key or _get_api_key()

    try:
        balance = fetch_credit_balance(api_key).get("balance")
    except Exception as e:  # balance is advisory; never block on it
        print(f"[X] Could not read live balance ({e}); using local ledger")
        balance = None

    left = remaining_credits(balance)
    print(f"[X] Credits available: {left} (spent to date: {credits_spent()})")
    if left < planned_cost:
        raise XCreditsExceededError(
            f"Only {left} credit(s) available but the plan needs "
            f"{planned_cost}. Lower --x-max-profiles or top up."
        )

    create_database()

    profiles = discover_x_profiles(discovery_query, api_key=api_key)
    print(f"[X] Discovery returned {len(profiles)} candidate profile(s)")

    # Filter BEFORE any timeline request: a rejected handle costs 0 credits
    # instead of 1, so a noisy discovery result is cheap rather than expensive.
    profiles, rejected = filter_profiles(
        profiles, discovery_query, require_topic=require_topic,
        allow_promo=allow_promo,
    )
    if rejected:
        print(f"[X] Relevance filter dropped {len(rejected)} profile(s) at no cost:")
        for handle, reason in rejected:
            print(f"     @{handle}: {reason}")
    print(f"[X] {len(profiles)} profile(s) passed the relevance filter")

    if not profiles:
        print("[X] No profile passed the filter. Re-run with "
              "--x-allow-promo / without --x-require-topic to widen it, "
              "or use a more specific query.")
        return []

    collected = []
    profiles_fetched = 0
    for profile in profiles:
        if profiles_fetched >= max_profiles:
            break

        handle = (profile.get("handle") or "").lstrip("@")
        if not handle:
            continue
        if handle in already_fetched:
            print(f"  -> @{handle}: already collected, skipping")
            continue

        profiles_fetched += 1
        try:
            posts, lookup_status, _card = collect_x_profile_tweets(
                handle, topic_query, limit=tweets_per_page, max_pages=max_pages,
                include_replies=include_replies, api_key=api_key,
            )
        except XCreditsExceededError:
            # Nothing was billed for this handle, so do NOT record it as
            # fetched -- caching it here would skip it forever.
            if collected:
                _save_collected(collected)
            raise
        except Exception as e:
            print(f"  [WARN] @{handle} failed: {e}")
            profiles_fetched -= 1
            continue

        clean_posts, promo_posts, is_promo_account = split_promo_posts(posts)

        # A promo account is a marketing account: its "clean" posts are still
        # promotion (partnership announcements, launch news), so the whole
        # handle is dropped rather than partially kept.
        if is_promo_account:
            clean_posts = []
            lookup_status = f"{lookup_status}+promo"
            print(f"  -> @{handle}: promo account, dropped "
                  f"{len(promo_posts)}/{len(posts)} tweet(s) [cached]")
        else:
            collected.extend(clean_posts)
            if promo_posts:
                print(f"  -> @{handle}: {len(promo_posts)}/{len(posts)} tweet(s) "
                      f"dropped as promo/giveaway [{lookup_status}]")
            else:
                print(f"  -> @{handle}: {len(clean_posts)} tweet(s) [{lookup_status}]")

        # Record every handle we paid for -- including private/not_found and
        # promo-only ones that yielded nothing usable -- so they are never
        # re-billed on a later run. A giveaway account is exactly the handle
        # we must not pay for twice.
        upsert_x_profile(
            _profile_row(profile, handle=handle), topic_query,
            lookup_status=lookup_status,
            tweets_collected=len(clean_posts),
        )

    if collected:
        _save_collected(collected)

    print(f"[X] Total collected: {len(collected)} tweets | "
          f"credits spent to date: {credits_spent()}")
    return collected


def collect_x_search(query, topic_query, limit=DEFAULT_QUERY_LIMIT, use_cache=True):
    """Backwards-compatible wrapper calling SocialFetch topic collection with Redis caching."""
    cache_key = None
    r_client = _get_redis_client() if use_cache else None
    if r_client:
        try:
            q_hash = hashlib.md5(f"{query}:{topic_query}:{limit}".encode()).hexdigest()
            cache_key = f"cache:x_search:{q_hash}"
            cached_val = r_client.get(cache_key)
            if cached_val:
                posts = json.loads(cached_val)
                print(f"[X collector] Retrieved {len(posts)} cached tweets from Redis for query '{query}'")
                return posts
        except Exception:
            pass

    try:
        posts = collect_x_for_topic(
            topic_query=topic_query,
            query=query,
            max_profiles=3,
            max_pages=1,
            budget_credits=4,
        )
        if r_client and cache_key and posts:
            try:
                r_client.setex(cache_key, 3600, json.dumps(posts))
            except Exception:
                pass
        return posts
    except Exception as ex:
        print(f"[X collector] Notice: {ex}")
        return []


def collect_x_profile(handle, topic_query, limit=DEFAULT_QUERY_LIMIT):
    """Scrape recent tweets from a specific user profile handle."""
    clean_handle = handle.lstrip("@")
    posts, _, _ = collect_x_profile_tweets(clean_handle, topic_query, limit=limit)
    return posts


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collect X tweets via Social Fetch")
    parser.add_argument("--topic", required=True, help="Topic recorded on each post")
    parser.add_argument("--query", default=None,
                        help="Discovery query (defaults to --topic)")
    parser.add_argument("--max-profiles", type=int, default=DEFAULT_MAX_PROFILES)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--budget-credits", type=int, default=DEFAULT_BUDGET_CREDITS)
    parser.add_argument("--tweets-per-page", type=int, default=TWEETS_PAGE_LIMIT)
    parser.add_argument("--no-include-replies", action="store_true",
                        help="Skip reply tweets (they are included by default)")
    parser.add_argument("--refresh", action="store_true",
                        help="Re-collect handles already pulled for this topic")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan and credit cost without spending")
    args = parser.parse_args()

    collect_x_for_topic(
        args.topic,
        query=args.query,
        max_profiles=args.max_profiles,
        max_pages=args.max_pages,
        budget_credits=args.budget_credits,
        tweets_per_page=args.tweets_per_page,
        include_replies=not args.no_include_replies,
        refresh=args.refresh,
        dry_run=args.dry_run,
    )

