import asyncio
import hashlib
import json
import os
import pathlib
import secrets
import subprocess
import sys
import threading
import time
import requests as _requests
from loguru import logger

from fastapi import FastAPI, Header, Request, Depends
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    StreamingResponse,
    RedirectResponse,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nyt import constant
from nyt.src.api.classes import classes
from nyt.src.api import constant as api_constant
from nyt.src.api.auth.auth import auth_manager, require_auth
from nyt.src.api.watcher_state import watcher_state
from nyt.src.config import ConfigManager
from nyt.src.utils import date_in_gmt, parse_range_header

STATIC_DIR = pathlib.Path(__file__).parent.parent.parent / "static"
ROOT = api_constant.ROOT_API_ROUTE

# ── App ───────────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(app: FastAPI):
    config = ConfigManager().load_config()
    if config.AUTO_UPDATE_ENABLED:
        def _startup_update():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade",
                    f"git+https://github.com/{constant.AUTHOR}/{constant.PACKAGE}.git"],
                    capture_output=True, text=True, timeout=300,
                )
                if result.returncode == 0:
                    logger.info("Startup auto-update: already up-to-date or updated successfully")
                else:
                    logger.warning(f"Startup auto-update failed:\n{result.stderr}")
            except Exception as exc:
                logger.warning(f"Startup auto-update exception: {exc}")

        threading.Thread(target=_startup_update, daemon=True).start()
    yield


api = FastAPI(lifespan=_lifespan)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Favicon ───────────────────────────────────────────────────────────────────

@api.get("/favicon.ico", include_in_schema=False)
async def favicon_route():
    return FileResponse(STATIC_DIR / "logo.svg", media_type="image/svg+xml")


api.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth_redirect(request: Request) -> RedirectResponse | None:
    if not auth_manager.is_auth_enabled():
        return None
    token = request.cookies.get("nyt_session")
    if not token or not auth_manager.validate_session(token):
        return RedirectResponse(url="/login")
    return None


# ── Frontend HTML routes ──────────────────────────────────────────────────────

@api.get("/", include_in_schema=False)
async def home_route(request: Request):
    redir = _auth_redirect(request)
    return redir or FileResponse(STATIC_DIR / "index.html")


@api.get("/watch/{video_id}", include_in_schema=False)
async def watch_route(video_id: str, request: Request):
    redir = _auth_redirect(request)
    return redir or FileResponse(STATIC_DIR / "watch.html")


@api.get("/channels", include_in_schema=False)
async def channels_page_route(request: Request):
    redir = _auth_redirect(request)
    return redir or FileResponse(STATIC_DIR / "channels.html")


@api.get("/login", include_in_schema=False)
async def login_route():
    if not auth_manager.is_auth_enabled():
        return RedirectResponse(url="/")
    return FileResponse(STATIC_DIR / "login.html")


@api.get("/settings", include_in_schema=False)
async def settings_page_route(request: Request):
    redir = _auth_redirect(request)
    return redir or FileResponse(STATIC_DIR / "settings.html")


# ── Auth API routes ───────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    username: str
    password: str


@api.post(f"{ROOT}/auth/login", response_class=JSONResponse)
async def auth_login_route(body: LoginBody):
    config = ConfigManager().load_config()
    if not config.ADMIN_USERNAME:
        token = auth_manager.create_session()
        resp  = JSONResponse({"ok": True})
        resp.set_cookie("nyt_session", token, httponly=True, samesite="strict", max_age=86400 * 30)
        return resp

    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        body.password.encode(),
        config.ADMIN_SALT.encode(),
        200_000,
    ).hex()

    if body.username != config.ADMIN_USERNAME or pw_hash != config.ADMIN_PASSWORD_HASH:
        logger.warning(f"Failed login attempt for user '{body.username}'")
        return JSONResponse({"ok": False, "message": "Invalid credentials"}, status_code=401)

    logger.info(f"User '{body.username}' logged in")
    token = auth_manager.create_session()
    resp  = JSONResponse({"ok": True})
    resp.set_cookie("nyt_session", token, httponly=True, samesite="strict", max_age=86400 * 30)
    return resp


