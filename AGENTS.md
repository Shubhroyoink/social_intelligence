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

# Skip optional analysis stages
python run_pipeline.py --skip-emotions --skip-demographics --skip-network
```

## Running the dashboard

```bash
cd dashboard
streamlit run app.py
```

## Environment variables

Telegram collector requires `.env` file with:
- `TG_API_ID` — from https://my.telegram.org
- `TG_API_HASH` — from https://my.telegram.org

X collector (via Nitter) requires no keys.
YouTube collector (via yt-dlp) requires no keys.

## Architecture

```
collectors/        Telegram (Telethon), X (Nitter) and YouTube (yt-dlp) scrapers
normalizer/        Text cleaning, dedup, tokenization
analytics/         Sentiment + emotion (HuggingFace transformers), demographics,
                   trend detection (TF-IDF), network analysis (NetworkX)
database/          SQLite schema and CRUD (social.db)
dashboard/         Streamlit UI
run_pipeline.py    CLI entrypoint wiring the stages together
```

## Key quirks

- **Sentiment model downloads on first run** (`cardiffnlp/twitter-roberta-base-sentiment-latest`). Slow startup until cached.
- **Emotion model downloads on first run** (`j-hartmann/emotion-english-distilroberta-base`). Same slow-first-run caveat.
- **Text truncated to 512 tokens** before model analysis (transformer limit).
- **Nitter is fragile** — X collection may silently return empty results if Nitter instances are down.
- **YouTube comments need a JS runtime** — as of 2026 YouTube requires solving a JS challenge to fetch comments. Install deno (`irm https://deno.land/install.ps1 | iex`) and have it on PATH; otherwise the collector warns and returns empty. yt-dlp must be recent enough to use it.
- **Telegram session file** (`session_name.session`) is created on first run and gitignored. Deleted if you re-authenticate.
- **DB path is hardcoded** as `social.db` in `database/db.py:5`. All modules import from `database.db`.
- **No tests, no linter, no CI** — no commands to run for verification.
- **Dashboard needs data first** — run the pipeline before launching `streamlit run app.py`, otherwise it shows empty state.

## Conventions

- All posts use a uniform dict schema: `id, platform, author_id, author_handle, text, created_at, collected_at, parent_id, topic_query, reactions, shares, replies, views`
- Timestamps are ISO 8601 UTC strings.
- `INSERT OR IGNORE` for posts (idempotent), `INSERT OR REPLACE` for sentiments, plain `INSERT` for trends (accumulates).
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

There are currently no automated tests or CI.

After modifying code:

1. Run the affected module.
2. Run the relevant pipeline command if practical.
3. Check for Python import/syntax errors.
4. Review `git diff`.
5. Report what was changed and what was verified.

Do not claim a change is working unless it has been verified.