import sys
import json
import random
import yt_dlp
import requests

from pathlib import Path
from loguru import logger
from datetime import datetime

from pytube import (
    YouTube,
    Channel
)

from nyt import constant

# DatabaseHandler
from nyt.src.database.database_handler import DatabaseHandler

# Table
from nyt.src.database.tables.channels_table import Channels
from nyt.src.database.tables.videos_table import Videos

# Models
from nyt.src.models.config_model import Config

# Utils
from nyt.src.utils.date import date_in_gmt
from nyt.src.utils.generate_uid import generate_uid
from nyt.src.utils.notification import send_notification

# Config manager
from nyt.src.config import ConfigManager

class NYT:
    """
    nyt base class
    """
    youtube_base_route: str = "https://www.youtube.com"

    # yt-dlp options
    ydl_opts = {
        "quiet": True,
        "format": 'bestvideo+bestaudio/best[ext=mp4]', # File extension set to 'mp4' 
        "progress": True,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            # "preferedformat": "mp4"
        }],
        "plugins": [
            "yt_dlp_plugins.age_gate_bypass.AgeGateBypassPlugin", # Plugin used to bypass age restriction
        ],
    }
    # Retries count
    DOWNLOAD_RETRIES: int = 3

    # Pair for each channel and the YouTube API Json response
    channels_js_pair: dict[str, dict] = dict()
    
    # notification
    show_notification: bool = True
    
    # Config manager 
    config_manager: ConfigManager = ConfigManager()
    config: Config = config_manager.load_config()

    def __init__(self) -> None:
        self.database_handler = DatabaseHandler(database_path=self.config.DATABASE_PATH)
        
        config_manager = ConfigManager()
        self.config = config_manager.load_config()

    def add_channel(self, channel_handle: str) -> float | None:
        """
        Adds a channel to be tracked

        Args:
            channel_handle (str): The channel's handle.

        Returns:
            None.
        """
        if self.check_channel_tracked(channel_handle=channel_handle):
            return constant.CHANNEL_ALREADY_TRACKED

        video_starting_point_id = self.get_channel_last_videos(channel_handle=channel_handle)[-1].video_id

        channel_info = self.get_channel_info(channel_handle=channel_handle)

        channel = Channels()

        watched_videos_uid = generate_uid(data=channel_handle)

        channel.channel_uid = generate_uid(data=channel_handle)
        channel.channel_handle = channel_handle
        channel.video_starting_point_id = video_starting_point_id
        channel.watched_videos_uid = watched_videos_uid

        channel.channel_avatar_url_default = channel_info["avatar_urls"][0]
        channel.channel_avatar_url_medium = channel_info["avatar_urls"][1]
        channel.channel_avatar_url_high = channel_info["avatar_urls"][2]

        channel.added_at = date_in_gmt()

        self.database_handler.add_channel_to_channels(
            channel=channel
        )

    def remove_channel(self, channel_handle: str) -> float | None :
        """
        Remove a channel from being tracked.

        Args:
            channel_handle (str): The channel's handle.

        Returns:
            None.
        """
        if not self.check_channel_tracked(channel_handle=channel_handle):
            return constant.CHANNEL_NOT_TRACKED

        self.database_handler.delete_channel_row(channel_handle=channel_handle)

    def watch(self) -> None:
        """
        Goes through all the channels, and checks if new videos have been uploaded.
        if yes then the video will be downloaded and a notification will displayed.

        Args:
            None.

        Returns:
            None.
        """
        channels = self.get_channels()
        
        if len(channels) == 0:
            logger.info("No channels in the channels track list.")
            sys.exit(0)

        logger.info(f"Channels that are being tracked are: {', '.join([channel.channel_handle for channel in channels])}")

        for channel in channels:
            logger.info(f"Checking for new videos uploaded by '{channel.channel_handle}'")

            video_starting_point_id = channel.video_starting_point_id
            video_starting_point_id_index = None

            logger.debug(f"Fetching last uploaded videos by '{channel.channel_handle}'")

            channel_last_videos = self.get_channel_last_videos(
                channel_handle=channel.channel_handle
            )

            logger.debug(f"Found {len(channel_last_videos)} videos")

            for i in range(len(channel_last_videos)):
                video = channel_last_videos[i]
                video_id = video.video_id

                if video_id == video_starting_point_id:
                    video_starting_point_id_index = i
                    break

            # Check if the starting video if the last uploaded video
            if len(channel_last_videos[video_starting_point_id_index:]) == 1:
                logger.info(f"No new videos found.")
                continue

            new_videos = channel_last_videos[video_starting_point_id_index+1:] # Exclude the video starting point

            logger.info(f"{len(new_videos)} new videos uploaded by '{channel.channel_handle}'")
            
            if self.show_notification:
                summary_text = "New YouTube Videos"
                message = f"{len(new_videos)} videos uploaded by '{channel.channel_handle}'"
                
                send_notification(
                    app_name=constant.PACKAGE,
                    summary_text=summary_text,
                    message=message,
                    icon_path=self.config.NYT_HIGH_RESOLUTION_LOGO
                )
            

            for video in new_videos:
                logger.info(f"Downloading '{video.title}' by '{video.author}' to '{self.config.VIDEOS_PREFIX_DIRECTORY}'")
 
                outer_break = False
                while self.DOWNLOAD_RETRIES:
                    n_fails = 1
                    try:
                        output_path, publish_date, title, thumbnail_url, size = self.download_video(
                            video_id=video.video_id,
                            prefix_directory=self.config.VIDEOS_PREFIX_DIRECTORY
                        )
                    except Exception as error:
                        if self.DOWNLOAD_RETRIES - n_fails == 0:
                            logger.warning(f"Skipping '{video.title}'. Reached maximum retries {self.DOWNLOAD_RETRIES}")
                            outer_break = True
                            continue
                        logger.warning(f"Faild to download. Run into error: '{error}' Retrying... {n_fails}")
                        n_fails += 1

                if outer_break:
                    continue

                _video = Videos(
                    video_id = video_id,
                    channel_handle = channel.channel_handle,
                    download_path = output_path,
                    is_downloaded = True,
                    is_watched = False,
                    publish_date = publish_date,
                    added_at = date_in_gmt(),
                    thumbnail_url = thumbnail_url,
                    title = title,
                    size = size
                )

                self.database_handler.add_video_to_videos(video=_video)

                logger.debug(f"Flaging '{video.video_id}' as watched from '{channel.channel_handle}'")

                self.flag_video_watched(
                    video_id=video.video_id,
                    watched_videos_uid=channel.watched_videos_uid
                )

            # Updating the video starting point to be the latest uploaded video
            logger.debug(f"Updating the starting point to be '{video.video_id}', old starting point is '{channel.video_starting_point_id}'")

            self.database_handler.update_video_starting_point_id(
                channel_handle=channel.channel_handle,
                video_starting_point_id=new_videos[-1].video_id
            )

    def get_channels(self) -> list[Channels]:
        """
        Fetches all the channels that are flaged to be tracked
        in the channels table.

        Args:
            None.

        Returns:
            list[Channels]: A list of Channels table instance of each channel.
        """
        channels = self.database_handler.get_channels()

        return channels

    def get_channel_info(self, channel_handle: str) -> dict:
        """
        Fetches info about a channel.

        Args:
            channel_handle (str): The channel's handle.

        Returns:
            dict: A dict containing the channel's info.
        """
        self._load_channel_js(channel_handle=channel_handle)

        channel_info = {
            "avatar_urls": self._get_channel_avatar_url(channel_handle=channel_handle)
        }

        return channel_info

    def _load_channel_js(self, channel_handle: str) -> None:
        api_key = random.choice(constant._api_keys)

        channel = Channel(f"{self.youtube_base_route}/@{channel_handle}")

        api_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel.channel_id}&key={api_key}"

        res = requests.get(api_url)
        res_json = res.json()

        self.channels_js_pair[channel_handle] = res_json

    def _get_channel_avatar_url(self, channel_handle: str) -> tuple[str, str, str]:
        avatar_url_default = self.channels_js_pair[channel_handle]['items'][0]['snippet']['thumbnails']['default']['url']
        avatar_url_medium = self.channels_js_pair[channel_handle]['items'][0]['snippet']['thumbnails']['medium']['url']
        avatar_url_high = self.channels_js_pair[channel_handle]['items'][0]['snippet']['thumbnails']['high']['url']

        return (avatar_url_default, avatar_url_medium, avatar_url_high)

    def check_channel_tracked(self, channel_handle: str) -> bool:
        """
        Checks if a channel is already in the track list.

        Args:
            channel_handle (str): The channel's handle to be checked.

        Returns:
            bool: True if yes, otherwise False.
        """
        channels = self.database_handler.get_channels()
        channels_handle = [channel.channel_handle for channel in channels]

        if channel_handle in channels_handle:
            return True

        return False

    def check_video_watched(self, video_id: str, channel_handle: str) -> bool:
        """
        Checks if the video was already watched or not

        Args:
            video_id (str): The video's ID.
            channel_handle (str): The channel's handle.

        Returns:
            bool: True if yes, otherwise False.
        """
        watched_videos = self.database_handler.get_watched_videos_row(channel_handle=channel_handle)

        if isinstance(watched_videos.watched_videos, dict):
            video_ids = watched_videos.watched_videos
        else:
            video_ids = json.loads(watched_videos.watched_videos)["ids"]

        logger.debug(f"Watched videos from '{channel_handle}' are {', '.join(video_ids)}")

        if video_id in video_ids:
            return True

        return False

    def flag_video_watched(self, video_id: str, watched_videos_uid: str) -> None:
        """
        Flags a video id as watched.

        Args:
            video_id (str): The video's ID.
            watched_videos_uid (str): The watched_videos' UID.
            channel_handle (str): The channel's handle.

        Returns:
            None.
        """
        watched_videos = self.database_handler.get_watched_videos_row(watched_videos_uid=watched_videos_uid)
        if isinstance(watched_videos.watched_videos, dict):
            watched_videos = watched_videos.watched_videos
        else:
            watched_videos = json.loads(watched_videos.watched_videos)

        self.database_handler.add_video_id_to_watched_videos(
            video_id=video_id,
            watched_videos_uid=watched_videos_uid,
            watched_videos=watched_videos
        )

    def get_channel_last_videos(self, channel_handle: str) -> list[YouTube]:
        """
        Returns the last uploaded videos to a YouTube channel

        Args:
            channel_handle (str): The channel's handle.

        Returns:
            list[YouTube]: A list of YouTube instances.
        """
        videos = []
        url = f"{self.youtube_base_route}/@{channel_handle}"
        channel = Channel(url)

        initial_data_json = channel.initial_data

        contents_block = initial_data_json["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1]["tabRenderer"]["content"]["richGridRenderer"]["contents"]

        for content_block in contents_block[:int(len(contents_block)/2)]:
            video_content = content_block["richItemRenderer"]["content"]
            video_id = video_content["videoRenderer"]["videoId"]
            video_url = f"{self.youtube_base_route}/watch?v={video_id}"

            video = YouTube(video_url)
            videos.append(video)

            logger.debug(f"{video_id = }, title = \'{video_content['videoRenderer']['title']['runs'][0]['text']}\'")

        return videos[::-1]

    # def order_videos(self, videos: list[YouTube]) -> list[YouTube]:
    #     """
    #     Orders the videos from the older to the most recent uploaded.

    #     Args:
    #         videos (list[YouTube]): A list of YouTube instance of videos.

    #     Returns:
    #         list[YouTube]: The ordered version of the original list.
    #     """
    #     order = {} # video_id : current_date - publish_date

    #     for video in videos:
    #         diff = video.publish_date - datetime.now()
    #         diff = diff.total_seconds()

    #         order[video.video_id] = diff

    #     sorted_order = sorted([order[video_id] for video_id in order])

    #     ordered_videos = []

    #     for diff in sorted_order:
    #         for video_id in order:
    #             if diff == order[video_id]:
    #                 video = YouTube(f"{self.youtube_base_route}/watch?v={video_id}")
    #                 ordered_videos.append(video)
    #             break

    #     return ordered_videos[::-1]

    def download_video(self, video_id: str, prefix_directory: str) -> tuple:
        """
        Download a YouTube video.

        Args:
            video_id (str): The video's id.
            prefix_directory (str): The directory where to save the video.

        Returns:
            tuple: A tuple of data about the video.
        """
        self.ydl_opts["outtmpl"] = f"{prefix_directory}{constant.PATH_DASH}%(uploader)s{constant.PATH_DASH}%(title)s"

        video_url = f"{self.youtube_base_route}/watch?v={video_id}"

        with yt_dlp.YoutubeDL(self.ydl_opts) as yt: 
            info_dict = yt.extract_info(video_url, download=False)

            yt.download([video_url])

            # file_name = yt.prepare_filename(info_dict=info_dict) +  ".mp4"
            
            file_name = yt.prepare_filename(info_dict=info_dict)
            title = info_dict.get("title", None)
            thumbnail_url = info_dict.get("thumbnail", None)

            logger.debug(f"{file_name = }, {title = }")

            size = Path(file_name).stat().st_size
            publish_date = datetime.fromtimestamp(int(info_dict["upload_date"]))

        return (file_name, publish_date, title, thumbnail_url, size)
