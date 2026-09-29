# AGENTS.md

## What this is

Python social media analytics pipeline. Collects posts from Telegram, X and YouTube, normalizes them, runs sentiment + emotion analysis (transformers), infers demographics, detects trends, builds an influence network, stores everything in SQLite (`social.db`), and visualizes via a Streamlit dashboard.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Running the pipeline

```bash
# Full pipeline (collect + analyze)
python run_pipeline.py --topic "AI Agents"

# Collect only, skip analysis
python run_pipeline.py --topic "AI Agents" --no-analyze

# Skip collection, re-analyze existing DB data
python run_pipeline.py --topic "AI Agents" --no-collect

# Custom channels / queries / YouTube videos
python run_pipeline.py --channels @aipost @KDnuggets --x-queries "AI Agents" "LLM"
python run_pipeline.py --topic "AI Agents" --youtube-urls "https://www.youtube.com/watch?v=VIDEO_ID"

# X collection (Social Fetch, metered in credits)
python run_pipeline.py --x-dry-run                      # print the plan, spend nothing
python run_pipeline.py --x-queries "AI Agents"          # 1 discovery + 3 profiles = 4 credits
python run_pipeline.py --x-queries "AI Agents" --x-max-profiles 1 --x-budget-credits 2
python run_pipeline.py --x-queries "AI Agents" --x-max-pages 3   # 1 + 3*3 = 10 credits
python run_pipeline.py --x-queries "AI Agents" --x-refresh       # re-pull cached handles
python run_pipeline.py --x-queries "AI Agents" --x-no-include-replies
python run_pipeline.py --x-queries "AI Agents" --x-no-require-topic  # widen the relevance filter
python run_pipeline.py --x-queries "AI Agents" --x-allow-promo       # keep giveaway/token accounts

# YouTube topic discovery (ON by default; tune it below)
python run_pipeline.py --topic "AI Agents" --yt-max-videos 5 --yt-comments 100
python run_pipeline.py --topic "AI Agents" --no-youtube-search   # disable discovery
python run_pipeline.py --topic "AI Agents" --yt-refresh          # re-fetch cached videos
python run_pipeline.py --topic "AI Agents" --yt-budget-units 2000

# Skip optional analysis stages
python run_pipeline.py --skip-emotions --skip-demographics --skip-network --skip-narrative
```

## Running the dashboard

```bash
cd dashboard
streamlit run app.py
```

The DB connection is anchored to the project root (`database/db.py` resolves `../social.db`), so the dashboard finds the same `social.db` as the pipeline regardless of the directory you launch from. An idle `dashboard/social.db` left by older runs is a stale artifact and can be deleted.

## Environment variables

Telegram collector requires `.env` file with:
- `TG_API_ID` — from https://my.telegram.org
- `TG_API_HASH` — from https://my.telegram.org

X collector (via Social Fetch) requires `SOCIALFETCH_API_KEY` — see below.
YouTube collector (via YouTube Data API v3) requires `YOUTUBE_API_KEY`.

