# NYT
from nyt.src.nyt import NYT

# Database handler
from nyt.src.database.database_handler import DatabaseHandler

class TrackedChannels:
    """
    Tracked channels class
    """
    def __init__(self, nyt: NYT, database_handler: DatabaseHandler) -> None:
        self.nyt = nyt
        self.database_handler = database_handler

    def list_tracked_channels(self) -> list[dict]:
        """
        Lists the tracked channels.

        Args:
            None.
        
        Returns:
            list[dict]: A list containing a dict of info about each channel that is being tracked.
        """
        channels = self.database_handler.get_channels()

        res: list[dict]  = list()

        for channel in channels:
            channel_info = {
                "channel_handle": channel.channel_handle,
                "channel_avatar_url_default": channel.channel_avatar_url_default,
                "channel_avatar_url_medium": channel.channel_avatar_url_medium,
                "channel_avatar_url_high": channel.channel_avatar_url_high,
                "added_at": channel.added_at
            }

            res.append(channel_info)
        
        return res
    
    def add_channel_to_tracked_list(self, channel_handle: str) -> dict:
        """
        Add a channel to the tracked channels list.

        Args:
            channel_handle (str): The channel's handle.

        Returns:
            None.
        """
        if self.nyt.check_channel_tracked(channel_handle=channel_handle):
            return {
                "status_code": 200,
                "message": f"The channel '{channel_handle}' is already being tracked."
            }
    
        self.nyt.add_channel(
            channel_handle=channel_handle
        )

        return {
            "status_code": 200,
            "message": f"The channel '{channel_handle}' have been added to the tracked channels list."
        }

    def remove_channel_from_tracked_list(self, channel_handle: str) -> tuple[str, str]:
        """
        Removes a channel from the tracked channels list.

        Args:
            channel_handler (str): The channel's handle.

        Returns:
            tuple[str, str]: A tuple containing status code and a message.
        """
        if not self.database_handler.check_channel_tracked(channel_handle=channel_handle):
            return { 
                "status_code": 404,
                "message": f"The channel '{channel_handle}' is not being tracked to be deleted."
            }

        self.database_handler.delete_channel_row(channel_handle=channel_handle)

        return {
            "status_code": 200,
            "message": f"The channel '{channel_handle}' have been deleted from the track channels list."
        }
        
