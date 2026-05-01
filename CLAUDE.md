# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NYT (No YouTube)** is a self-hosted YouTube channel tracker and video downloader. It monitors tracked channels for new uploads, downloads them locally via yt-dlp, and serves them through a FastAPI REST API consumed by a Next.js web frontend.

## Commands

### Backend (Python / Poetry)

```bash
# Install dependencies
poetry install

# Run the CLI
nyt track --channel-handle "ChannelName"   # Track a YouTube channel
nyt remove --channel-handle "ChannelName"  # Stop tracking a channel
nyt watch --delay 30                       # Watch for new videos (delay in minutes)
nyt api --host localhost --port 9473       # Start the FastAPI server
nyt version
```

### Frontend (Node.js / npm)

```bash
cd nytweb
npm install
npm run dev      # Dev server at localhost:3000
npm run build
npm run lint     # next lint (ESLint)
```

### External requirement

FFmpeg must be installed separately (`winget install ffmpeg` on Windows).

## Architecture

The project has three distinct layers:

```
CLI / Watcher  →  FastAPI REST API  →  Next.js Frontend
                        ↓
                  SQLite Database (~/.nyt/nyt.db)
                  Local video files (~/.nyt/videos/)
```

### Backend (`nyt/`)

- **`nyt/cli.py`** — Typer CLI entry point (`nyt:cli.run`). Registers commands: `version`, `track`, `remove`, `watch`, `api`.
- **`nyt/src/nyt.py`** — Core business logic (`Nyt` class). Handles channel tracking (`add_channel`), the polling loop (`watch`), and video downloading (`download_video`) via yt-dlp with age-gate bypass.
- **`nyt/src/database/database_handler.py`** — SQLAlchemy ORM wrapper over SQLite. Three tables: `channels`, `videos`, `watched_videos`.
- **`nyt/src/api/api.py`** — FastAPI app. Routes live under `/api/v1/`. Channels CRUD in `nyt/src/api/channels/`, video streaming and listing in `nyt/src/api/videos/`. Video streaming uses HTTP range requests (7 MB chunks) to support seeking.
- **`nyt/src/config.py`** — Reads/writes `~/.nyt/nyt.toml`. On first run, the CLI creates this file, the database, and downloads logo assets.

### Frontend (`nytweb/`)

- **`nytweb/app/page.tsx`** — Home page; server-side fetch of all downloaded videos via `FetchVideos()`, renders a `VideoCard` grid.
- **`nytweb/app/watch/[video_id]/page.tsx`** — Video watch page (currently a stub).
- **`nytweb/app/services/videos.ts`** — API client. All calls target `http://localhost:9473/api/v1` (hardcoded in `nytweb/app/constant.ts`).
- Stack: Next.js 14, React 18, TypeScript 5, Tailwind CSS, Material-UI v5.

### Data flow

1. `nyt watch` polls tracked channels via pytube, downloads new videos with yt-dlp.
2. `nyt api` exposes downloaded videos over HTTP; the frontend fetches the list and streams video files directly from the API.

## Key details

- **Config file:** `~/.nyt/nyt.toml` (auto-generated on first run). API host/port defaults to `localhost:9473`; frontend API base URL must match.
- **No test suite** exists in the project.
- **No database migrations framework** — schema changes require manual SQLite work or dropping and recreating the DB.
- **Python version constraint:** `>=3.11,<3.12` (strict upper bound).
