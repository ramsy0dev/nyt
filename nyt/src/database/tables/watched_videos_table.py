
from sqlalchemy import (
    Column,
    String
)
from sqlalchemy.dialects.sqlite import JSON, DATETIME

# Decrlarative base class
from nyt.src.database.tables.declarative_base import Base

class WatchedVideos(Base):
    """ watched_videos table """
    __tablename__ = "watched_videos"

    watched_videos_uid       =   Column(String, primary_key=True, nullable=False)
    watched_videos           =   Column(JSON, default={"ids": []})
    updated_at               =   Column(DATETIME, nullable=True)
    created_at               =   Column(DATETIME, nullable=False)

    def __repr__(self):
        return f"WatchedVideos(watched_videos_uid={self.watched_videos_uid!r}, watched_videos={self.watched_videos!r}, updated_at={self.updated_at!r}, created_at={self.created_at!r}"
