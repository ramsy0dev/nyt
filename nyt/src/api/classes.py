# NYT
from nyt.src.nyt import NYT

# Database handler
from nyt.src.database.database_handler import DatabaseHandler

# Tracked channels
from nyt.src.api.channels.tracked_channels import TrackedChannels

# Videos
from nyt.src.api.videos.videos import VideosHandler

class Classes:
    """
    Handle the initilization of all the used classes in the API
    """
    def __init__(self) -> None:
        self.nyt = NYT()
        self.database_handler = DatabaseHandler()
        self.tracked_channels = TrackedChannels(nyt=self.nyt, database_handler=self.database_handler)
        self.videos_handler = VideosHandler(nyt=self.nyt, database_handler=self.database_handler)

classes = Classes()
