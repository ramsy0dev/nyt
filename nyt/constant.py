import os
import sys

# Package info
PACKAGE = "nyt"
VERSION = "v0.1.2"
GITHUB = "https://github.com/ramsy0dev/nyt"
AUTHOR = "ramsy0dev"
LICENSE = "GPL-3.0"

# Platform
PLATFORM = sys.platform

if PLATFORM == "linux":
    HOME = os.getenv("HOME")
    PATH_DASH = "/"

if PLATFORM == "win32":
    HOME = os.getenv("UserProfile")
    PATH_DASH = "\\"

# nyt's root prefix path
ROOT_PREFIX = f"{HOME}{PATH_DASH}.nyt"

# API logs path
API_LOG_PATH = f"{ROOT_PREFIX}{PATH_DASH}nyt.log"

# Assets path
ASSETS_PREFIX = f"{ROOT_PREFIX}{PATH_DASH}assets"

NYT_HIGH_RESOLUTION_LOGO = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo.png"
NYT_HIGH_RESOLUTION_LOGO_BLACK = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo-black.png"
NYT_HIGH_RESOLUTION_LOGO_WHITE = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo-white.png"
NYT_HIGH_RESOLUTION_LOGO_TRANSPARENT = f"{ASSETS_PREFIX}{PATH_DASH}nyt-high-resolution-logo-transparent.png"

# SQLite Database path
DATABASE_PATH = f"{ROOT_PREFIX}{PATH_DASH}nyt.db"

# Videos path
VIDEOS_PREFIX_DIRECTORY = f"{ROOT_PREFIX}{PATH_DASH}videos"

# Response codes
CHANNEL_ALREADY_TRACKED = 1e0
CHANNEL_NOT_TRACKED = 1e1

# YouTube V3 api keys
_api_keys = [
    "AIzaSyDRVd48upuMgHohLPYlG3v363RfNJVzYmg"
]

# API
API_HOST = "localhost"
API_PORT = 8080

# Web App
WEBAPP_HOST = "localhost"
WEBAPP_PORT = 8645
