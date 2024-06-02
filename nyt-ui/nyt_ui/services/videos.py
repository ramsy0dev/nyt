import requests

# Video model
from nyt_ui.services.models.video_model import VideoModel

class Videos:
    """
    The videos class to communicate with the API's videos routes
    """
    root_videos_api_route: str = "http://localhost:8888/api/v1/videos"

    def __init__(self) -> None:
        pass

    def get_videos_list(self) -> list[VideoModel]:
        """
        Fetches the videos list from the API

        Args:
            None.

        Returns:
            list[dict]: A list of VideoModel object containing info for each video.
        """
        url = f"{self.root_videos_api_route}/list/"

        res = requests.get(url)

        videos_info = [
            VideoModel().load_from_dict(video) for video in res.json()["videos_info"]
        ]

        return videos_info

    def stream_video(self, video_id: str) -> str:
        """
        Stream a video.

        Args:
            None.

        Returns:
            str: The url to the video.
        """
        return f"{self.root_videos_api_route}/videos/{video_id}"

