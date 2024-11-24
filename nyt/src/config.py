import os
import tomllib

from pathlib import Path

from nyt import constant

# Models
from nyt.src.models.config_model import Config

class ConfigManager:
    """
    Config manager for nyt and nytweb
    """
    def __init__(self) -> None:
        pass

    def load_config(self) -> Config:
        """
        Loads the config file content.
        
        Args:
            None.

        Returns:
            Config: The config model containing the configuration.
        """
        config = Config()
        
        if not self.is_config_dir_exists():
            os.mkdir(constant.ROOT_PREFIX)

        if constant.CONFIG_FILE_PATH.split(constant.PATH_DASH)[-1] not in os.listdir(constant.ROOT_PREFIX):
            self.write_config()

        with open(Config.CONFIG_FILE_PATH, "rb") as f:
            config_content = tomllib.load(f)

        config.API_HOST = config_content["nyt"]["api"]["host"]
        config.API_PORT = config_content["nyt"]["api"]["port"]
        config.DATABASE_PATH = config_content["nyt"]["api"]["database_path"] 

        config.VIDEOS_PREFIX_DIRECTORY = config_content["nyt"]["videos_prefix_directory"]

        config.WEBAPP_HOST = config_content["nyt"]["webapp"]["host"]
        config.WEBAPP_PORT = config_content["nyt"]["webapp"]["port"]

        return config

    def write_config(self, costum_config: str | None = None) -> None:
        """
        Writes the configuration to the config file.
        
        Args:
            costum_config (str, default: None, optional): A costum configuration to write to the config file.

        Returns:
            None.
        """
        config = costum_config if costum_config is not None else self.generate_config()
        
        with open(Config.CONFIG_FILE_PATH, "w") as f:
            f.write(config)

    def generate_config(self) -> str:
        """
        Generates a config content.

        Args:
            None.

        Returns:
            str: The generated config content.
        """
        default_config = Config()

        config = f"""[nyt]
videos_prefix_directory = "{default_config.VIDEOS_PREFIX_DIRECTORY}"
logs_file_path = "{default_config.API_LOGS_FILE_PATH}"

[nyt.api]
host = "{default_config.API_HOST}"
port = "{default_config.API_PORT}"
database_path = "{default_config.DATABASE_PATH}"

[nyt.webapp]
host = "{default_config.WEBAPP_HOST}"
port = "{default_config.WEBAPP_PORT}"

[nyt.assets]
nyt_high_resolution_logo = "{default_config.NYT_HIGH_RESOLUTION_LOGO}"
nyt_high_resolution_logo_black = "{default_config.NYT_HIGH_RESOLUTION_LOGO_BLACK}"
nyt_high_resolution_logo_white = "{default_config.NYT_HIGH_RESOLUTION_LOGO_BLACK}"
nyt_high_resolution_transparent = "{default_config.NYT_HIGH_RESOLUTION_LOGO_BLACK}"
"""
        return config
    
    def is_config_dir_exists(self) -> bool:
        """
        Check if the config directory exists or not.

        Args:
            None.

        Returns:
            bool: True if it exists, otherwise False.
        """
        
        return Path(constant.ROOT_PREFIX).exists()

