import os
import sys

# Package info
PACKAGE = "nyt"
VERSION = "v0.1.2"
GITHUB = "https://github.com/ramsy0dev/nyt"
AUTHOR = "ramsy0dev"
LICENSE = "MIT"

# Log levels
INFO = "[[green]INFO[white]][reset]"
DEBUG = "[[blue]DEBUG[white]][reset]"
ERROR = "[[blue]ERROR[white]][reset]"

# Assets
NYT_HIGH_RESOLUTION_LOGO = "assets/nyt-high-resolution-logo.png"
NYT_HIGH_RESOLUTION_LOGO_BLACK = "assets/nyt-high-resolution-logo-black.png"
NYT_HIGH_RESOLUTION_LOGO_WHITE = "assets/nyt-high-resolution-logo-white.png"
NYT_HIGH_RESOLUTION_LOGO_TRANSPARENT = "assets/nyt-high-resolution-logo-transparent.png"

# Constants
PLATFORM = sys.platform 
if PLATFORM == "linux":
    HOME = os.getenv("HOME")
if PLATFORM == "win32":
    HOME = os.getenv("UserProfile")

DATABASE_PATH = f"{HOME}/.nyt/nyt.db"
VIDEOS_PREFIX_DIRECTORY = f"{HOME}/.nyt/videos"

# Response codes
CHANNEL_ALREADY_TRACKED = 1e0
CHANNEL_NOT_TRACKED = 1e1
