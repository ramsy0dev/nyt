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

# The root prefix
ROOT_PREFIX: str = f"{HOME}{PATH_DASH}.nyt"

# Config file PATH_DASH
CONFIG_FILE_PATH = f"{ROOT_PREFIX}{PATH_DASH}nyt.toml"

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
