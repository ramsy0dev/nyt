import tomllib
from pathlib import Path

from nyt.src.models.config_model import Config


class ConfigManager:
    def load_config(self) -> Config:
        cfg = Config()
        path = Path(cfg.CONFIG_FILE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            path.write_text(self._to_toml(cfg))

        with open(path, "rb") as f:
            data = tomllib.load(f)

        nyt = data.get("nyt", {})
        api = nyt.get("api", {})
        cfg.API_HOST               = api.get("host",          cfg.API_HOST)
        cfg.API_PORT               = int(api.get("port",      cfg.API_PORT))
        cfg.DATABASE_PATH          = api.get("database_path", cfg.DATABASE_PATH)
        cfg.VIDEOS_PREFIX_DIRECTORY = nyt.get("videos_prefix_directory", cfg.VIDEOS_PREFIX_DIRECTORY)

        auth = nyt.get("auth", {})
        cfg.ADMIN_USERNAME      = auth.get("admin_username",      "")
        cfg.ADMIN_PASSWORD_HASH = auth.get("admin_password_hash", "")
        cfg.ADMIN_SALT          = auth.get("admin_salt",          "")

        cfg.WATCH_DELAY_MINUTES = int(nyt.get("watcher", {}).get("watch_delay_minutes", cfg.WATCH_DELAY_MINUTES))

        player = nyt.get("player", {})
        cfg.QUALITY_SELECTION_ENABLED = bool(player.get("quality_selection_enabled", cfg.QUALITY_SELECTION_ENABLED))
        cfg.TRANSCODING_ENABLED       = bool(player.get("transcoding_enabled",       cfg.TRANSCODING_ENABLED))

        storage = nyt.get("storage", {})
        cfg.STORAGE_LIMIT_GB = float(storage.get("limit_gb", cfg.STORAGE_LIMIT_GB))

        cleanup = nyt.get("cleanup", {})
        cfg.AUTO_DELETE_WATCHED_DAYS = int(cleanup.get("auto_delete_watched_days", cfg.AUTO_DELETE_WATCHED_DAYS))

        updates = nyt.get("updates", {})
        cfg.AUTO_UPDATE_ENABLED = bool(updates.get("auto_update_enabled", cfg.AUTO_UPDATE_ENABLED))

        return cfg

    def save_auth(self, username: str, password_hash: str, salt: str) -> None:
        cfg = self.load_config()
        cfg.ADMIN_USERNAME      = username
        cfg.ADMIN_PASSWORD_HASH = password_hash
        cfg.ADMIN_SALT          = salt
        Path(cfg.CONFIG_FILE_PATH).write_text(self._to_toml(cfg))

    def save_settings(
        self,
        watch_delay_minutes: int | None = None,
        videos_directory: str | None = None,
        storage_limit_gb: float | None = None,
        quality_selection_enabled: bool | None = None,
        transcoding_enabled: bool | None = None,
        auto_delete_watched_days: int | None = None,
        auto_update_enabled: bool | None = None,
    ) -> None:
        cfg = self.load_config()
        if watch_delay_minutes is not None:
            cfg.WATCH_DELAY_MINUTES = watch_delay_minutes
        if videos_directory is not None:
            cfg.VIDEOS_PREFIX_DIRECTORY = videos_directory
        if storage_limit_gb is not None:
            cfg.STORAGE_LIMIT_GB = storage_limit_gb
        if quality_selection_enabled is not None:
            cfg.QUALITY_SELECTION_ENABLED = quality_selection_enabled
        if transcoding_enabled is not None:
            cfg.TRANSCODING_ENABLED = transcoding_enabled
        if auto_delete_watched_days is not None:
            cfg.AUTO_DELETE_WATCHED_DAYS = auto_delete_watched_days
        if auto_update_enabled is not None:
            cfg.AUTO_UPDATE_ENABLED = auto_update_enabled
        Path(cfg.CONFIG_FILE_PATH).write_text(self._to_toml(cfg))

    @staticmethod
    def _qs(s: str) -> str:
        """Encode a string as a TOML double-quoted string, escaping backslashes and double-quotes."""
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

    def _to_toml(self, c: Config) -> str:
        q = self._qs
        return (
            f'[nyt]\n'
            f'videos_prefix_directory = {q(c.VIDEOS_PREFIX_DIRECTORY)}\n'
            f'logs_file_path = {q(c.API_LOGS_FILE_PATH)}\n'
            f'\n'
            f'[nyt.api]\n'
            f'host = {q(c.API_HOST)}\n'
            f'port = {q(str(c.API_PORT))}\n'
            f'database_path = {q(c.DATABASE_PATH)}\n'
            f'\n'
            f'[nyt.auth]\n'
            f'admin_username      = {q(c.ADMIN_USERNAME)}\n'
            f'admin_password_hash = {q(c.ADMIN_PASSWORD_HASH)}\n'
            f'admin_salt          = {q(c.ADMIN_SALT)}\n'
            f'\n'
            f'[nyt.watcher]\n'
            f'watch_delay_minutes = {c.WATCH_DELAY_MINUTES}\n'
            f'\n'
            f'[nyt.storage]\n'
            f'limit_gb = {c.STORAGE_LIMIT_GB}\n'
            f'\n'
            f'[nyt.player]\n'
            f'quality_selection_enabled = {"true" if c.QUALITY_SELECTION_ENABLED else "false"}\n'
            f'transcoding_enabled = {"true" if c.TRANSCODING_ENABLED else "false"}\n'
            f'\n'
            f'[nyt.cleanup]\n'
            f'auto_delete_watched_days = {c.AUTO_DELETE_WATCHED_DAYS}\n'
            f'\n'
            f'[nyt.updates]\n'
            f'auto_update_enabled = {"true" if c.AUTO_UPDATE_ENABLED else "false"}\n'
        )
