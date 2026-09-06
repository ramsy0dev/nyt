import os
import mimetypes

from pathlib import Path

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

    def get_local_formats(self, video_id: str) -> list[dict]:
        video = self.database_handler.get_video_from_videos(video_id=video_id)
        if not video or not video.is_downloaded:
            return []
        formats = [{"format_id": "original", "label": "Original", "height": 0, "ext": "mp4"}]
        for v in (video.variants or []):
            formats.append({
                "format_id": f"{v['height']}p",
                "label":     v["label"],
                "height":    v["height"],
                "ext":       "mp4",
            })
        return formats

    def stream_video(self, video_id: str, start: int, end: int, format_id: str | None = None):
        """Stream a downloaded video's local file. Only called for downloaded videos —
        stream-only (not-yet-downloaded) videos are played via a YouTube iframe embed
        on the frontend instead."""
        video = self.database_handler.get_video_from_videos(video_id=video_id)

        if not video or not video.is_downloaded or not video.download_path or not os.path.exists(video.download_path):
            async def _empty():
                return
                yield

            return _empty()

        if format_id and format_id != "original":
            for v in (video.variants or []):
                if f"{v['height']}p" == format_id:
                    vpath = v.get("path", "")
                    if vpath and os.path.exists(vpath):
                        return self._stream_local(vpath, start, end)
                    break

        return self._stream_local(video.download_path, start, end)

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

    def list_videos(self) -> list[dict]:
        videos = self.database_handler.get_videos_list()
        res = []
        for video in videos:
            channel_info = self.database_handler.get_channel_row(channel_handle=video.channel_handle)
            res.append({
                "video_id":                  video.video_id,
                "video_title":               video.title,
                "channel_handle":            video.channel_handle,
                "channel_name":              channel_info.channel_name if channel_info else "",
                "channel_avatar_url_default": channel_info.channel_avatar_url_default if channel_info else "",
                "publish_date":              video.publish_date.isoformat() if video.publish_date else None,
                "thumbnail_url":             video.thumbnail_url,
                "watch_url":                 f"/videos/{video.video_id}",
                "is_watched":                video.is_watched,
                "is_downloaded":             video.is_downloaded,
                "timestamp":                 video.timestamp.isoformat() if video.timestamp else None,
            })
        return res

    def check_video_exists(self, video_id: str) -> bool:
        return self.database_handler.get_video_from_videos(video_id=video_id) is not None
