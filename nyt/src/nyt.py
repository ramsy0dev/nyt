import subprocess
import threading
import yt_dlp
import requests

from dataclasses import dataclass
from pathlib import Path
from loguru import logger
from datetime import datetime

from nyt import constant


@dataclass
class _VideoEntry:
    video_id: str
    title:    str
from nyt.src.database.database_handler import DatabaseHandler
from nyt.src.database.tables.channels_table import Channels
from nyt.src.database.tables.videos_table import Videos
from nyt.src.utils import date_in_gmt, generate_uid, send_notification
from nyt.src.config import ConfigManager


class NYT:
    YOUTUBE_BASE     = "https://www.youtube.com"
    DOWNLOAD_RETRIES = 3
    show_notification = True

    _ydl_base_opts: dict = {
        "quiet":    True,
        "progress": True,
        "format":   "best[ext=mp4]/best",
    }

    def __init__(self) -> None:
        self.config           = ConfigManager().load_config()
        self.database_handler = DatabaseHandler(database_path=self.config.DATABASE_PATH)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_channel(self, channel_handle: str) -> int | None:
        if self.database_handler.check_channel_tracked(channel_handle):
            return constant.CHANNEL_ALREADY_TRACKED

        videos = self.get_channel_last_videos(channel_handle)
        video_starting_point_id = videos[-1].video_id

        # One API call (forHandle=) covers name + avatar — no second page scrape needed.
        info = self.search_channel(channel_handle) or {}

        channel = Channels(
            channel_uid                = generate_uid(),
            channel_handle             = channel_handle,
            channel_name               = info.get("channel_name", ""),
            video_starting_point_id    = video_starting_point_id,
            watched_videos_uid         = generate_uid(),
            channel_avatar_url_default = info.get("avatar_url_default", ""),
            channel_avatar_url_medium  = info.get("avatar_url_medium",  ""),
            channel_avatar_url_high    = info.get("avatar_url_high",    ""),
            added_at                   = date_in_gmt(),
        )
        self.database_handler.add_channel_to_channels(channel=channel)
        display = info.get("channel_name") or channel_handle
        logger.info(f"Now tracking '{display}' (@{channel_handle}) — starting from {video_starting_point_id}")

        avatar_url = (
            channel.channel_avatar_url_high
            or channel.channel_avatar_url_medium
            or channel.channel_avatar_url_default
        )
        if avatar_url:
            self._download_avatar(channel_handle, avatar_url)

    def remove_channel(self, channel_handle: str) -> int | None:
        if not self.database_handler.check_channel_tracked(channel_handle):
            return constant.CHANNEL_NOT_TRACKED
        self.database_handler.delete_channel_row(channel_handle=channel_handle)
        logger.info(f"Stopped tracking '@{channel_handle}' — videos and files removed")

    def check_channel_tracked(self, channel_handle: str) -> bool:
        return self.database_handler.check_channel_tracked(channel_handle)

    def watch(self) -> None:
        channels = self.database_handler.get_channels()

        if not channels:
            logger.info("No channels in the track list.")
            return

        logger.info(f"Tracking: {', '.join(c.channel_handle for c in channels)}")

        for channel in channels:
            if channel.last_checked_at is not None:
                delay = channel.watch_delay_minutes or self.config.WATCH_DELAY_MINUTES
                last  = channel.last_checked_at
                if hasattr(last, "tzinfo") and last.tzinfo is not None:
                    last = last.replace(tzinfo=None)
                elapsed = (datetime.utcnow() - last).total_seconds()
                if elapsed < delay * 60:
                    logger.debug(
                        f"Skipping '{channel.channel_handle}' — "
                        f"not due for {int((delay * 60 - elapsed) // 60)}m"
                    )
                    continue

            logger.info(f"Checking '{channel.channel_handle}' for new uploads")

            try:
                channel_last_videos = self.get_channel_last_videos(channel.channel_handle)
            except RuntimeError as exc:
                logger.warning(str(exc))
                self.database_handler.update_channel_last_checked(channel.channel_handle)
                continue

            logger.debug(f"Fetched {len(channel_last_videos)} videos")

            start_idx = next(
                (i for i, v in enumerate(channel_last_videos) if v.video_id == channel.video_starting_point_id),
                None,
            )

            if start_idx is None:
                logger.warning(
                    f"Starting-point video not found for '{channel.channel_handle}'. "
                    "Treating all fetched videos as new."
                )
                new_videos = channel_last_videos
            elif start_idx == len(channel_last_videos) - 1:
                logger.info(f"No new videos from '{channel.channel_handle}'.")
                self.database_handler.update_channel_last_checked(channel.channel_handle)
                continue
            else:
                new_videos = channel_last_videos[start_idx + 1:]

            logger.info(f"{len(new_videos)} new video(s) from '{channel.channel_handle}'")

            if self.show_notification:
                icon = str(Path(self.config.ASSETS_PREFIX) / "nyt-high-resolution-logo.png")
                send_notification(
                    app_name     = constant.PACKAGE,
                    summary_text = "New YouTube Videos",
                    message      = f"{len(new_videos)} video(s) uploaded by '{channel.channel_handle}'",
                    icon_path    = icon,
                )

            auto_dl = channel.auto_download if channel.auto_download is not None else True

            for video in new_videos:
                _transcode_args = None

                if auto_dl:
                    logger.info(f"Downloading '{video.title}' to '{self.config.VIDEOS_PREFIX_DIRECTORY}'")

                    downloaded = False
                    for attempt in range(1, self.DOWNLOAD_RETRIES + 1):
                        try:
                            output_path, publish_date, title, thumbnail_url, size, height, subtitles, chapters = self.download_video(
                                video_id         = video.video_id,
                                prefix_directory = self.config.VIDEOS_PREFIX_DIRECTORY,
                            )
                            downloaded = True
                            break
                        except Exception as error:
                            if attempt == self.DOWNLOAD_RETRIES:
                                logger.warning(f"Skipping '{video.title}' after {self.DOWNLOAD_RETRIES} failed attempts.")
                            else:
                                logger.warning(f"Download attempt {attempt}/{self.DOWNLOAD_RETRIES} failed: {error}. Retrying…")

                    if not downloaded:
                        continue

                    if ConfigManager().load_config().TRANSCODING_ENABLED and height and height > 360:
                        _transcode_args = (video.video_id, output_path, height)

                    record = Videos(
                        video_id       = video.video_id,
                        channel_handle = channel.channel_handle,
                        download_path  = output_path,
                        is_downloaded  = True,
                        is_watched     = False,
                        publish_date   = publish_date,
                        added_at       = date_in_gmt(),
                        thumbnail_url  = thumbnail_url,
                        title          = title,
                        size           = size,
                        variants       = [],
                        subtitles      = subtitles,
                        chapters       = chapters,
                    )
                else:
                    logger.info(f"Listing '{video.title}' (stream-only)")
                    try:
                        title, thumbnail_url, publish_date = self.fetch_video_metadata(video.video_id)
                    except Exception as exc:
                        logger.warning(f"Could not fetch metadata for '{video.video_id}': {exc}")
                        continue

                    record = Videos(
                        video_id       = video.video_id,
                        channel_handle = channel.channel_handle,
                        download_path  = "",
                        is_downloaded  = False,
                        is_watched     = False,
                        publish_date   = publish_date,
                        added_at       = date_in_gmt(),
                        thumbnail_url  = thumbnail_url,
                        title          = title,
                        size           = 0,
                    )

                self.database_handler.add_video_to_videos(video=record)
                self._flag_video_watched(
                    video_id          = video.video_id,
                    watched_videos_uid = channel.watched_videos_uid,
                )

                if _transcode_args:
                    t = threading.Thread(
                        target=self._transcode_video,
                        args=_transcode_args,
                        daemon=True,
                        name=f"transcode-{_transcode_args[0]}",
                    )
                    t.start()

            if new_videos:
                self.database_handler.update_video_starting_point_id(
                    channel_handle          = channel.channel_handle,
                    video_starting_point_id = new_videos[-1].video_id,
                )

            self.database_handler.update_channel_last_checked(channel.channel_handle)

    def search_channel(self, channel_handle: str) -> dict | None:
        url  = f"{self.YOUTUBE_BASE}/@{channel_handle}"
        opts = {"quiet": True, "extract_flat": True, "playlist_items": "0"}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            logger.warning(f"Channel lookup failed for '{channel_handle}': {exc}")
            return None

        if not info:
            return None

        thumbnails = info.get("thumbnails") or []
        avatar     = next((t["url"] for t in reversed(thumbnails) if t.get("url")), "")

        return {
            "channel_id":         info.get("channel_id", ""),
            "channel_name":       info.get("channel", ""),
            "channel_handle":     channel_handle,
            "avatar_url_default": avatar,
            "avatar_url_medium":  avatar,
            "avatar_url_high":    avatar,
            "subscriber_count":   str(info.get("channel_follower_count", 0)),
            "description":        info.get("description", ""),
        }

    def cleanup_watched_videos(self, days: int) -> int:
        videos = self.database_handler.get_stale_downloaded_videos(older_than_days=days)
        deleted = 0
        for video in videos:
            if video.download_path:
                try:
                    Path(video.download_path).unlink()
                    deleted += 1
                    logger.debug(f"Auto-deleted '{video.download_path}'")
                except FileNotFoundError:
                    pass
            self.database_handler.update_videos_values(
                video_id=video.video_id,
                values={"is_downloaded": False, "download_path": "", "size": 0},
            )
        if deleted:
            logger.info(f"Auto-deleted {deleted} watched video file(s) older than {days} day(s)")
        return deleted

    def get_channel_last_videos(self, channel_handle: str) -> list[_VideoEntry]:
        url  = f"{self.YOUTUBE_BASE}/@{channel_handle}/videos"
        opts = {
            "quiet":        True,
            "extract_flat": True,
            "playlistend":  50,
            "ignoreerrors": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            raise RuntimeError(
                f"Could not fetch video list for '@{channel_handle}': {exc}"
            ) from exc

        entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
        if not entries:
            raise RuntimeError(f"No videos found for '@{channel_handle}'")

        # yt-dlp returns newest-first; the watcher expects oldest-first
        entries.reverse()

        videos = [_VideoEntry(video_id=e["id"], title=e.get("title") or e["id"]) for e in entries]
        logger.debug(f"Fetched {len(videos)} videos for '@{channel_handle}'")
        return videos

    def download_video(self, video_id: str, prefix_directory: str) -> tuple:
        from nyt.src.api.download_state import update_progress

        def _hook(d: dict) -> None:
            status = d.get("status")
            title  = d.get("info_dict", {}).get("title", video_id)
            if status == "downloading":
                dl    = d.get("downloaded_bytes") or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                update_progress(video_id, {
                    "title":   title,
                    "percent": round(dl / total * 100, 1) if total else 0,
                    "speed":   d.get("speed") or 0,
                    "eta":     d.get("eta"),
                    "status":  "downloading",
                })
            elif status == "finished":
                update_progress(video_id, {"title": title, "percent": 100, "status": "finished"})
            elif status == "error":
                update_progress(video_id, {"title": title, "status": "error"})

        opts = {
            **self._ydl_base_opts,
            "outtmpl":           str(Path(prefix_directory) / "%(uploader)s" / "%(title)s.%(ext)s"),
            "writesubtitles":    True,
            "subtitleslangs":    ["all"],
            "subtitlesformat":   "vtt",
            "writeautomaticsub": False,
            "progress_hooks":    [_hook],
        }
        video_url = f"{self.YOUTUBE_BASE}/watch?v={video_id}"

        import time as _time
        _t0 = _time.monotonic()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info      = ydl.extract_info(video_url, download=False)
            ydl.download([video_url])
            file_name     = ydl.prepare_filename(info)
            title         = info.get("title")
            thumbnail_url = info.get("thumbnail")
            publish_date  = datetime.strptime(info["upload_date"], "%Y%m%d")
            size          = Path(file_name).stat().st_size
            height        = info.get("height") or 0
            elapsed       = _time.monotonic() - _t0
            size_mb       = size / 1024 ** 2
            logger.info(f"Downloaded '{title}' — {size_mb:.1f} MB, {height}p, {elapsed:.0f}s")

        # Collect subtitle VTT files written alongside the video
        subtitles = self._collect_subtitles(file_name)

        # Extract chapter metadata from yt-dlp info
        chapters = [
            {"start_time": c["start_time"], "end_time": c["end_time"], "title": c["title"]}
            for c in (info.get("chapters") or [])
        ]
        if chapters:
            logger.debug(f"Chapters: {len(chapters)} for '{title}'")

        return file_name, publish_date, title, thumbnail_url, size, height, subtitles, chapters

    def fetch_video_metadata(self, video_id: str) -> tuple[str, str, datetime]:
        url = f"{self.YOUTUBE_BASE}/watch?v={video_id}"
        with yt_dlp.YoutubeDL({"quiet": True, "format": "best[ext=mp4]/best"}) as ydl:
            info = ydl.extract_info(url, download=False)
        return (
            info.get("title", video_id),
            info.get("thumbnail", ""),
            datetime.strptime(info["upload_date"], "%Y%m%d"),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _collect_subtitles(self, video_path: str) -> list[dict]:
        """Return a list of {lang, path, label} for VTT subtitle files next to the video."""
        p    = Path(video_path)
        stem = p.stem
        subs = []
        try:
            for entry in p.parent.iterdir():
                name = entry.name
                if (
                    name != p.name
                    and name.startswith(stem + ".")
                    and name.endswith(".vtt")
                ):
                    lang = name[len(stem) + 1 : -4]  # strip "{stem}." prefix and ".vtt"
                    if lang:
                        subs.append({"lang": lang, "path": str(entry), "label": lang})
        except OSError:
            pass
        if subs:
            logger.debug(f"Found {len(subs)} subtitle(s) for '{stem}': {[s['lang'] for s in subs]}")
        return subs

    def _download_avatar(self, channel_handle: str, url: str) -> None:
        dest = Path(self.config.AVATARS_DIRECTORY) / f"{channel_handle}.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            dest.write_bytes(res.content)
            logger.debug(f"Cached avatar for '{channel_handle}' → {dest}")
        except Exception as exc:
            logger.warning(f"Could not cache avatar for '{channel_handle}': {exc}")

    def _flag_video_watched(self, video_id: str, watched_videos_uid: str) -> None:
        row = self.database_handler.get_watched_videos_row(watched_videos_uid=watched_videos_uid)
        self.database_handler.add_video_id_to_watched_videos(
            video_id           = video_id,
            watched_videos_uid = watched_videos_uid,
            watched_videos     = row.watched_videos,
        )

    def _transcode_video(self, video_id: str, source_path: str, source_height: int) -> None:
        from nyt.src.api.download_state import update_progress

        TARGETS = [720, 480, 360]
        targets = [h for h in TARGETS if h < source_height]
        if not targets:
            return

        logger.info(f"Transcoding '{video_id}' → {', '.join(f'{h}p' for h in targets)} (source: {source_height}p)")

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    source_path,
                ],
                capture_output=True, text=True, timeout=30,
            )
            total_seconds = float(result.stdout.strip())
        except Exception as exc:
            logger.warning(f"ffprobe failed for '{video_id}': {exc}")
            return

        source   = Path(source_path)
        variants = list(self.database_handler.get_video_from_videos(video_id).variants or [])

        for height in targets:
            out_path     = source.parent / f"{source.stem}_{height}p.mp4"
            progress_key = f"{video_id}_{height}p"

            update_progress(progress_key, {
                "title":    f"{height}p — {source.stem[:40]}",
                "percent":  0,
                "status":   "transcoding",
                "video_id": video_id,
            })

            try:
                proc = subprocess.Popen(
                    [
                        "ffmpeg", "-y",
                        "-i",       source_path,
                        "-vf",      f"scale=-2:{height}",
                        "-c:v",     "libx264",
                        "-crf",     "23",
                        "-preset",  "fast",
                        "-c:a",     "aac",
                        "-b:a",     "128k",
                        "-progress", "pipe:1",
                        "-nostats",
                        str(out_path),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )

                for line in proc.stdout:
                    line = line.strip()
                    if line.startswith("out_time_us="):
                        try:
                            us      = int(line.split("=", 1)[1])
                            elapsed = us / 1_000_000
                            pct     = min(round(elapsed / total_seconds * 100, 1), 99)
                            update_progress(progress_key, {
                                "title":    f"{height}p — {source.stem[:40]}",
                                "percent":  pct,
                                "status":   "transcoding",
                                "video_id": video_id,
                            })
                        except (ValueError, ZeroDivisionError):
                            pass

                proc.wait()

                if proc.returncode == 0 and out_path.exists():
                    size = out_path.stat().st_size
                    variants.append({
                        "height": height,
                        "label":  f"{height}p",
                        "path":   str(out_path),
                        "size":   size,
                    })
                    self.database_handler.update_videos_values(
                        video_id=video_id,
                        values={"variants": variants},
                    )
                    update_progress(progress_key, {
                        "title":    f"{height}p — {source.stem[:40]}",
                        "percent":  100,
                        "status":   "finished",
                        "video_id": video_id,
                    })
                    logger.info(f"Transcoded '{video_id}' → {height}p at '{out_path}'")
                else:
                    update_progress(progress_key, {
                        "title":    f"{height}p — {source.stem[:40]}",
                        "status":   "error",
                        "video_id": video_id,
                    })
                    logger.warning(f"FFmpeg exited with error for '{video_id}' at {height}p")

            except Exception as exc:
                update_progress(progress_key, {
                    "title":    f"{height}p — {source.stem[:40]}",
                    "status":   "error",
                    "video_id": video_id,
                })
                logger.warning(f"Transcoding error for '{video_id}' at {height}p: {exc}")
