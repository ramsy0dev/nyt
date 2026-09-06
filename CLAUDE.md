# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**nyt** is a self-hosted YouTube channel tracker: it polls tracked channels via `yt-dlp`, downloads new uploads, and serves them through a FastAPI backend + vanilla HTML/JS frontend. Single-binary CLI (`nyt`) that starts the API, web UI, and a background watcher thread together.

## Commands

```bash
# Install deps (Poetry-managed)
poetry install

# Run the CLI locally during development
poetry run nyt serve                      # API + web UI + watcher on :9473
poetry run nyt serve --host 0.0.0.0 --port 8080 --delay 120
poetry run nyt watch --delay 60           # watcher only, no web UI
poetry run nyt track --channel-handle <handle>    # handle without @
poetry run nyt remove --channel-handle <handle>
poetry run nyt superuser --username admin --password <pw>   # enable auth
poetry run nyt superuser --disable        # disable auth (prompts to confirm)

# Docker
docker compose up -d
docker compose exec nyt nyt track --channel-handle <handle>

# Type checking (pyrightconfig.json present)
poetry run pyright
```

There is no test suite and no lint config in this repo — don't invent test/lint commands.

## Architecture

**Entry point:** `nyt/cli.py` (`nyt = "nyt:cli.run"` in `pyproject.toml`) parses argv and dispatches to `cmd_*` functions. `cmd_serve` starts the FastAPI app (`nyt/src/api/api.py`) via uvicorn and spawns the watcher as a daemon thread (`_watcher_loop`) — the watcher polls every 60s internally but only actually checks a given channel when its own per-channel or global delay has elapsed (timing lives inside `NYT.watch()`, not in the loop).

**Core domain logic — `nyt/src/nyt.py` (`NYT` class):** all yt-dlp interaction (channel search/lookup, listing a channel's videos, downloading, fetching metadata) and the download/notify/transcode pipeline live here. `watch()` is the heart of the polling cycle: for each tracked channel it diffs the channel's current video list against `video_starting_point_id` (the last-seen video), downloads/lists whatever is new, and advances the starting point. Video downloads and FFmpeg transcodes (`_transcode_video`) run in background threads and report progress via `nyt/src/api/download_state.py` (in-memory dict polled over SSE at `/downloads/progress`).

**API layer — `nyt/src/api/`:**
- `api.py` — the single FastAPI app: frontend HTML routes (serve static files, gated by a cookie-based auth redirect), the REST API under `ROOT_API_ROUTE` (`nyt/src/api/constant.py`), and video streaming (HTTP range requests via `parse_range_header` in `nyt/src/utils.py`).
- `classes.py` — a `Classes` singleton (`classes = Classes()`) instantiated at import time, holding one shared `NYT`, `DatabaseHandler`, `TrackedChannels`, and `VideosHandler`. Route handlers reach domain logic through this singleton rather than constructing their own instances.
- `channels/tracked_channels.py`, `videos/videos.py` — thin per-domain wrappers over `NYT`/`DatabaseHandler` used by the API routes.
- `auth/auth.py` — hand-rolled HS256 JWT (`AuthManager`), no external JWT library. The signing secret is derived from `ADMIN_SALT + ADMIN_PASSWORD_HASH`, so it changes whenever credentials change (implicitly invalidating old sessions). `require_auth` is a FastAPI dependency added per-route; `is_auth_enabled()` is a no-op passthrough when no admin username is configured — auth is entirely opt-in.
- `watcher_state.py`, `download_state.py` — small in-memory state objects read by status/SSE endpoints; not persisted.

**Database — `nyt/src/database/`:** raw `sqlite3` (no ORM), single `DatabaseHandler` class in `database_handler.py`. Schema is defined as a `CREATE TABLE IF NOT EXISTS` string plus a **linear, append-only list of migrations** (`_MIGRATIONS`) applied via `PRAGMA user_version`. When changing the schema: add a new `(version, sql)` tuple to the end of `_MIGRATIONS` in `database_handler.py` — never edit an existing entry or renumber. JSON-shaped columns (`variants`, `subtitles`, `chapters`, `watched_videos`) are stored as TEXT and (de)serialized in the row-converter helpers (`_to_channel`, `_to_video`, `_to_watched`, `_json_col`). Row objects (`Channels`, `Videos`, `WatchedVideos` in `nyt/src/database/tables/`) are plain dataclasses, not SQLAlchemy models, despite living under `database/tables/`.

**Config — `nyt/src/config.py` + `nyt/src/models/config_model.py`:** `Config` is a dataclass of defaults; `ConfigManager.load_config()` reads/creates `~/.nyt/nyt.toml` (TOML written by hand via `_to_toml`, not a serialization library) and overlays it onto the defaults. All persistent state — config, DB, logs, videos, avatars — lives under `~/.nyt/` (`%UserProfile%\.nyt\` on Windows). Settings/auth are mutated through `ConfigManager.save_settings()` / `save_auth()`, which rewrite the whole TOML file — there's no partial-write path.

**Frontend — `nyt/static/`:** plain HTML/CSS/JS (no bundler, no framework), one HTML file per page (`index.html`, `watch.html`, `channels.html`, `settings.html`, `login.html`), served directly as `FileResponse` from the FastAPI routes in `api.py`. Auth gating for HTML pages happens server-side per-route (`_auth_redirect`) by checking the `nyt_session` cookie before returning the file.

**Watch/download cycle data flow:** `channels.video_starting_point_id` is the pointer used to detect "new" videos on each poll — it's critical to how `watch()` decides what's new, and gets advanced only after new videos are processed for that channel. `channels.watched_videos_uid` links each channel to a row in `watched_videos`, which tracks which video IDs have been marked watched independently of the `videos.is_watched` flag used by the UI grid.
