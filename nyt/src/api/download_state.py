import time

# {video_id: {title, percent, speed, eta, status, _ts}}
_progress: dict[str, dict] = {}


def update_progress(video_id: str, data: dict) -> None:
    _progress[video_id] = {**data, "_ts": time.monotonic()}


def get_all_progress() -> dict:
    now = time.monotonic()
    expired = [
        vid for vid, d in _progress.items()
        if d.get("status") in ("finished", "error") and now - d.get("_ts", now) > 10
    ]
    for vid in expired:
        del _progress[vid]
    return {vid: {k: v for k, v in d.items() if k != "_ts"} for vid, d in _progress.items()}
