import yt_dlp
import requests

from pathlib import Path
from loguru import logger
from datetime import datetime

from pytubefix import YouTube, Channel

from nyt import constant
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
                if auto_dl:
                    logger.info(f"Downloading '{video.title}' to '{self.config.VIDEOS_PREFIX_DIRECTORY}'")

                    downloaded = False
                    for attempt in range(1, self.DOWNLOAD_RETRIES + 1):
                        try:
                            output_path, publish_date, title, thumbnail_url, size = self.download_video(
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

    def get_channel_last_videos(self, channel_handle: str) -> list[YouTube]:
        url     = f"{self.YOUTUBE_BASE}/@{channel_handle}"
        channel = Channel(url)

        try:
            contents = (
                channel.initial_data
                ["contents"]
                ["twoColumnBrowseResultsRenderer"]
                ["tabs"][1]
                ["tabRenderer"]
                ["content"]
                ["richGridRenderer"]
                ["contents"]
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Could not parse YouTube page for '@{channel_handle}'. "
                "YouTube may have changed their page structure."
            ) from exc

        videos: list[YouTube] = []
        for block in contents[: len(contents) // 2]:
            try:
                renderer = block["richItemRenderer"]["content"]["videoRenderer"]
                video_id = renderer["videoId"]
                title    = renderer["title"]["runs"][0]["text"]
            except (KeyError, IndexError):
                continue
            videos.append(YouTube(f"{self.YOUTUBE_BASE}/watch?v={video_id}"))
            logger.debug(f"Found video {video_id!r}: {title!r}")

        return videos[::-1]  # oldest first

    def download_video(self, video_id: str, prefix_directory: str) -> tuple:
        opts = {
            **self._ydl_base_opts,
            "outtmpl": str(Path(prefix_directory) / "%(uploader)s" / "%(title)s.%(ext)s"),
        }
        video_url = f"{self.YOUTUBE_BASE}/watch?v={video_id}"

        with yt_dlp.YoutubeDL(opts) as ydl:
            info      = ydl.extract_info(video_url, download=False)
            ydl.download([video_url])
            file_name     = ydl.prepare_filename(info)
            title         = info.get("title")
            thumbnail_url = info.get("thumbnail")
            publish_date  = datetime.strptime(info["upload_date"], "%Y%m%d")
            size          = Path(file_name).stat().st_size
            logger.debug(f"Downloaded: {file_name!r}, title={title!r}")

        return file_name, publish_date, title, thumbnail_url, size

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
