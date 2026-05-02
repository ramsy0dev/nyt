import os
import shutil
import subprocess
import time
import mimetypes
import requests
import yt_dlp

from pathlib import Path
from loguru import logger

from nyt.src.database.database_handler import DatabaseHandler
from nyt.src.nyt import NYT

_MIME_FALLBACK = "video/mp4"
_CHUNK = 8 * 1024 * 1024  # 8 MB
_FORMAT_TTL = 3600  # YouTube stream URLs stay valid for ~6 hours; cache conservatively

_format_cache: dict[str, dict] = {}  # video_id -> {expires_at, formats, url_map, video_only_ids, best_audio_url}


def _mime_for(path: str) -> str:
    guessed, _ = mimetypes.guess_type(path)
    return guessed or _MIME_FALLBACK


def _ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


class VideosHandler:
    def __init__(self, database_handler: DatabaseHandler, nyt: NYT) -> None:
        self.database_handler = database_handler
        self.nyt = nyt

    def get_video_mime(self, video_id: str) -> str:
        video = self.database_handler.get_video_from_videos(video_id=video_id)
        if video and video.is_downloaded and video.download_path:
            return _mime_for(video.download_path)
        return _MIME_FALLBACK

    def get_formats(self, video_id: str) -> list[dict]:
        cached = _format_cache.get(video_id)
        if cached and time.monotonic() < cached["expires_at"]:
            return cached["formats"]

        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            logger.warning(f"Could not fetch formats for '{video_id}': {exc}")
            return []

        raw_formats = info.get("formats", [])

        # Find best audio-only format; prefer m4a/AAC for MP4 container compatibility
        audio_only = [
            f for f in raw_formats
            if f.get("vcodec") == "none" and f.get("acodec") != "none" and f.get("url")
        ]
        audio_only.sort(key=lambda f: (f.get("ext") == "m4a", f.get("abr") or 0), reverse=True)
        best_audio_url = audio_only[0]["url"] if audio_only else None

        formats: list[dict] = []
        seen: set[str] = set()
        video_only_ids: set[str] = set()

        # First pass: muxed streams (audio + video), no merging needed
        for f in raw_formats:
            height = f.get("height")
            if not height or not f.get("url"):
                continue
            if f.get("acodec") == "none" or f.get("vcodec") == "none":
                continue
            fps   = f.get("fps") or 0
            label = f"{height}p{int(fps)}" if fps > 30 else f"{height}p"
            if label in seen:
                continue
            seen.add(label)
            formats.append({
                "format_id": f["format_id"],
                "label":     label,
                "height":    height,
                "ext":       f.get("ext", "mp4"),
            })

        # Second pass: video-only DASH streams merged with best audio via ffmpeg.
        # Only adds heights not already covered by muxed streams above.
        if best_audio_url and _ffmpeg_available():
            for f in raw_formats:
                height = f.get("height")
                if not height or not f.get("url"):
                    continue
                if f.get("acodec") != "none" or f.get("vcodec") == "none":
                    continue
                fps   = f.get("fps") or 0
                label = f"{height}p{int(fps)}" if fps > 30 else f"{height}p"
                if label in seen:
                    continue
                seen.add(label)
                video_only_ids.add(f["format_id"])
                formats.append({
                    "format_id": f["format_id"],
                    "label":     label,
                    "height":    height,
                    "ext":       f.get("ext", "mp4"),
                })

        formats.sort(key=lambda x: x["height"], reverse=True)

        _format_cache[video_id] = {
            "expires_at":     time.monotonic() + _FORMAT_TTL,
            "formats":        formats,
            "url_map":        {f["format_id"]: f["url"] for f in raw_formats if f.get("url")},
            "video_only_ids": video_only_ids,
            "best_audio_url": best_audio_url,
        }
        return formats

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
        video = self.database_handler.get_video_from_videos(video_id=video_id)

        if video and video.is_downloaded and video.download_path and os.path.exists(video.download_path):
            if format_id and format_id != "original":
                for v in (video.variants or []):
                    if f"{v['height']}p" == format_id:
                        vpath = v.get("path", "")
                        if vpath and os.path.exists(vpath):
                            return self._stream_local(vpath, start, end)
                        break
            return self._stream_local(video.download_path, start, end)

        return self._stream_youtube(video_id, start, end, format_id=format_id)

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

    def _stream_youtube(self, video_id: str, start: int, end: int, format_id: str | None = None):
        stream_url = None

        if format_id:
            cached = _format_cache.get(video_id)
            if cached and time.monotonic() < cached["expires_at"]:
                # Video-only DASH format — merge with best audio via ffmpeg
                if format_id in cached.get("video_only_ids", set()):
                    video_url = cached["url_map"].get(format_id)
                    audio_url = cached.get("best_audio_url")
                    if video_url and audio_url:
                        return self._stream_merged_youtube(video_url, audio_url)
                stream_url = cached["url_map"].get(format_id)

        if not stream_url:
            url      = f"https://www.youtube.com/watch?v={video_id}"
            fmt      = format_id if format_id else "best[ext=mp4]/best"
            ydl_opts = {"quiet": True, "format": fmt}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                stream_url = info["url"]
            except Exception as exc:
                logger.warning(f"Could not resolve YouTube stream for '{video_id}': {exc}")

                async def _empty():
                    return
                    yield

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

    def _stream_merged_youtube(self, video_url: str, audio_url: str):
        cmd = [
            'ffmpeg', '-loglevel', 'error',
            '-i', video_url,
            '-i', audio_url,
            '-c', 'copy',
            '-f', 'mp4',
            '-movflags', 'frag_keyframe+empty_moov+default_base_moof',
            'pipe:1',
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        def _gen():
            try:
                while True:
                    chunk = proc.stdout.read(_CHUNK)
                    if not chunk:
                        break
                    yield chunk
            finally:
                try:
                    proc.terminate()
                    proc.wait()
                except Exception:
                    pass

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
