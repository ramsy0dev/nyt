import os

# NYT
from nyt.src.nyt import NYT

from nyt.constant import VIDEOS_PREFIX_DIRECTORY

# Database handler
from nyt.src.database.database_handler import DatabaseHandler

class VideosHandler:
    """
    handles downloaded YouTube videos
    """
    def __init__(self, database_handler: DatabaseHandler, nyt: NYT) -> None:
        self.database_handler = database_handler
        self.nyt = nyt

    def stream_video(self, video_id: str, start: int, end: int) -> None:
        """
        Streams a video.

        Args:
            video_id (str): The video's id.
        """
        video = self.database_handler.get_video_from_videos(video_id=video_id)

        if not os.path.exists(video.download_path) or not video.is_downloaded:
            output_path = self.nyt.download_video(
                video_id=video_id,
                prefix_directory=VIDEOS_PREFIX_DIRECTORY
            )
            values = {
                "download_path": output_path,
                "is_downloaded": True
            }

            self.database_handler.update_videos_values(
                values=values
            )
        else:
            output_path = video.download_path
        
        async def _stream_video(file_path: str, start: int, end: int):
            with open(file_path, "rb") as video_file:
                video_file.seek(start)
                while True:
                    chunk = video_file.read(min(end - start + 1, 1024 * 1024 * 7))  # Read up to 7MB at a time
                    if not chunk:
                        break
                    yield chunk
        
        return _stream_video(
            file_path=output_path,
            start=start,
            end=end
        )

    def list_videos(self) -> list[dict]:
        """ 
        List videos.

        Args:
            None.
        
        Returns:
            list[dict]: A list of videos' info.
        """
        videos = self.database_handler.get_videos_list()
        res = list()

        for video in videos:
            channel_info = self.database_handler.get_channel_row(channel_handle=video.channel_handle)
            video_info = {
                "video_id": video.video_id,
                "video_title": video.title,
                "channel_handle": video.channel_handle,
                "channel_avatar_url_default": channel_info.channel_avatar_url_default,
                "publish_date": video.publish_date,
                "thumbnail_url": video.thumbnail_url,
                "watch_url": f"/videos/{video.video_id}",
                "is_watched": video.is_watched,
                "timestamp": video.timestamp
            }
            
            res.append(video_info)

        return res
    
    def check_video_exists(self, video_id: str) -> bool:
        """
        Checks if a video exists of not.

        Args:
            video_id (str): The video's id.
        
        Returns:
            bool: True if yes, otherwise False is returned.
        """
        videos = self.database_handler.get_videos_list()

        for video in videos:
            if video.video_id == video_id:
                return True
            
        return False
