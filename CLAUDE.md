# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python automation tool that:
- Fetches articles from 30+ curated RSS feeds (tech, economics, geopolitics, Chinese finance)
- Uses the DeepSeek LLM to generate curated tech digests modeled on Andrej Karpathy's curation style
- Tracks 5 Chinese A-stock market indices and generates market summaries
- Delivers digests via Slack (`#tech-digest`) and Feishu (ByteDance's collaboration platform)

The entire logic lives in a single file: `rss_digest.py` (~270 lines).

## Running the Script

No build step. Install dependencies and run directly:

```bash
pip install feedparser requests akshare
python rss_digest.py
```

Python 3.11 is required (matches CI).

## Execution Modes

Controlled by the `MODE` environment variable:

| `MODE` | Behavior | CI Schedule (Beijing time) |
|---|---|---|
| `rss` (default) | Daily tech digest from RSS feeds | 09:00 daily |
| `astock_morning` | Chinese A-stock market open summary | 11:30 weekdays |
| `astock_afternoon` | Chinese A-stock market close summary | 15:00 weekdays |

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `DEEPSEEK_API_KEY` | Yes | Required for all modes |
| `SLACK_TOKEN` | No | Delivery skipped if empty |
| `FEISHU_APP_SECRET` | No | Delivery skipped if empty |
| `FEISHU_APP_ID` | No | Falls back to hardcoded default |
| `FEISHU_USER_ID` | No | Falls back to hardcoded default |

## Architecture

`rss_digest.py` has four functional areas:

**1. Feed Collection & Deduplication**
- `FEEDS`: list of 30+ RSS feed URLs
- `get_recent_articles(hours=24)`: fetches articles published within the last 24 hours, skipping URLs already seen
- `load_seen_urls()` / `save_seen_urls()`: persist a URL→timestamp dict in `seen_urls.json` with a 7-day sliding window

**2. Deduplication State (`seen_urls.json`)**
- Tracks every processed URL with an ISO 8601 timestamp
- Entries older than 7 days are pruned on each run
- The CI workflow auto-commits this file back to the repo after every run — do not delete it manually

**3. AI Digest Generation**
- `generate_digest(articles)`: calls the DeepSeek API with a role prompt instructing the model to curate like Andrej Karpathy — "信噪比优先" (signal-to-noise first), in Chinese, ~600 words
- `generate_astock_digest()`: one-liner market analysis for the A-stock summary modes

**4. Delivery**
- `send_to_slack()`: posts formatted digest to `#tech-digest` via Slack Web API
- `send_to_feishu()`: fetches a Feishu tenant access token, then sends a DM to the configured user

## CI/CD

Three scheduled GitHub Actions jobs in `.github/workflows/daily.yml`:

- `rss-digest`: runs `MODE=rss` daily
- `astock-morning`: runs `MODE=astock_morning` on weekdays
- `astock-afternoon`: runs `MODE=astock_afternoon` on weekdays

All three jobs install dependencies, run `rss_digest.py`, then `git commit && git push` any changes to `seen_urls.json`. Credentials are stored as GitHub Actions secrets.

## Conventions

- Chinese comments and UI strings throughout the codebase — this is intentional, not a mistake.
- No test suite exists. Validate changes by running the script with real or stubbed environment variables.
- Credentials are never stored in code; always use environment variables or GitHub Actions secrets.