@api.post(f"{ROOT}/auth/refresh", response_class=JSONResponse)
async def auth_refresh_route(request: Request):
    if not auth_manager.is_auth_enabled():
        return JSONResponse({"ok": True, "refreshed": False})
    token = request.cookies.get("nyt_session")
    if not token or not auth_manager.validate_session(token):
        return JSONResponse({"ok": False}, status_code=401)
    new_token = auth_manager.create_session()
    resp = JSONResponse({"ok": True, "refreshed": True})
    resp.set_cookie("nyt_session", new_token, httponly=True, samesite="strict", max_age=86400 * 30)
    return resp


@api.post(f"{ROOT}/auth/logout", response_class=JSONResponse)
async def auth_logout_route(request: Request):
    token = request.cookies.get("nyt_session")
    if token:
        auth_manager.revoke_session(token)
        logger.info("User logged out")
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("nyt_session")
    return resp


@api.get(f"{ROOT}/auth/status", response_class=JSONResponse)
async def auth_status_route(request: Request):
    enabled = auth_manager.is_auth_enabled()
    token   = request.cookies.get("nyt_session")
    logged_in = bool(token and auth_manager.validate_session(token))
    return JSONResponse({"auth_enabled": enabled, "logged_in": logged_in})


# ── Watcher status ────────────────────────────────────────────────────────────

@api.get(f"{ROOT}/watcher/status", response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def watcher_status_route():
    return JSONResponse({
        "status_code": 200,
        "watcher": {
            "running":  watcher_state.running,
            "last_run": watcher_state.last_run.isoformat() if watcher_state.last_run else None,
            "next_run": watcher_state.next_run.isoformat() if watcher_state.next_run else None,
            "error":    watcher_state.error,
        },
    })


# ── Download progress (SSE) ───────────────────────────────────────────────────

@api.get(f"{ROOT}/downloads/progress")
async def download_progress_sse(request: Request):
    from nyt.src.api.download_state import get_all_progress

    async def _stream():
        while True:
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(get_all_progress())}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


# ── API root ──────────────────────────────────────────────────────────────────

@api.get(ROOT, status_code=200, response_class=JSONResponse)
async def root_route():
    return JSONResponse([{"code": 200}])


# ── Channel routes ────────────────────────────────────────────────────────────

@api.get(f"{ROOT}/channels", status_code=200, response_class=JSONResponse)
async def root_channels_route():
    return JSONResponse({"code": 200, "message": "root channels route"})


