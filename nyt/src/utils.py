import re
import sys
import uuid
import subprocess
import requests as _requests

from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from nyt import constant


# ── Date ──────────────────────────────────────────────────────────────────────

def date_in_gmt() -> datetime:
    return datetime.now(timezone.utc)


# ── UID ───────────────────────────────────────────────────────────────────────

def generate_uid() -> str:
    return uuid.uuid4().hex


# ── Range header ──────────────────────────────────────────────────────────────

def parse_range_header(header_value: str) -> tuple[int, int | None]:
    match = re.match(r"bytes=(\d+)-(\d*)", header_value)
    if match:
        start = int(match.group(1))
        end   = int(match.group(2)) if match.group(2) else None
        return start, end
    return 0, None


# ── Desktop notifications ─────────────────────────────────────────────────────

def send_notification(app_name: str, summary_text: str, message: str, icon_path: str = "") -> None:
    try:
        if sys.platform == "win32":
            _notify_windows(summary_text, message)
        elif sys.platform == "darwin":
            _notify_macos(summary_text, message)
        else:
            _notify_linux(app_name, summary_text, message, icon_path)
    except Exception as exc:
        logger.warning(f"Desktop notification failed: {exc}")


def _notify_linux(app_name: str, title: str, message: str, icon_path: str) -> None:
    cmd = ["notify-send", "--app-name", app_name, title, message]
    if icon_path:
        cmd += ["--icon", icon_path]
    subprocess.run(cmd, check=True)


def _notify_macos(title: str, message: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
        check=True,
    )


def _notify_windows(title: str, message: str) -> None:
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$n = New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon = [System.Drawing.SystemIcons]::Information;"
        f'$n.BalloonTipTitle = "{title}";'
        f'$n.BalloonTipText = "{message}";'
        "$n.Visible = $true;"
        "$n.ShowBalloonTip(4000);"
        "Start-Sleep -Milliseconds 4500;"
        "$n.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


# ── Assets ────────────────────────────────────────────────────────────────────

_ASSET_URLS: dict[str, str] = {
    "nyt-high-resolution-logo.png": (
        f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo.png"
    ),
    "nyt-high-resolution-logo-white.png": (
        f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo-white.png"
    ),
    "nyt-high-resolution-logo-black.png": (
        f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo-black.png"
    ),
    "nyt-high-resolution-logo-transparent.png": (
        f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo-transparent.png"
    ),
}


def _assets_dir() -> Path:
    from nyt.src.config import ConfigManager  # late import — avoids circular dependency
    return Path(ConfigManager().load_config().ASSETS_PREFIX)


def check_assets() -> bool:
    d = _assets_dir()
    return all((d / name).exists() for name in _ASSET_URLS)


def download_assets() -> None:
    d = _assets_dir()
    d.mkdir(parents=True, exist_ok=True)
    for name, url in _ASSET_URLS.items():
        (d / name).write_bytes(_requests.get(url, timeout=30).content)


def create_assets_prefix() -> None:
    _assets_dir().mkdir(parents=True, exist_ok=True)
