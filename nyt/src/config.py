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

        return cfg

    def save_auth(self, username: str, password_hash: str, salt: str) -> None:
        cfg = self.load_config()
        cfg.ADMIN_USERNAME      = username
        cfg.ADMIN_PASSWORD_HASH = password_hash
        cfg.ADMIN_SALT          = salt
        Path(cfg.CONFIG_FILE_PATH).write_text(self._to_toml(cfg))

    def save_settings(self, watch_delay_minutes: int | None = None, videos_directory: str | None = None) -> None:
        cfg = self.load_config()
        if watch_delay_minutes is not None:
            cfg.WATCH_DELAY_MINUTES = watch_delay_minutes
        if videos_directory is not None:
            cfg.VIDEOS_PREFIX_DIRECTORY = videos_directory
        Path(cfg.CONFIG_FILE_PATH).write_text(self._to_toml(cfg))

    @staticmethod
    def _to_toml(c: Config) -> str:
        return (
            f'[nyt]\n'
            f'videos_prefix_directory = "{c.VIDEOS_PREFIX_DIRECTORY}"\n'
            f'logs_file_path = "{c.API_LOGS_FILE_PATH}"\n'
            f'\n'
            f'[nyt.api]\n'
            f'host = "{c.API_HOST}"\n'
            f'port = "{c.API_PORT}"\n'
            f'database_path = "{c.DATABASE_PATH}"\n'
            f'\n'
            f'[nyt.auth]\n'
            f'admin_username      = "{c.ADMIN_USERNAME}"\n'
            f'admin_password_hash = "{c.ADMIN_PASSWORD_HASH}"\n'
            f'admin_salt          = "{c.ADMIN_SALT}"\n'
            f'\n'
            f'[nyt.watcher]\n'
            f'watch_delay_minutes = {c.WATCH_DELAY_MINUTES}\n'
        )