The narrative report stage optionally uses Google Gemini:
- `LLM_API_KEY` — Google AI Studio key (https://aistudio.google.com/apikey). If absent, the pipeline falls back to a deterministic template report instead of an LLM call.
- `LLM_MODEL` — optional model override (default `gemini-3.5-flash`; `gemini-2.5-flash` is retired for new API users).

## Architecture

```
collectors/        Telegram (Telethon), X (Social Fetch) and YouTube (Data API v3) scrapers
normalizer/        Text cleaning, dedup, tokenization
analytics/         Sentiment + emotion (HuggingFace transformers), demographics,
                   trend detection (TF-IDF), network analysis (NetworkX),
                   narrative report (Gemini API or template)
database/          SQLite schema and CRUD (social.db)
dashboard/         Streamlit UI
run_pipeline.py    CLI entrypoint wiring the stages together
tests/             pytest suite (isolated DBs under .test_tmp/, mocked models)
reports/           Markdown narrative reports written by the pipeline
```

## Key quirks

- **Sentiment model downloads on first run** (`cardiffnlp/twitter-roberta-base-sentiment-latest`). Slow startup until cached.
- **Emotion model downloads on first run** (`j-hartmann/emotion-english-distilroberta-base`). Same slow-first-run caveat.
- **Text truncated to 512 tokens** before model analysis (transformer limit).
- **X collection goes through Social Fetch, two stages** — `collectors/x_collector.py` first discovers profiles for the query (`GET /v1/twitter/search?section=people`), then pulls each profile's timeline (`GET /v1/twitter/profiles/{handle}/tweets`). Only the **tweets** are stored and analyzed; `x_profiles` is bookkeeping, exactly like `youtube_videos`. Replaces the old Nitter scraper (`ntscraper` is gone).
- **X profile tweets are the unit of collection** — `--x-queries` are *discovery queries* (they find people, they are not searched for tweets). `--x-max-profiles` (default 3) profiles are fetched per query; `--x-max-pages` (default 1) timeline pages per profile; replies are included by default (`--x-no-include-replies` opts out).
- **Social Fetch credits are flat 1 per successful request, never refunded** — discovery 1 credit, each timeline page 1 credit, no tiers and no attempt floor. So a default run is 1 + 3 = 4 credits. The API accepts `limit=100`, but a live run on "AI Agents" returned only 20-22 tweets per profile page, so treat yield as **~20 per credit observed, not the 100 the API advertises**; `private`/`not_found` profiles bill and return nothing.
- **X spend is ledger-tracked** — `collectors/x_collector.py` keeps lifetime-cumulative spend in a gitignored `x_credits.json` (`{"credits_spent"}`). It is deliberately **not** date-keyed (unlike the YouTube ledger): credits are prepaid and never refill, so a date key would silently reset and drain the free 100-credit grant. Runs pre-check `--dry-run` (free), then a per-run cap (`--x-budget-credits`, default 4), then the live balance via the free `GET /v1/balance`. `meta.creditsCharged` is always the source of truth, never a local estimate.
- **Handle cache prevents re-billing** — `x_profiles` (keyed by `handle + topic_query`) records every handle we paid for, including `private`/`not_found` and promo-only ones that returned zero usable tweets, so re-runs skip them free. `--x-refresh` forces a re-fetch. `upsert_x_profile` stamps `last_fetched_at` automatically and the *billed handle* wins over whatever a profile card claims, so a mismatched card cannot poison the cache. Note the cache saves the *timeline* request only: re-running the same topic still pays 1 credit for discovery before the known handles are skipped.
- **X billing gotchas** — cache hits (`meta.cached`) still bill full price; `502`/`503` are never charged and are retried; `402` is exhaustion **only** when `error.code == "insufficient_credits"` (the provider also uses 402 for x402 USDC payment challenges, which is a different failure).
- **YouTube comments need a YouTube Data API v3 key** — fetched via the official `commentThreads` endpoint using `YOUTUBE_API_KEY` from `.env`. Set it up at Google Cloud Console (enable YouTube Data API v3, create an API key). Missing keys are skipped with a warning, never crash the pipeline.
- **YouTube topic discovery is ON by default** — the pipeline searches the topic via `search.list` (100 units/call), then pulls comments from each new video (`commentThreads`). Discovered videos are cached in the `youtube_videos` table (keyed by `video_id + topic_query`), so re-runs only fetch **new** videos' comments (`--yt-refresh` forces a re-fetch). Comments still land in `posts` under the uniform schema.
- **YouTube quota is ledger-tracked** — `collectors/youtube_collector.py` keeps spend in a gitignored `youtube_quota.json` (`{"date", "used"}`), resetting at UTC midnight. Runs pre-check against both the remaining daily quota (10,000 units) and a per-run cap (`--yt-budget-units`, default 2000, ≈5 videos/topic). A `403 quotaExceeded` aborts the remaining videos with a clear message instead of silently continuing. `search_videos` costs 100 units flat; `commentThreads` ≈ 1 + items.
- **Telegram session file** (`session_name.session`) is created on first run and gitignored. Deleted if you re-authenticate.
- **DB path is anchored** to the project root — `database/db.py` resolves `social.db` relative to the repo root, so the pipeline and dashboard share one DB no matter the current directory. All modules import from `database.db`.
- **Tests exist and never touch the real DB** — `python -m pytest` runs the suite in `tests/` (see `pytest.ini`). `tests/conftest.py` isolates each test in an SQLite file under `.test_tmp/` (kept on the D: drive), mocks the HF sentiment/emotion models, no-ops `load_dotenv()`, and scrubs real secret keys (`YOUTUBE_API_KEY`, `TG_API_ID`, `TG_API_HASH`, `LLM_API_KEY`, `SOCIALFETCH_API_KEY`) for the whole session so no collector can leak `.env` values mid-test. There is no linter or CI.
- **X discovery returns promoters, so relevance filtering is on by default** — a live "AI Agents" run returned three giveaway/token accounts (`gametyio`, `AAAPadSF`, `AiWhitebridge`) whose display names looked innocuous ("WhiteBridge: AI Agents Network") while ~48% of their tweets were giveaways, presales and partnership marketing. Two layers, both in `collectors/x_collector.py`:
  - **Pre-spend profile filter** (`filter_profiles`): drops profiles whose name/bio lack a topic term from the query (`topic_terms`, word-anchored so `ai` does not match `email`/`chain`) or carry promo markers. This runs *before* any timeline request, so a rejected handle costs **0 credits instead of 1** — the main reason filtering early is worth it.
  - **Per-tweet filter** (`is_promo_tweet` / `split_promo_posts`): drops giveaway/airdrop/presale/CTA posts. This is the layer that actually protects data quality, because a giveaway account's *profile card* is clean and only its *posts* reveal it. A profile with ≥`PROMO_TWEET_RATIO` (0.5) promo is dropped entirely, but still written to `x_profiles` so it is never re-billed.
  - Both are heuristics that can over-filter. `--x-no-require-topic` drops the topic requirement, `--x-allow-promo` disables promo filtering. Keyword lists are a proxy: a crypto project genuinely posting *about* AI agents is not reliably separable from a commentator, and this is a known residual gap.
- **Narrative report** is the final pipeline stage: it calls the Google Gemini API when `LLM_API_KEY` is set, otherwise it deterministically falls back to a template. Reports are stored in the `narratives` table, rendered in the dashboard, and written to `reports/<topic>_<timestamp>.md`.
- **Dashboard needs data first** — run the pipeline before launching `streamlit run app.py`, otherwise it shows empty state.

## Conventions

- All posts use a uniform dict schema: `id, platform, author_id, author_handle, text, raw_text, created_at, collected_at, parent_id, topic_query, reactions, shares, replies, views`
- `text` is the normalizer-cleaned version (mentions/URLs stripped); `raw_text` keeps the original (needed by network analysis for @mentions).
- Timestamps are ISO 8601 UTC strings.
- `INSERT OR IGNORE` for posts (idempotent), `INSERT OR REPLACE` for sentiments, plain `INSERT` for trends (accumulates). `youtube_videos` and `x_profiles` use `ON CONFLICT DO UPDATE` so `first_seen_at` survives re-discovery.
- The YouTube quota ledger (`youtube_quota.json`) is gitignored JSON keyed by UTC date; never read it into memory, only via `quota_remaining()` / `spend_quota()` in `collectors/youtube_collector.py`.
- The X credit ledger (`x_credits.json`) is gitignored lifetime-cumulative JSON; only reach it via `credits_spent()` / `spend_credits()` / `remaining_credits()` in `collectors/x_collector.py`, never cache it in module state.
- X `author_handle` is stored `@`-prefixed from the bare handle, never from `displayName` — `analytics/network.py` keys nodes on `author_handle` and matches `@mentions` from `raw_text`, so the bare handle is what lets mention edges resolve across platforms (X `<->` Telegram).
- **`parent_id` must carry the platform prefix** (`x_<id>`, `yt_<id>`, `<channel>_<msgid>`) so it equals the parent post's `id`. `analytics/network.py` resolves reply edges with `post_author[parent_id]`, so a raw unprefixed platform id silently yields **zero** reply edges and collapses the influence graph to mentions-only. Collectors should build it with `stable_post_id(platform, reply_to, "")` when the reply id is present, else `None`.
- X data runs through every analysis stage exactly like Telegram/YouTube — sentiment, emotion, demographics, trends, network, narrative. All of them are platform-agnostic (they read `id`/`text`/`author_handle`), so parity depends only on the collector filling the uniform schema. `tests/test_x_analysis.py` and `tests/test_x_pipeline_e2e.py` lock this in.
- Modules use lazy imports (imported inside functions) to avoid loading heavy deps (torch, transformers) unless needed.

## AI Agent Rules

### Secrets and sensitive files

NEVER read, display, print, modify, or expose the contents of:

- `.env`
- `*.session`
- API keys
- access tokens
- passwords
- authentication credentials

Do not include secrets in code, logs, terminal output, commits, or responses.

Use `.env.example` to understand required environment variables.

### Files and directories to avoid

Do not inspect or modify:

- `.venv/`
- `.git/`
- `*.session`
- `*.db`
- `*.db-shm`
- `*.db-wal`

unless explicitly required by the task.

### Modification policy

Before modifying code:

1. Read the relevant existing implementation.
2. Understand how it interacts with the rest of the pipeline.
3. Search for existing utilities and implementations.
4. Make the smallest reasonable change.
5. Do not rewrite unrelated code.
6. Do not introduce new dependencies unless necessary.

Preserve existing behavior unless the task explicitly requires changing it.

### Architecture boundaries

Keep these responsibilities separate:

- `collectors/` → external data collection
- `normalizer/` → cleaning and normalization
- `analytics/` → analysis and ML
- `database/` → persistence and database access
- `dashboard/` → presentation/UI

Do not move logic between these layers without a clear reason.

### Git safety

Do not:

- run `git push` without explicit permission
- delete branches
- rewrite Git history
- use destructive Git commands such as `git reset --hard`
- delete project files without confirmation

Before substantial changes, inspect the current Git state.

After changes, review the diff.

### Verification

Automated tests exist — run `python -m pytest`. The suite runs offline (HF models mocked) and never touches the real `social.db` (isolated DBs under `.test_tmp/`). There is no linter or CI.

After modifying code:

1. Run the affected module.
2. Run the relevant pipeline command if practical.
3. Check for Python import/syntax errors.
4. Run `python -m pytest`.
5. Review `git diff`.
6. Report what was changed and what was verified.

Do not claim a change is working unless it has been verified.