from sqlalchemy import (
    Column,
    String
)

# Decrlarative base class
from nyt.src.database.tables.declarative_base import Base
from sqlalchemy.dialects.sqlite import DATETIME

class Channels(Base):
    """ channels table """
    __tablename__ = "channels"

    channel_uid              =   Column(String, primary_key=True, nullable=False)
    channel_handle           =   Column(String, nullable=False)
    video_starting_point_id  =   Column(String, nullable=False)
    watched_videos_uid       =   Column(String, nullable=False)
    added_at                 =   Column(DATETIME, nullable=False)

    def __repr__(self):
        return f"Channels(channel_uid={self.channel_uid!r}, channel_handle={self.channel_handle!r}, video_starting_point_id={self.video_starting_point_id!r}, watched_videos_uid={self.watched_videos_uid!r}, added_at={self.added_at!r})"
