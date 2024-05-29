import sys
import time
import typer

from rich import console

from nyt import constant

from nyt.src.nyt import NYT

# Init cli
cli = typer.Typer()

# Init console
console = console.Console()

@cli.command()
def version():
    """ nyt version """
    console.log(f"{constant.INFO} Version {constant.VERSION}")

@cli.command()
def track(
    channel_handle: str = typer.Option(None, "--channel-handle", help="The channel's handle"),
    debug_mode: bool = typer.Option(False, "--debug-mode", help="Enable debug mode")
):
    """ Add a YouTube channel to track """
    nyt = NYT(
        database_path=constant.DATABASE_PATH,
        console=console,
        debug_mode=debug_mode
    )

    rs_code = nyt.add_channel(
        channel_handle=channel_handle
    )
    if rs_code == constant.CHANNEL_ALREADY_TRACKED:
        console.log(f"{constant.INFO} Channel '{channel_handle}' is already being tracked")
        return
    
    console.log(f"{constant.INFO} Channel '{channel_handle}' added to be tracked")

@cli.command()
def remove(
    channel_handle: str = typer.Option(None, "--channel-handle", help="The channel's handle"),
    debug_mode: bool = typer.Option(False, "--debug-mode", help="Enable debug mode")
):
    """ Remove a channel from being tracked """
    nyt = NYT(
        database_path=constant.DATABASE_PATH,
        console=console,
        debug_mode=debug_mode
    )
    
    rs_code = nyt.remove_channel(
        channel_handle=channel_handle
    )
    if rs_code == constant.CHANNEL_NOT_TRACKED:
        console.log(f"{constant.INFO} Channel '{channel_handle}' is not being tracked.")
        return
    
    console.log(f"{constant.INFO} Channel '{channel_handle}' removed from being tracked.")

@cli.command()
def watch(
    delay: int = typer.Option(30, "--delay", help="The delay between each check in minutes"),
    debug_mode: bool = typer.Option(False, "--debug-mode", help="Enable debug mode")
):
    """ Watch the YouTube channels and look out for new uploads """
    nyt = NYT(
        database_path=constant.DATABASE_PATH,
        console=console,
        debug_mode=debug_mode
    )

    while True:
        try:
            nyt.watch()
        except KeyboardInterrupt or Exception:
            sys.exit(1)
        
        console.log(f"{constant.INFO} Sleeping for {(delay*60)/60} minute")

        time.sleep(delay*60)

def run() -> None:
    cli()
