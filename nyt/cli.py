import sys
import time
import typer
import uvicorn
import logging

from rich import console
from loguru import logger

from nyt import constant

from nyt.src.nyt import NYT

from nyt.src.api.api import api as nyt_api
from nyt.src.logger.logger import (
    InterceptHandler
)

# Models
from nyt.src.models.config_model import Config

# Config manager
from nyt.src.config import ConfigManager

# Utils
from nyt.src.utils.assets import (
    check_assets,
    download_assets,
    create_assets_prefix
)

# Init cli
cli = typer.Typer()

# Config manager
config_manager = ConfigManager()
config = config_manager.load_config()

# Costum intercept handler
INTERCEPT_HANDLER = InterceptHandler()

@cli.command()
def version():
    """ nyt version """
    console.log(f"{constant.INFO} Version {constant.VERSION}")

@cli.command()
def track(
    channel_handle: str = typer.Option(None, "--channel-handle", help="The channel's handle"),
):
    """ Add a YouTube channel to track """
    nyt = NYT()

    rs_code = nyt.add_channel(
        channel_handle=channel_handle
    )
    if rs_code == constant.CHANNEL_ALREADY_TRACKED:
        logger.info(f"Channel '{channel_handle}' is already being tracked")
        return

    logger.info(f"Channel '{channel_handle}' added to be tracked")

@cli.command()
def remove(
    channel_handle: str = typer.Option(None, "--channel-handle", help="The channel's handle"),
):
    """ Remove a channel from being tracked """
    nyt = NYT()

    rs_code = nyt.remove_channel(
        channel_handle=channel_handle
    )
    if rs_code == constant.CHANNEL_NOT_TRACKED:
        logger.info(f"Channel '{channel_handle}' is not being tracked.")
        return

    logger.info(f"Channel '{channel_handle}' removed from being tracked.")

@cli.command()
def watch(
    delay: int = typer.Option(30, "--delay", help="The delay between each check in minutes"),
):
    """ Watch the YouTube channels and look out for new uploads """
    nyt = NYT()

    while True:
        try:
            nyt.watch()
        except KeyboardInterrupt or Exception:
            sys.exit(1)

        logger.info(f"Sleeping for {(delay*60)/60} minutes")

        time.sleep(delay*60)

@cli.command()
def api(
    host: str = typer.Option(config.API_HOST, "--host", help="The host for the API"),
    port: int = typer.Option(config.API_PORT, "--port", help="The port for the API"),
):
    """ Serve the API """
    uvicorn.run(
        nyt_api,
        host=host,
        port=port
    )

def run() -> None:
    """ main function """
    # Configure the logger
    log_level_str = "DEBUG"

    handler = logging.handlers.RotatingFileHandler(
        filename=config.API_LOGS_FILE_PATH,
        maxBytes=10*1024*1024,
        backupCount=3
    )
    logger.add(handler, level=log_level_str)

    SEEN = set()

    for name in [
        *logging.root.manager.loggerDict.keys(),
        "gunicorn",
        "gunicorn.access",
        "gunicorn.error",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ]:
        if name not in SEEN:
            SEEN.add(name.split(".")[0])
            logging.getLogger(name).handlers = [INTERCEPT_HANDLER]

    # Create prefix directories
    create_assets_prefix()

    # Check if the nyt's logos are installed
    if not check_assets():
        download_assets()

    cli()

