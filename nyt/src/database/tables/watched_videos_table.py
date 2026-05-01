from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WatchedVideos:
    watched_videos_uid: str | None = None
    watched_videos:     dict = field(default_factory=lambda: {"ids": []})
    updated_at:         datetime | None = None
    created_at:         datetime | None = None
