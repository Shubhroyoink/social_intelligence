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

X collector (via Nitter) requires no keys.
YouTube collector (via YouTube Data API v3) requires `YOUTUBE_API_KEY`.

The narrative report stage optionally uses Google Gemini:
- `LLM_API_KEY` — Google AI Studio key (https://aistudio.google.com/apikey). If absent, the pipeline falls back to a deterministic template report instead of an LLM call.
- `LLM_MODEL` — optional model override (default `gemini-3.5-flash`; `gemini-2.5-flash` is retired for new API users).

## Architecture

```
collectors/        Telegram (Telethon), X (Nitter) and YouTube (Data API v3) scrapers
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
- **Nitter is fragile** — X collection may silently return empty results if Nitter instances are down.
- **YouTube comments need a YouTube Data API v3 key** — fetched via the official `commentThreads` endpoint using `YOUTUBE_API_KEY` from `.env`. Set it up at Google Cloud Console (enable YouTube Data API v3, create an API key). Missing keys are skipped with a warning, never crash the pipeline.
- **YouTube topic discovery is ON by default** — the pipeline searches the topic via `search.list` (100 units/call), then pulls comments from each new video (`commentThreads`). Discovered videos are cached in the `youtube_videos` table (keyed by `video_id + topic_query`), so re-runs only fetch **new** videos' comments (`--yt-refresh` forces a re-fetch). Comments still land in `posts` under the uniform schema.
- **YouTube quota is ledger-tracked** — `collectors/youtube_collector.py` keeps spend in a gitignored `youtube_quota.json` (`{"date", "used"}`), resetting at UTC midnight. Runs pre-check against both the remaining daily quota (10,000 units) and a per-run cap (`--yt-budget-units`, default 2000, ≈5 videos/topic). A `403 quotaExceeded` aborts the remaining videos with a clear message instead of silently continuing. `search_videos` costs 100 units flat; `commentThreads` ≈ 1 + items.
- **Telegram session file** (`session_name.session`) is created on first run and gitignored. Deleted if you re-authenticate.
- **DB path is anchored** to the project root — `database/db.py` resolves `social.db` relative to the repo root, so the pipeline and dashboard share one DB no matter the current directory. All modules import from `database.db`.
- **Tests exist and never touch the real DB** — `python -m pytest` runs the suite in `tests/` (see `pytest.ini`). `tests/conftest.py` isolates each test in an SQLite file under `.test_tmp/` (kept on the D: drive), mocks the HF sentiment/emotion models, no-ops `load_dotenv()`, and scrubs real secret keys (`YOUTUBE_API_KEY`, `TG_API_ID`, `TG_API_HASH`, `LLM_API_KEY`) for the whole session so no collector can leak `.env` values mid-test. There is no linter or CI.
- **Narrative report** is the final pipeline stage: it calls the Google Gemini API when `LLM_API_KEY` is set, otherwise it deterministically falls back to a template. Reports are stored in the `narratives` table, rendered in the dashboard, and written to `reports/<topic>_<timestamp>.md`.
- **Dashboard needs data first** — run the pipeline before launching `streamlit run app.py`, otherwise it shows empty state.

## Conventions

- All posts use a uniform dict schema: `id, platform, author_id, author_handle, text, raw_text, created_at, collected_at, parent_id, topic_query, reactions, shares, replies, views`
- `text` is the normalizer-cleaned version (mentions/URLs stripped); `raw_text` keeps the original (needed by network analysis for @mentions).
- Timestamps are ISO 8601 UTC strings.
- `INSERT OR IGNORE` for posts (idempotent), `INSERT OR REPLACE` for sentiments, plain `INSERT` for trends (accumulates). `youtube_videos` uses `ON CONFLICT DO UPDATE` so `first_seen_at` survives re-discovery.
- The YouTube quota ledger (`youtube_quota.json`) is gitignored JSON keyed by UTC date; never read it into memory, only via `quota_remaining()` / `spend_quota()` in `collectors/youtube_collector.py`.
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