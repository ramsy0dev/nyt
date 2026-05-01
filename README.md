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

**nyt** is a self-hosted YouTube channel tracker. It monitors the channels you care about, downloads new videos the moment they appear, and serves them through a clean web interface — no algorithm, no recommendations, no distractions. Just your subscriptions.

## Features

- **Track channels** from the web UI or the CLI
- **Auto-download** new uploads as they appear, or enable stream-only mode to save bandwidth and stream on demand
- **Built-in player** — no third-party embeds, videos served directly from your machine
- **Channel management UI** — search YouTube, add/remove channels, set per-channel check intervals
- **Admin authentication** — optional password protection for your instance
- **Desktop notifications** on new uploads (Linux, macOS, Windows)
- **No FFmpeg required** — downloads the best pre-merged format available
- Single binary-style install via pip — no Node.js, no Docker, no build step

## Requirements

- Python 3.11 or newer

## Install

```bash
pip install git+https://github.com/ramsy0dev/nyt.git
```

Add your API key to `~/.nyt/nyt.toml` after the first run (the file is created automatically):

```toml
# nyt.toml is generated on first launch — add your key here
```

> The API key goes in `nyt/constant.py` for now. A proper config field is on the roadmap.

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

`nyt serve` starts the web UI, the REST API, and the background watcher in one command:

```bash
nyt serve
```

Then open [http://localhost:9473](http://localhost:9473).

```bash
# Custom host / port / watcher interval
nyt serve --host 0.0.0.0 --port 8080 --delay 120
```

The watcher runs in a background thread and checks each channel on its own schedule. The default interval is **60 minutes** and can be overridden per channel from the web UI.

### Secure your instance

Set admin credentials before exposing nyt on a network:

```bash
nyt superuser --username admin --password yourpassword
```

Restart the server after running this. All pages will redirect to a login screen until authenticated. The session is cookie-based and lasts 30 days.

### Run the watcher standalone

If you only want the download loop without the web interface:

```bash
nyt watch --delay 60
```

## Web UI

| Page | Description |
|------|-------------|
| **/** | Video grid — sort by date or channel, filter unwatched, mark watched |
| **/watch/:id** | Video player — streams directly from your local library |
| **/channels** | Channel management — search YouTube, add/remove channels, set download mode and poll interval |
| **/login** | Auth page — only shown when a superuser is configured |

**Stream-only mode** — per channel, you can disable auto-download. New videos are listed in the grid but not stored locally. Clicking play streams the video from YouTube on demand through the nyt server. Toggle it from the Channels page.

## Storage

Everything lives under `~/.nyt/` (Linux / macOS) or `%UserProfile%\.nyt\` (Windows):

| Path | Contents |
|------|----------|
| `nyt.toml` | Configuration |
| `nyt.db` | SQLite database |
| `nyt.log` | Log file (rotating, 10 MB max) |
| `videos/` | Downloaded video files |
| `avatars/` | Cached channel avatar images |
| `assets/` | nyt logo assets |

## Configuration

`~/.nyt/nyt.toml` is created automatically on first run. Relevant fields:

```toml
[nyt]
videos_prefix_directory = "/home/user/.nyt/videos"

[nyt.api]
host = "localhost"
port = "9473"

[nyt.watcher]
watch_delay_minutes = 60

[nyt.auth]
admin_username      = ""
admin_password_hash = ""
admin_salt          = ""
```

Auth fields are managed by `nyt superuser` — edit them manually at your own risk.

## License

[GPL-3.0](LICENSE) — do whatever you want with it, just keep it open.
