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

# Utils
from nyt.src.utils.assets import (
    check_assets,
    download_assets,
    create_assets_prefix
)

# Init cli
cli = typer.Typer()

INTERCEPT_HANDLER = InterceptHandler()

@cli.command()
def version():
    """ nyt version """
    console.log(f"{constant.INFO} Version {constant.VERSION}")

@cli.command()
def track(
    channel_handle: str = typer.Option(None, "--channel-handle", help="The channel's handle"),
    # debug_mode: bool = typer.Option(False, "--debug-mode", help="Enable debug mode")
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
    # debug_mode: bool = typer.Option(False, "--debug-mode", help="Enable debug mode")
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
    # debug_mode: bool = typer.Option(False, "--debug-mode", help="Enable debug mode")
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
    host: str = typer.Option("127.0.0.1", "--host", help="The host for the API"),
    port: int = typer.Option(8080, "--port", help="The port for the API"),
    # debug_mode: bool = typer.Option(False, "--debug-mode", help="Enable debug mode")
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
        filename=constant.API_LOG_PATH,
        maxBytes=10*1024*1024,
        backupCount=3
    )
    logger.add(handler)

    logging.basicConfig(handlers=[INTERCEPT_HANDLER], level=log_level_str)
    logging.root.handlers = [INTERCEPT_HANDLER]
    logging.root.setLevel(log_level_str)

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

    logger.configure(handlers=[{"sink": sys.stdout}])
    
    # Create prefix directories
    create_assets_prefix()
    
    # Check if the nyt's logos are installed
    if not check_assets():
        download_assets()
    
    cli()
