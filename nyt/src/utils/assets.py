import os
import requests

from nyt import constant

# Models
from nyt.src.models.config_model import Config

paths = {
    Config.NYT_HIGH_RESOLUTION_LOGO : f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo.png",
    Config.NYT_HIGH_RESOLUTION_LOGO_WHITE: f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo-white.png",
    Config.NYT_HIGH_RESOLUTION_LOGO_BLACK: f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo-black.png",
    Config.NYT_HIGH_RESOLUTION_LOGO_TRANSPARENT: f"https://raw.githubusercontent.com/{constant.AUTHOR}/nyt/main/assets/nyt-high-resolution-logo-transparent.png"
}

def download_assets() -> None:
    """
    Downloads the nyt logos from the github repo.

    Args:
        None.
    
    Returns:
        None.
    """
    for path in paths:
        png_content = requests.get(paths[path]).content
        
        with open(path, "wb") as png:
            png.write(png_content)

def check_assets() -> bool:
    """
    Checks if the nyt's logos are downloaded.

    Args:
        None.
    
    Returns:
        bool: True if yes, otherwise False is returned.
    """
    for path in paths:
        if not os.path.exists(path):
            return False
    
    return True

def create_assets_prefix() -> None:
    """
    Creates the assets prefix directory.
    """
    if not os.path.exists(Config.ASSETS_PREFIX):
        os.mkdir(Config.ASSETS_PREFIX)
