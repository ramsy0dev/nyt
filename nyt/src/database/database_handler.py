import json

from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    select,
    update,
    delete
)

# Database
from nyt.src.database.database import Database
from nyt.src.database.tables.declarative_base import Base

# Tables
from nyt.src.database.tables.channels_table import Channels
from nyt.src.database.tables.watched_videos_table import WatchedVideos

# Utils
from nyt.src.utils.date import date_in_gmt
from nyt.src.utils.generate_uid import generate_uid

class DatabaseHandler:
    """ Database handler """
    def __init__(self, database_path: str) -> None:
        self.database = Database(database_path=database_path)
        self.engine = self.database.engine()
        self.session = sessionmaker(bind=self.engine)

        self.create_tables()
    
    def create_tables(self) -> None:
        """
        Creates the database's tables

        Args:
            None.
        
        Returns:
            None.
        """
        Base.metadata.create_all(bind=self.engine)
    
    def add_channel_to_channels(self, channel_handle: str, video_starting_point_id: str) -> None:
        """
        Adds a channel to the channels table

        Args:
            channel_handle (str): The channel's handle.
            video_starting_point_id (str): The ID of the video that will be the starting point.
        
        Args:
            None.
        """
        channel = Channels()

        watched_videos_uid = generate_uid(data=channel_handle)
        
        channel.channel_uid = generate_uid(data=channel_handle)
        channel.channel_handle = channel_handle
        channel.video_starting_point_id = video_starting_point_id
        channel.watched_videos_uid = watched_videos_uid
        channel.added_at = date_in_gmt()

        with self.session() as session:
            session.add(channel)

            session.commit()
        
        self.create_watched_video_row(
            watched_videos_uid=watched_videos_uid
        )

    def delete_channel_row(self, channel_handle: str) -> None:
        """
        Delete a channel row.

        Args:
            channel_handle (str): The channel's handle.
        
        Returns:
            None.
        """
        with self.session() as session:
            channel = self.get_channel_row(channel_handle=channel_handle)

            stmts = [
                delete(Channels).where(
                    Channels.channel_handle == channel_handle
                ),
                delete(WatchedVideos).where(
                    WatchedVideos.watched_videos_uid == channel.watched_videos_uid
                )
            ]
            
            for stmt in stmts:
                session.execute(stmt)
            session.commit()
    
    def delete_watched_videos_row(self, watched_videos_uid: str) -> None:
        """
        Delete a watched_videos row.

        Args:
            watched_videos_uid (str): The watched_videos's UID.
        
        Returns:
            None.
        
        """
        with self.session() as session:
            stmt = delete(WatchedVideos).where(
                WatchedVideos.watched_videos_uid == watched_videos_uid
            )
            session.execute(stmt)
            session.commit()
        
    def get_channels(self) -> list[Channels]:
        """
        Returns a list of the rows in the channels table
        """
        channels: list[Channels] = None

        with self.session() as session:
            stmt = select(Channels)
            channels = session.execute(stmt).fetchall()
        
        return channels
    
    def create_watched_video_row(self, watched_videos_uid: str | None = None) -> None:
        """
        Creates a new row in the watched_videos table.

        Args:
            watched_videos_uid (str): A pre-generated UID.
        
        Returns:
            None.
        """
        watched_video = WatchedVideos()
        watched_video.watched_videos_uid = generate_uid(data="") if watched_videos_uid is None else watched_videos_uid
        watched_video.created_at = date_in_gmt()
        
        with self.session() as session:
            session.add(watched_video)
        
            session.commit()
    
    def get_watched_videos_row(self, watched_videos_uid: str | None = None, channel_handle: str | None = None) -> WatchedVideos:
        """
        fetch a row from the watched_videos table.

        Args:
            watched_videos_uid (str): The UID of the row to fetch.

        Returns:
            WatchedVideos: An instance of the table WatchedVideos. 
        """
        watched_videos: WatchedVideos = None

        with self.session() as session:
            if watched_videos_uid is not None:
                stmt = select(WatchedVideos).where(
                    WatchedVideos.watched_videos_uid == watched_videos_uid
                )

                watched_videos = session.execute(stmt).fetchone()[0]
            else:
                channel = self.get_channel_row(channel_handle=channel_handle)
                watched_videos_uid = channel.watched_videos_uid

                watched_videos = self.get_watched_videos_row(
                    watched_videos_uid=watched_videos_uid
                )

        return watched_videos
    
    def get_channel_row(self, channel_handle: str | None = None, channel_uid: str | None = None) -> None:
        """
        Fetch a channel row.

        Args:
            channel_handle (str, optional, default: None): The channel's handle.
            channel_uid (str, optional, default: None): The channel's UID.
        
        Returns:
            Channels: A Channels instance table of the channel.
        """
        channel: Channels = None

        with self.session() as session:
            stmt = select(Channels).where(
                Channels.channel_handle == channel_handle if channel_handle is not None else Channels.channel_uid == channel_uid
            )
            channel = session.execute(stmt).fetchone()[0]
        
        return channel

    def get_watched_videos(self) -> list[WatchedVideos]:
        """
        fetch a list of rows from the watched_videos table.

        Args:
            None.
        
        Returns:
            list[WatchedVideo]: A list of WatchedVideos instances.
        """
        watched_videos: list[WatchedVideos] = None

        with self.session() as session:
            stmt = select(WatchedVideos)
            watched_videos = [watched_video [0] for watched_video in session.execute(stmt).fetchall()]

        return watched_videos
    
    def add_video_id_to_watched_videos(self, watched_videos_uid: str, video_id: str, watched_videos: dict[str, list[str]]) -> None:
        """
        Adds a video id to the watched_videos column in the watched_videos table

        Args:
            watched_videos_uid (str): The watched_videos's UID.
            video_id (str): The video's id.
            watched_videos (dict[str, list[str]): The original list of the watched videos' id.
        
        Args:
            None.
        """
        watched_videos["ids"].append(video_id)

        with self.session() as session:
            stmt = update(WatchedVideos).where(
                WatchedVideos.watched_videos_uid == watched_videos_uid
            ).values(
                watched_videos = json.dumps(watched_videos),
                updated_at = date_in_gmt()
            )
            
            session.execute(stmt)
            session.commit()

    def update_video_starting_point_id(self, channel_handle: str, video_starting_point_id: str) -> None:
        """
        Update the video_starting_point_id column in the channels table.

        Args:
            channel_handle (str): The channel's handle.
            video_starting_point_id (str): The new video starting point ID.
        
        Returns:
            None.
        """
        with self.session() as session:
            stmt = update(Channels).where(
                Channels.channel_handle == channel_handle
            ).values(
                video_starting_point_id=video_starting_point_id
            )

            session.execute(stmt)
            session.commit()
    