@api.get(f"{ROOT}/channels/list", status_code=200, response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def list_channels_route():
    return JSONResponse({
        "status_code": 200,
        "tracked_channels": classes.tracked_channels.list_tracked_channels(),
    })


@api.get(f"{ROOT}/channels/search", status_code=200, response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def search_channels_route(handle: str):
    result = classes.tracked_channels.search_channel(handle)
    if result is None:
        return JSONResponse({"status_code": 404, "result": None}, status_code=404)
    return JSONResponse({"status_code": 200, "result": result})


@api.post(f"{ROOT}/channels/add", status_code=200, response_class=JSONResponse,
          dependencies=[Depends(require_auth)])
async def add_channels_route(channel_handle: str):
    return JSONResponse(
        classes.tracked_channels.add_channel_to_tracked_list(channel_handle=channel_handle)
    )


@api.put(f"{ROOT}/channels/{{channel_handle}}/delay", status_code=200, response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def set_channel_delay_route(channel_handle: str, body: dict):
    delay = body.get("delay_minutes")
    classes.database_handler.update_channel_delay(
        channel_handle=channel_handle,
        delay_minutes=int(delay) if delay is not None else None,
    )
    return JSONResponse({"status_code": 200})


@api.put(f"{ROOT}/channels/{{channel_handle}}/auto-download", status_code=200, response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def set_channel_auto_download_route(channel_handle: str, body: dict):
    classes.database_handler.update_channel_auto_download(
        channel_handle=channel_handle,
        auto_download=bool(body.get("auto_download", True)),
    )
    return JSONResponse({"status_code": 200})


@api.delete(f"{ROOT}/channels/delete/{{channel_handle}}", status_code=200, response_class=JSONResponse,
            dependencies=[Depends(require_auth)])
async def delete_channels_route(channel_handle: str):
    return JSONResponse(
        classes.tracked_channels.remove_channel_from_tracked_list(channel_handle=channel_handle)
    )


@api.get(f"{ROOT}/channels/{{channel_handle}}/avatar", include_in_schema=False)
async def channel_avatar_route(channel_handle: str):
    config = ConfigManager().load_config()
    avatars_dir = pathlib.Path(config.AVATARS_DIRECTORY)
    avatars_dir.mkdir(parents=True, exist_ok=True)
    cached = avatars_dir / f"{channel_handle}.jpg"

    if not cached.exists():
        channel = classes.database_handler.get_channel_row(channel_handle=channel_handle)
        if channel is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        url = channel.channel_avatar_url_high or channel.channel_avatar_url_medium or channel.channel_avatar_url_default
        if not url:
            return JSONResponse({"detail": "no avatar url"}, status_code=404)
        try:
            res = _requests.get(url, timeout=15)
            res.raise_for_status()
            cached.write_bytes(res.content)
        except Exception:
            return JSONResponse({"detail": "fetch failed"}, status_code=502)

    return FileResponse(str(cached), media_type="image/jpeg")


# ── Video routes ──────────────────────────────────────────────────────────────

@api.get(f"{ROOT}/videos", status_code=200, response_class=JSONResponse)
async def videos_root_route():
    return JSONResponse({"status_code": 200, "message": "videos root route"})


@api.get(f"{ROOT}/videos/list/", status_code=200, response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
def list_videos_route():
    return JSONResponse({
        "status_code": 200,
        "videos_info": classes.videos_handler.list_videos(),
    })


@api.post(f"{ROOT}/videos/{{video_id}}/watched", status_code=200, response_class=JSONResponse,
          dependencies=[Depends(require_auth)])
async def mark_video_watched_route(video_id: str):
    classes.database_handler.update_videos_values(
        video_id=video_id,
        values={"is_watched": True, "timestamp": date_in_gmt()},
    )
    logger.debug(f"Marked '{video_id}' as watched")
    return JSONResponse({"status_code": 200})


@api.post(f"{ROOT}/videos/{{video_id}}/unwatched", status_code=200, response_class=JSONResponse,
          dependencies=[Depends(require_auth)])
async def mark_video_unwatched_route(video_id: str):
    classes.database_handler.update_videos_values(
        video_id=video_id,
        values={"is_watched": False, "timestamp": date_in_gmt()},
    )
    logger.debug(f"Marked '{video_id}' as unwatched")
    return JSONResponse({"status_code": 200})


@api.post(f"{ROOT}/videos/{{video_id}}/download", status_code=202, response_class=JSONResponse,
          dependencies=[Depends(require_auth)])
async def download_video_route(video_id: str):
    video = classes.database_handler.get_video_from_videos(video_id=video_id)
    if not video:
        return JSONResponse({"status_code": 404, "message": "Not found"}, status_code=404)
    if video.is_downloaded:
        return JSONResponse({"status_code": 409, "message": "Already downloaded"}, status_code=409)

    config = ConfigManager().load_config()

    def _do_download():
        try:
            output_path, publish_date, title, thumbnail_url, size, height, subtitles, chapters = \
                classes.nyt.download_video(
                    video_id=video_id,
                    prefix_directory=config.VIDEOS_PREFIX_DIRECTORY,
                )
            classes.database_handler.update_videos_values(video_id=video_id, values={
                "download_path": output_path,
                "is_downloaded": True,
                "publish_date":  publish_date,
                "title":         title,
                "thumbnail_url": thumbnail_url,
                "size":          size,
                "subtitles":     subtitles,
                "chapters":      chapters,
                "variants":      [],
            })
            if ConfigManager().load_config().TRANSCODING_ENABLED and height and height > 360:
                classes.nyt._transcode_video(video_id, output_path, height)
        except Exception as exc:
            from nyt.src.api.download_state import update_progress
            update_progress(video_id, {"title": video.title or video_id, "status": "error"})
            logger.warning(f"Manual download failed for '{video_id}': {exc}")

    logger.info(f"Download queued for '{video.title or video_id}'")
    threading.Thread(target=_do_download, daemon=True).start()
    return JSONResponse({"status_code": 202, "message": "Download started"})


def _delete_video_files(video) -> None:
    for path in [video.download_path] + \
                [v.get("path", "") for v in (video.variants or [])] + \
                [s.get("path", "") for s in (video.subtitles or [])]:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass


@api.delete(f"{ROOT}/videos/{{video_id}}/file", status_code=200, response_class=JSONResponse,
            dependencies=[Depends(require_auth)])
async def delete_video_file_route(video_id: str):
    video = classes.database_handler.get_video_from_videos(video_id=video_id)
    if not video:
        return JSONResponse({"status_code": 404, "message": "Not found"}, status_code=404)
    if not video.is_downloaded:
        return JSONResponse({"status_code": 409, "message": "Not downloaded"}, status_code=409)
    _delete_video_files(video)
    classes.database_handler.update_videos_values(video_id=video_id, values={
        "is_downloaded": False,
        "download_path": "",
        "size":          0,
        "variants":      [],
        "subtitles":     [],
    })
    logger.info(f"Deleted local file for '{video.title or video_id}'")
    return JSONResponse({"status_code": 200})


@api.delete(f"{ROOT}/videos/{{video_id}}", status_code=200, response_class=JSONResponse,
            dependencies=[Depends(require_auth)])
async def delete_video_route(video_id: str):
    video = classes.database_handler.get_video_from_videos(video_id=video_id)
    if not video:
        return JSONResponse({"status_code": 404, "message": "Not found"}, status_code=404)
    if video.is_downloaded:
        _delete_video_files(video)
    classes.database_handler.delete_video_row(video_id=video_id)
    logger.info(f"Removed video '{video.title or video_id}' from library")
    return JSONResponse({"status_code": 200})


@api.get(f"{ROOT}/videos/{{video_id}}/status", status_code=200, response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def video_status_route(video_id: str):
    is_present = classes.database_handler.get_video_from_videos(video_id=video_id) is not None
    return JSONResponse({
        "status_code": 200,
        "video_status": {"is_present": is_present},
    })


@api.get(f"{ROOT}/videos/{{video_id}}/metadata", response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def get_video_metadata_route(video_id: str):
    video = classes.database_handler.get_video_from_videos(video_id=video_id)
    if not video:
        return JSONResponse({"detail": "not found"}, status_code=404)
    return JSONResponse({
        "status_code": 200,
        "subtitles":   video.subtitles or [],
        "chapters":    video.chapters  or [],
    })


@api.get(f"{ROOT}/videos/{{video_id}}/subtitles/{{lang}}", include_in_schema=False)
async def get_subtitle_route(video_id: str, lang: str):
    import os
    video = classes.database_handler.get_video_from_videos(video_id=video_id)
    if not video:
        return JSONResponse({"detail": "not found"}, status_code=404)
    for sub in (video.subtitles or []):
        if sub.get("lang") == lang:
            path = sub.get("path", "")
            if path and os.path.exists(path):
                return FileResponse(path, media_type="text/vtt")
    return JSONResponse({"detail": "subtitle not found"}, status_code=404)


@api.get(f"{ROOT}/videos/{{video_id}}/formats", response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def get_video_formats_route(video_id: str):
    config = ConfigManager().load_config()
    video  = classes.database_handler.get_video_from_videos(video_id=video_id)

    if video and video.is_downloaded and video.download_path:
        if not config.TRANSCODING_ENABLED:
            return JSONResponse({"status_code": 403, "message": "Transcoding is disabled"}, status_code=403)
        formats = classes.videos_handler.get_local_formats(video_id)
        return JSONResponse({"status_code": 200, "formats": formats, "is_local": True})

    if not config.QUALITY_SELECTION_ENABLED:
        return JSONResponse({"status_code": 403, "message": "Quality selection is disabled"}, status_code=403)

    formats = classes.videos_handler.get_formats(video_id)
    return JSONResponse({"status_code": 200, "formats": formats, "is_local": False})


@api.get(f"{ROOT}/videos/{{video_id}}", status_code=200, response_class=StreamingResponse)
async def get_videos_route(video_id: str, range_header: str = Header(None), format_id: str | None = None):
    if range_header:
        start, end = parse_range_header(range_header)
    else:
        start, end = 0, 0

    media_type = classes.videos_handler.get_video_mime(video_id)

    return StreamingResponse(
        classes.videos_handler.stream_video(video_id=video_id, start=start, end=end, format_id=format_id),
        media_type=media_type,
    )


# ── Settings routes ───────────────────────────────────────────────────────────

@api.get(f"{ROOT}/settings", response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def get_settings_route():
    config     = ConfigManager().load_config()
    used_bytes = classes.database_handler.get_storage_used_bytes()
    return JSONResponse({
        "status_code": 200,
        "settings": {
            "watch_delay_minutes":       config.WATCH_DELAY_MINUTES,
            "videos_directory":          config.VIDEOS_PREFIX_DIRECTORY,
            "storage_limit_gb":          config.STORAGE_LIMIT_GB,
            "storage_used_bytes":        used_bytes,
            "auth_enabled":              bool(config.ADMIN_USERNAME),
            "admin_username":            config.ADMIN_USERNAME,
            "quality_selection_enabled": config.QUALITY_SELECTION_ENABLED,
            "transcoding_enabled":       config.TRANSCODING_ENABLED,
            "auto_delete_watched_days":  config.AUTO_DELETE_WATCHED_DAYS,
            "auto_update_enabled":       config.AUTO_UPDATE_ENABLED,
        },
    })


class GeneralSettingsBody(BaseModel):
    watch_delay_minutes: int
    videos_directory: str
    storage_limit_gb: float | None = None
    quality_selection_enabled: bool | None = None
    transcoding_enabled: bool | None = None
    auto_delete_watched_days: int | None = None
    auto_update_enabled: bool | None = None


@api.put(f"{ROOT}/settings/general", response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def update_general_settings_route(body: GeneralSettingsBody):
    if body.watch_delay_minutes < 1:
        return JSONResponse({"ok": False, "message": "Interval must be at least 1 minute"}, status_code=422)
    ConfigManager().save_settings(
        watch_delay_minutes=body.watch_delay_minutes,
        videos_directory=body.videos_directory.strip() or None,
        storage_limit_gb=max(0.0, body.storage_limit_gb) if body.storage_limit_gb is not None else None,
        quality_selection_enabled=body.quality_selection_enabled,
        transcoding_enabled=body.transcoding_enabled,
        auto_delete_watched_days=body.auto_delete_watched_days,
        auto_update_enabled=body.auto_update_enabled,
    )
    logger.info("Settings updated")
    return JSONResponse({"ok": True})


class AuthSettingsBody(BaseModel):
    username: str
    current_password: str = ""
    new_password: str


@api.put(f"{ROOT}/settings/auth", response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def update_auth_settings_route(body: AuthSettingsBody):
    config = ConfigManager().load_config()
    if config.ADMIN_USERNAME:
        pw_hash = hashlib.pbkdf2_hmac(
            "sha256", body.current_password.encode(), config.ADMIN_SALT.encode(), 200_000
        ).hex()
        if pw_hash != config.ADMIN_PASSWORD_HASH:
            return JSONResponse({"ok": False, "message": "Current password is incorrect"}, status_code=401)
    if not body.username.strip():
        return JSONResponse({"ok": False, "message": "Username cannot be empty"}, status_code=422)
    if not body.new_password:
        return JSONResponse({"ok": False, "message": "Password cannot be empty"}, status_code=422)
    salt    = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", body.new_password.encode(), salt.encode(), 200_000).hex()
    ConfigManager().save_auth(body.username.strip(), pw_hash, salt)
    logger.info(f"Auth credentials updated for user '{body.username.strip()}'")
    return JSONResponse({"ok": True})


class DisableAuthBody(BaseModel):
    current_password: str


@api.post(f"{ROOT}/settings/auth/disable", response_class=JSONResponse,
          dependencies=[Depends(require_auth)])
async def disable_auth_route(body: DisableAuthBody):
    config = ConfigManager().load_config()
    if not config.ADMIN_USERNAME:
        return JSONResponse({"ok": True})
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", body.current_password.encode(), config.ADMIN_SALT.encode(), 200_000
    ).hex()
    if pw_hash != config.ADMIN_PASSWORD_HASH:
        return JSONResponse({"ok": False, "message": "Password is incorrect"}, status_code=401)
    ConfigManager().save_auth("", "", "")
    logger.info("Authentication disabled")
    return JSONResponse({"ok": True})


# ── Version / update check ────────────────────────────────────────────────────

_GITHUB_RELEASES = f"https://api.github.com/repos/{constant.AUTHOR}/nyt/releases/latest"
_version_cache: dict = {"tag": None, "url": None, "fetched_at": 0.0}
_VERSION_TTL = 3600  # re-check GitHub at most once per hour


@api.get(f"{ROOT}/version", response_class=JSONResponse,
         dependencies=[Depends(require_auth)])
async def version_route():
    now = time.monotonic()
    if now - _version_cache["fetched_at"] > _VERSION_TTL:
        try:
            res = _requests.get(
                _GITHUB_RELEASES,
                timeout=5,
                headers={"Accept": "application/vnd.github+json"},
            )
            res.raise_for_status()
            body = res.json()
            _version_cache["tag"] = body.get("tag_name")
            _version_cache["url"] = body.get("html_url")
        except Exception:
            pass  # keep stale cache; don't overwrite fetched_at so we retry next request
        else:
            _version_cache["fetched_at"] = now

    latest  = _version_cache["tag"]
    current = constant.VERSION
    config  = ConfigManager().load_config()
    if latest and latest != current:
        logger.info(f"Update available: {current} → {latest}")
    return JSONResponse({
        "current_version":    current,
        "latest_version":     latest,
        "update_available":   bool(latest and latest != current),
        "release_url":        _version_cache["url"],
        "auto_update_enabled": config.AUTO_UPDATE_ENABLED,
    })


_update_state: dict = {"running": False, "last_result": None}


@api.post(f"{ROOT}/update", response_class=JSONResponse,
          dependencies=[Depends(require_auth)])
async def trigger_update_route():
    if _update_state["running"]:
        return JSONResponse({"ok": False, "message": "Update already in progress"}, status_code=409)

    def _do_update():
        _update_state["running"] = True
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade",
                    f"git+https://github.com/{constant.AUTHOR}/{constant.PACKAGE}.git"],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                _update_state["last_result"] = "success"
                logger.info("Auto-update completed successfully")
            else:
                _update_state["last_result"] = "error"
                logger.warning(f"Auto-update failed:\n{result.stderr}")
        except Exception as exc:
            _update_state["last_result"] = "error"
            logger.warning(f"Auto-update exception: {exc}")
        finally:
            _update_state["running"] = False

    threading.Thread(target=_do_update, daemon=True).start()
    return JSONResponse({"ok": True, "message": "Update started — restart nyt once it completes"})
