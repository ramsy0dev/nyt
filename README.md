<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="nyt/static/logo.svg">
  <img src="nyt/static/logo-dark.png" alt="nyt" width="260">
</picture>

<br><br>

**No YouTube.** Track channels, download videos locally, watch on your own terms.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/license-GPL--3.0-coral?style=flat-square)](LICENSE)

</div>

---

**nyt** is a self-hosted YouTube channel tracker. It monitors the channels you care about, downloads new uploads the moment they appear, and serves them through a clean web interface — no algorithm, no recommendations, no distractions. Just your subscriptions.

## Features

**Watching**
- Responsive video grid with sort (by date or channel) and filter (all / unwatched)
- Native HTML5 player — streams video files directly from your machine via HTTP range requests
- **Creator subtitles** — VTT subtitle tracks downloaded alongside each video and loaded natively in the player with a language selector
- **Chapter bar** — interactive timeline below the player; click any segment to jump to that chapter, with the active chapter highlighted in real time
- Resume playback — the player remembers your position and offers to pick up where you left off
- Mark watched automatically on play, or manually from the grid

**Downloading**
- Auto-download new uploads from tracked channels, or enable **stream-only mode** per channel to list videos without storing them locally
- **Quality variants** via FFmpeg — transcode downloads to 720p, 480p, and 360p in the background; switch quality mid-playback from the player
- **Storage cap** — set a maximum GB limit; nyt tracks disk usage and displays a live usage meter in settings
- **Auto-delete** watched videos after a configurable number of days to reclaim space
- Download progress and transcoding progress streamed to the web UI in real time via SSE
- Desktop notifications on new uploads (Linux, macOS, Windows)

**Channel management**
- Search YouTube by handle and preview channel info (avatar, subscriber count, description) before tracking
- Per-channel **custom poll interval** — override the global watcher delay on a channel-by-channel basis
- Per-channel stream-only toggle

**Server**
- Single command (`nyt serve`) starts the web UI, REST API, and background watcher together
- Background watcher runs as a daemon thread — each channel is checked on its own schedule, skipped if not yet due
- **JWT authentication** — optional password protection using HS256 tokens; sessions last 30 days with automatic refresh on every page load, invalidated on logout or credential change
- Rotating log file (10 MB, 3 backups)

## Requirements

- Python 3.11 or newer
- FFmpeg (optional — only needed for quality variant transcoding)

## Docker

**Requirements:** Docker and Docker Compose (included with Docker Desktop).

### 1. Clone the repo

```bash
git clone https://github.com/ramsy0dev/nyt.git
cd nyt
```

### 2. Build and start

```bash
docker compose up -d
```

This builds the image, starts the container, and runs the watcher in the background. Everything — config, database, videos, avatars — is stored in a named Docker volume and persists across restarts and rebuilds.

### 3. Open the web UI

```
http://localhost:9473
```

### 4. Track your first channel

```bash
docker compose exec nyt nyt track --channel-handle LinusTechTips
```

The watcher picks up new uploads automatically every 60 minutes. Downloaded videos appear in the grid immediately.

### 5. Secure your instance (optional)

Set credentials before exposing nyt on a network:

```bash
docker compose exec nyt nyt superuser --username admin --password yourpassword
docker compose restart nyt
```

All pages will require login. To remove the password later:

```bash
docker compose exec nyt nyt superuser --disable
docker compose restart nyt
```

---

### Configuration

**Change the watcher interval** — edit `docker-compose.yml` and add a `command` override:

```yaml
services:
  nyt:
    command: ["nyt", "serve", "--host", "0.0.0.0", "--delay", "120"]
```

**Expose on a different port:**

```yaml
services:
  nyt:
    ports:
      - "8080:9473"
```

**Use a bind mount** instead of a named volume (easier to browse downloaded files directly):

```yaml
services:
  nyt:
    volumes:
      - ./data:/root/.nyt
```

After changing `docker-compose.yml`, run `docker compose up -d` to apply.

## Install (without Docker)

```bash
pip install git+https://github.com/ramsy0dev/nyt.git
```

The config file, database, and directory structure under `~/.nyt/` are created automatically on first run.

## Usage

### Track a channel

```bash
nyt track --channel-handle LinusTechTips
```

Do not include the `@`. To stop tracking:

```bash
nyt remove --channel-handle LinusTechTips
```

### Start the server

```bash
nyt serve
```

Opens the web UI + REST API + background watcher at [http://localhost:9473](http://localhost:9473).

```bash
# Custom host / port / global watcher interval
nyt serve --host 0.0.0.0 --port 8080 --delay 120
```

### Run the watcher standalone

Download-only mode, no web interface:

```bash
nyt watch --delay 60
```

### Secure your instance

Set admin credentials before exposing nyt on a network:

```bash
nyt superuser --username admin --password yourpassword
```

Restart the server. All pages will redirect to a login screen until authenticated. To remove authentication:

```bash
nyt superuser --disable
# prompts for current credentials before clearing them
```

## Web UI

| Page | Path | Description |
|------|------|-------------|
| Home | `/` | Video grid — sort, filter, mark watched |
| Player | `/watch/:id` | Native player with subtitle tracks and chapter bar |
| Channels | `/channels` | Search YouTube, add/remove channels, configure poll intervals and download mode |
| Settings | `/settings` | Watcher interval, storage limit + usage meter, transcoding toggle, auth management |
| Login | `/login` | Only shown when a superuser is configured |

## Storage

Everything lives under `~/.nyt/` (Linux / macOS) or `%UserProfile%\.nyt\` (Windows):

| Path | Contents |
|------|----------|
| `nyt.toml` | Configuration |
| `nyt.db` | SQLite database |
| `nyt.log` | Log file (rotating, 10 MB max) |
| `videos/` | Downloaded video files and subtitle VTTs |
| `avatars/` | Cached channel avatar images |
| `assets/` | nyt logo assets |

## Configuration

`~/.nyt/nyt.toml` is generated automatically. Key fields:

```toml
[nyt]
videos_prefix_directory = "/home/user/.nyt/videos"

[nyt.api]
host = "localhost"
port = "9473"

[nyt.watcher]
watch_delay_minutes = 60   # global default; overridable per channel from the UI

[nyt.player]
transcoding_enabled = false  # set true to generate 720p/480p/360p variants via FFmpeg

[nyt.storage]
storage_limit_gb = 0.0       # 0 = unlimited
auto_delete_watched_days = 0 # 0 = disabled; deletes watched video files after N days

[nyt.auth]
admin_username      = ""   # empty = auth disabled; managed via `nyt superuser`
admin_password_hash = ""
admin_salt          = ""
```

Auth fields are managed by `nyt superuser` — do not edit them manually.

## License

[GPL-3.0](LICENSE) — do whatever you want with it, just keep it open.
