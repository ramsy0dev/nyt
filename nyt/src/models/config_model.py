from dataclasses import dataclass
from pathlib import Path

_ROOT = Path.home() / ".nyt"


@dataclass
class Config:
    # API server
    API_HOST: str = "localhost"
    API_PORT: int = 9473

    # Paths (all under ~/.nyt/)
    API_LOGS_FILE_PATH:      str = str(_ROOT / "nyt.log")
    CONFIG_FILE_PATH:        str = str(_ROOT / "nyt.toml")
    DATABASE_PATH:           str = str(_ROOT / "nyt.db")
    VIDEOS_PREFIX_DIRECTORY: str = str(_ROOT / "videos")
    AVATARS_DIRECTORY:       str = str(_ROOT / "avatars")
    ASSETS_PREFIX:           str = str(_ROOT / "assets")

    # Auth (empty string = auth disabled)
    ADMIN_USERNAME:      str = ""
    ADMIN_PASSWORD_HASH: str = ""
    ADMIN_SALT:          str = ""

    # Watcher
    WATCH_DELAY_MINUTES: int = 60
