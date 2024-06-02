from datetime import datetime

# Model
from nyt_ui.services.models.model import Model

class VideoModel(Model):
    """
    A video model
    """
    video_id: str = ""
    video_title: str = ""
    channel_handle: str = ""
    channel_avatar_url_default: str = ""
    thumbnail_url: str = ""
    publish_date: str = ""
    watch_url: str = ""
    is_watched: bool = False
    timestamp: datetime = ""

    def __init__(self) -> None:
        super().__init__()
