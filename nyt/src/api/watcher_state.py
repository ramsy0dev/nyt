from dataclasses import dataclass
from datetime import datetime


@dataclass
class WatcherState:
    running:  bool            = False
    last_run: datetime | None = None
    next_run: datetime | None = None
    error:    str | None      = None


watcher_state = WatcherState()
