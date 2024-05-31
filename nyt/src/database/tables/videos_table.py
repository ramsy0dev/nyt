from sqlalchemy import (
    Column,
    String
)
from sqlalchemy.dialects.sqlite import (
    DATETIME,
    BOOLEAN,
    INTEGER
)

from nyt.src.database.tables.declarative_base import Base

class Videos(Base):
    """ videos table """
    __tablename__ = "videos"

    video_id        =   Column(String, primary_key=True, nullable=False)
    channel_handle  =   Column(String, nullable=False)
    thumbnail_url   =   Column(String, nullable=False)
    title           =   Column(String, nullable=False)
    publish_date    =   Column(DATETIME, nullable=False)
    download_path   =   Column(String, nullable=False)
    is_downloaded   =   Column(BOOLEAN, default=False, nullable=False)
    size            =   Column(INTEGER, nullable=False)
    is_watched      =   Column(BOOLEAN, default=False, nullable=False)
    timestamp       =   Column(DATETIME, nullable=True)
    updated_at      =   Column(DATETIME, nullable=True)
    added_at        =   Column(DATETIME, nullable=False)

    def __repr__(self):
        return f"Videos(video_id={self.video_id!r}, thumbnail_url={self.thumbnail_url!r}, title={self.title!r}, publish_date={self.publish_date!r}, download_path={self.download_path!r}, is_downloaded={self.is_downloaded!r}, size={self.size!r}, is_watched={self.is_watched}, timstamp={self.timestamp}, updated_at={self.updated_at!r}, added_at={self.added_at!r})"
