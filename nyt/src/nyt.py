import json
import yt_dlp

from pytube import (
    YouTube,
    Channel
)

from nyt import constant

# DatabaseHandler
from nyt.src.database.database_handler import DatabaseHandler

# Table
from nyt.src.database.tables.channels_table import Channels

# Utils
from nyt.src.utils.notification import send_notification

class NYT:
    youtube_base_route: str = "https://www.youtube.com"

    # yt-dlp options
    ydl_opts = {
        "quiet": True,
        "format": 'best',
        "progress": False,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }],
        "plugins": [
            "yt_dlp_plugins.age_gate_bypass.AgeGateBypassPlugin", # Plugin used to bypass age restriction
        ],
    }

    def __init__(self, database_path: str, debug_mode: bool, console) -> None:
        self.database_handler = DatabaseHandler(
            database_path=database_path
        )
        self.console = console
        self.debug_mode = debug_mode

    def add_channel(self, channel_handle: str) -> None:
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

        self.database_handler.add_channel_to_channels(
            channel_handle=channel_handle,
            video_starting_point_id=video_starting_point_id
        )

    def remove_channel(self, channel_handle: str) -> None:
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

        self.console.log(f"{constant.INFO} Channels that are being tracked are: {', '.join([channel.channel_handle for channel in channels])}")

        for channel in channels:
            self.console.log(f"{constant.INFO} Checking for new videos uploaded by '{channel.channel_handle}'")

            video_starting_point_id = channel.video_starting_point_id
            video_starting_point_id_index = None

            if self.debug_mode:
                self.console.log(f"{constant.DEBUG} Fetching last 10 videos by '{channel.channel_handle}'")

            channel_last_videos = self.get_channel_last_videos(
                channel_handle=channel.channel_handle
            )

            if self.debug_mode:
                self.console.log(f"{constant.DEBUG} Found {len(channel_last_videos)} videos")

            for i in range(len(channel_last_videos)):
                video = channel_last_videos[i]
                video_id = video.video_id

                if video_id == video_starting_point_id:
                    video_starting_point_id_index = i
                    break

            # Check if the starting video if the last uploaded video
            if len(channel_last_videos[video_starting_point_id_index:]) == 1:
                self.console.log(f"{constant.INFO} No new videos found.")
                continue

            new_videos = channel_last_videos[video_starting_point_id_index+1:] # Exclude the video starting point

            self.console.log(f"{constant.INFO} {len(new_videos)} new videos uploaded by '{channel.channel_handle}'")

            summary_text = "New YouTube Videos"
            message = f"{len(new_videos)} videos uploaded by '{channel.channel_handle}'"

            send_notification(
                summary_text=summary_text,
                message=message
            )

            for video in new_videos:
                self.console.log(f"{constant.INFO} Downloading '{video.title}' by '{video.author}' to '{constant.VIDEOS_PREFIX_DIRECTORY}'")
                self.download_video(
                    video=video,
                    prefix_directory=constant.VIDEOS_PREFIX_DIRECTORY
                )


                if self.debug_mode:
                    self.console.log(f"{constant.DEBUG} Flaging '{video.video_id}' as watched from '{channel.channel_handle}'")

                self.flag_video_watched(
                    video_id=video.video_id,
                    watched_videos_uid=channel.watched_videos_uid,
                    channel_handle=channel.channel_handle
                )

            # Updating the video starting point to be the latest uploaded video
            if self.debug_mode:
                self.console.log(f"{constant.DEBUG} Updating the starting point to be '{video.video_id}', old starting point is '{channel.video_starting_point_id}'")

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
        channels = [channel[0] for channel in self.database_handler.get_channels()]

        return channels

    def check_channel_tracked(self, channel_handle: str) -> bool:
        """
        Checks if a channel is already in the track list.

        Args:
            channel_handle (str): The channel's handle to be checked.

        Returns:
            bool: True if yes, otherwise False.
        """
        channels = self.database_handler.get_channels()
        channels_handle = [channel[0].channel_handle for channel in channels]

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

        if self.debug_mode:
            self.console.log(f"{constant.DEBUG} Watched videos from '{channel_handle}' are {', '.join(video_ids)}")

        if video_id in video_ids:
            return True

        return False

    def flag_video_watched(self, video_id: str, watched_videos_uid: str, channel_handle: str) -> None:
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
        Returns the last 10 uploaded videos to a YouTube channel

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

        for content_block in contents_block[:10]:
            video_content = content_block["richItemRenderer"]["content"]
            video_id = video_content["videoRenderer"]["videoId"]
            video_url = f"{self.youtube_base_route}/watch?v={video_id}"

            video = YouTube(video_url)
            videos.append(video)

            if self.debug_mode:
                self.console.log(f"{constant.DEBUG} {video_id = }, title = {video_content['videoRenderer']['title']['runs'][0]['text']}")

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

    def download_video(self, video: YouTube, prefix_directory: str) -> None:
        """
        Download a YouTube video.

        Args:
            prefix_directory (str): The directory where to save the video.

        Returns:
            None.
        """
        self.ydl_opts["outtmpl"] = f"{prefix_directory}/%(uploader)s/%(title)s"

        with yt_dlp.YoutubeDL(self.ydl_opts) as yt:
            yt.download([video.watch_url])
