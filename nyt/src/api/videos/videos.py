import os
import mimetypes
import requests
import yt_dlp

from pathlib import Path
from loguru import logger

from nyt.src.database.database_handler import DatabaseHandler
from nyt.src.nyt import NYT

_MIME_FALLBACK = "video/mp4"
_CHUNK = 8 * 1024 * 1024  # 8 MB


def _mime_for(path: str) -> str:
    guessed, _ = mimetypes.guess_type(path)
    return guessed or _MIME_FALLBACK


class VideosHandler:
    def __init__(self, database_handler: DatabaseHandler, nyt: NYT) -> None:
        self.database_handler = database_handler
        self.nyt = nyt

    def get_video_mime(self, video_id: str) -> str:
        video = self.database_handler.get_video_from_videos(video_id=video_id)
        if video and video.is_downloaded and video.download_path:
            return _mime_for(video.download_path)
        return _MIME_FALLBACK

    def stream_video(self, video_id: str, start: int, end: int):
        video = self.database_handler.get_video_from_videos(video_id=video_id)

        if video and video.is_downloaded and video.download_path and os.path.exists(video.download_path):
            return self._stream_local(video.download_path, start, end)

        return self._stream_youtube(video_id, start, end)

    def _stream_local(self, file_path: str, start: int, end: int):
        file_size = Path(file_path).stat().st_size
        read_end  = end if end else file_size - 1

        async def _gen():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = read_end - start + 1
                while remaining > 0:
                    chunk = f.read(min(_CHUNK, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return _gen()

    def _stream_youtube(self, video_id: str, start: int, end: int):
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {"quiet": True, "format": "best[ext=mp4]/best"}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            stream_url = info["url"]
        except Exception as exc:
            logger.warning(f"Could not resolve YouTube stream for '{video_id}': {exc}")

            async def _empty():
                return
                yield  # make it a generator

            return _empty()

        headers: dict = {}
        if start or end:
            headers["Range"] = f"bytes={start}-{end or ''}"

        def _gen():
            with requests.get(stream_url, headers=headers, stream=True, timeout=30) as r:
                for chunk in r.iter_content(chunk_size=_CHUNK):
                    if chunk:
                        yield chunk

        return _gen()

    def list_videos(self) -> list[dict]:
        videos = self.database_handler.get_videos_list()
        res = []
        for video in videos:
            channel_info = self.database_handler.get_channel_row(channel_handle=video.channel_handle)
            res.append({
                "video_id":                  video.video_id,
                "video_title":               video.title,
                "channel_handle":            video.channel_handle,
                "channel_avatar_url_default": channel_info.channel_avatar_url_default if channel_info else "",
                "publish_date":              video.publish_date,
                "thumbnail_url":             video.thumbnail_url,
                "watch_url":                 f"/videos/{video.video_id}",
                "is_watched":                video.is_watched,
                "is_downloaded":             video.is_downloaded,
                "timestamp":                 video.timestamp,
            })
        return res

    def check_video_exists(self, video_id: str) -> bool:
        return self.database_handler.get_video_from_videos(video_id=video_id) is not None
