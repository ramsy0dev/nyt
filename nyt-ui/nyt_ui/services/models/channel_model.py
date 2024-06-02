from datetime import datetime

# Model
from nyt_ui.services.models.model import Model

class Channel(Model):
    """
    The channel model
    """
    channel_handle: str
    channel_avatar_url_default: str
    channel_avatar_url_medium: str
    channel_avatar_url_high: str
    added_at: datetime

    def __init__(self) -> None:
        super().__init__()
