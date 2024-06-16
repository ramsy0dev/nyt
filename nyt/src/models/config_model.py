from nyt.constant import (
    HOME,
    PATH_DASH
)

class Config:
    """
    Config model
    """
    # The root path
    ROOT_PREFIX: str = f"{HOME}{PATH_DASH}.nyt"
    
    # API
    API_HOST: str = "localhost"
    API_PORT: int = 9473
    API_LOGS_FILE_PATH: str = f"{ROOT_PREFIX}{PATH_DASH}nyt.log"

    # WEBAPP
    WEBAPP_HOST: str = "localhost"
    WEBAPP_PORT: int = 8080 # NOTE: This is the default port used by Django therefor it can't changed from here.
    
    # The config file path
    CONFIG_FILE_PATH: str = f"{ROOT_PREFIX}{PATH_DASH}nyt.toml"
    
    # Assets path
    ASSETS_PREFIX: str = f"{ROOT_PREFIX}{PATH_DASH}assets"

    NYT_HIGH_RESOLUTION_LOGO: str = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo.png"
    NYT_HIGH_RESOLUTION_LOGO_BLACK: str = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo-black.png"
    NYT_HIGH_RESOLUTION_LOGO_WHITE: str = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo-white.png"
    NYT_HIGH_RESOLUTION_LOGO_TRANSPARENT: str = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo-transparent.png"

    # SQLite Database path
    DATABASE_PATH: str = f"{ROOT_PREFIX}{PATH_DASH}nyt.db"

    # Videos path
    VIDEOS_PREFIX_DIRECTORY: str = f"{ROOT_PREFIX}{PATH_DASH}videos"

