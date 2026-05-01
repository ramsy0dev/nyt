import hashlib
import pathlib
import secrets
import requests as _requests

from fastapi import FastAPI, Header, Request, Depends, Response
from fastapi.responses import (
    FileResponse,
    ORJSONResponse,
    StreamingResponse,
    RedirectResponse,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nyt.src.api.classes import classes
from nyt.src.api import constant as api_constant
from nyt.src.api.auth.auth import auth_manager, require_auth
from nyt.src.api.watcher_state import watcher_state
from nyt.src.config import ConfigManager
from nyt.src.utils import date_in_gmt, parse_range_header

STATIC_DIR = pathlib.Path(__file__).parent.parent.parent / "static"
ROOT = api_constant.ROOT_API_ROUTE

# ── App ───────────────────────────────────────────────────────────────────────

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth_redirect(request: Request) -> RedirectResponse | None:
    """Return a redirect if auth is enabled and the session cookie is invalid."""
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


@api.post(f"{ROOT}/auth/login", response_class=ORJSONResponse)
async def auth_login_route(body: LoginBody, response: Response):
    config = ConfigManager().load_config()
    if not config.ADMIN_USERNAME:
        token = auth_manager.create_session()
        response.set_cookie("nyt_session", token, httponly=True, samesite="strict", max_age=86400 * 30)
        return ORJSONResponse({"ok": True})

    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        body.password.encode(),
        config.ADMIN_SALT.encode(),
        200_000,
    ).hex()

    if body.username != config.ADMIN_USERNAME or pw_hash != config.ADMIN_PASSWORD_HASH:
        return ORJSONResponse({"ok": False, "message": "Invalid credentials"}, status_code=401)

    token = auth_manager.create_session()
    response.set_cookie("nyt_session", token, httponly=True, samesite="strict", max_age=86400 * 30)
    return ORJSONResponse({"ok": True})


@api.post(f"{ROOT}/auth/logout", response_class=ORJSONResponse)
async def auth_logout_route(request: Request, response: Response):
    token = request.cookies.get("nyt_session")
    if token:
        auth_manager.revoke_session(token)
    response.delete_cookie("nyt_session")
    return ORJSONResponse({"ok": True})


@api.get(f"{ROOT}/auth/status", response_class=ORJSONResponse)
async def auth_status_route(request: Request):
    enabled = auth_manager.is_auth_enabled()
    token   = request.cookies.get("nyt_session")
    logged_in = bool(token and auth_manager.validate_session(token))
    return ORJSONResponse({"auth_enabled": enabled, "logged_in": logged_in})


# ── Watcher status ────────────────────────────────────────────────────────────

@api.get(f"{ROOT}/watcher/status", response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def watcher_status_route():
    return ORJSONResponse({
        "status_code": 200,
        "watcher": {
            "running":  watcher_state.running,
            "last_run": watcher_state.last_run.isoformat() if watcher_state.last_run else None,
            "next_run": watcher_state.next_run.isoformat() if watcher_state.next_run else None,
            "error":    watcher_state.error,
        },
    })


# ── API root ──────────────────────────────────────────────────────────────────

@api.get(ROOT, status_code=200, response_class=ORJSONResponse)
async def root_route():
    return ORJSONResponse([{"code": 200}])


# ── Channel routes ────────────────────────────────────────────────────────────

@api.get(f"{ROOT}/channels", status_code=200, response_class=ORJSONResponse)
async def root_channels_route():
    return ORJSONResponse({"code": 200, "message": "root channels route"})


@api.get(f"{ROOT}/channels/list", status_code=200, response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def list_channels_route():
    return ORJSONResponse({
        "status_code": 200,
        "tracked_channels": classes.tracked_channels.list_tracked_channels(),
    })


@api.get(f"{ROOT}/channels/search", status_code=200, response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def search_channels_route(handle: str):
    result = classes.tracked_channels.search_channel(handle)
    if result is None:
        return ORJSONResponse({"status_code": 404, "result": None}, status_code=404)
    return ORJSONResponse({"status_code": 200, "result": result})


@api.post(f"{ROOT}/channels/add", status_code=200, response_class=ORJSONResponse,
          dependencies=[Depends(require_auth)])
async def add_channels_route(channel_handle: str):
    return ORJSONResponse(
        classes.tracked_channels.add_channel_to_tracked_list(channel_handle=channel_handle)
    )


@api.put(f"{ROOT}/channels/{{channel_handle}}/delay", status_code=200, response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def set_channel_delay_route(channel_handle: str, body: dict):
    delay = body.get("delay_minutes")
    classes.database_handler.update_channel_delay(
        channel_handle=channel_handle,
        delay_minutes=int(delay) if delay is not None else None,
    )
    return ORJSONResponse({"status_code": 200})


@api.put(f"{ROOT}/channels/{{channel_handle}}/auto-download", status_code=200, response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def set_channel_auto_download_route(channel_handle: str, body: dict):
    classes.database_handler.update_channel_auto_download(
        channel_handle=channel_handle,
        auto_download=bool(body.get("auto_download", True)),
    )
    return ORJSONResponse({"status_code": 200})


@api.delete(f"{ROOT}/channels/delete/{{channel_handle}}", status_code=200, response_class=ORJSONResponse,
            dependencies=[Depends(require_auth)])
async def delete_channels_route(channel_handle: str):
    return ORJSONResponse(
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
            return ORJSONResponse({"detail": "not found"}, status_code=404)
        url = channel.channel_avatar_url_high or channel.channel_avatar_url_medium or channel.channel_avatar_url_default
        if not url:
            return ORJSONResponse({"detail": "no avatar url"}, status_code=404)
        try:
            res = _requests.get(url, timeout=15)
            res.raise_for_status()
            cached.write_bytes(res.content)
        except Exception:
            return ORJSONResponse({"detail": "fetch failed"}, status_code=502)

    return FileResponse(str(cached), media_type="image/jpeg")


# ── Video routes ──────────────────────────────────────────────────────────────

@api.get(f"{ROOT}/videos", status_code=200, response_class=ORJSONResponse)
async def videos_root_route():
    return ORJSONResponse({"status_code": 200, "message": "videos root route"})


@api.get(f"{ROOT}/videos/list/", status_code=200, response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
def list_videos_route():
    return ORJSONResponse({
        "status_code": 200,
        "videos_info": classes.videos_handler.list_videos(),
    })


@api.post(f"{ROOT}/videos/{{video_id}}/watched", status_code=200, response_class=ORJSONResponse,
          dependencies=[Depends(require_auth)])
async def mark_video_watched_route(video_id: str):
    classes.database_handler.update_videos_values(
        video_id=video_id,
        values={"is_watched": True, "timestamp": date_in_gmt()},
    )
    return ORJSONResponse({"status_code": 200})


@api.get(f"{ROOT}/videos/{{video_id}}/status", status_code=200, response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def video_status_route(video_id: str):
    is_present = classes.database_handler.get_video_from_videos(video_id=video_id) is not None
    return ORJSONResponse({
        "status_code": 200,
        "video_status": {"is_present": is_present},
    })


@api.get(f"{ROOT}/videos/{{video_id}}", status_code=200, response_class=StreamingResponse)
async def get_videos_route(video_id: str, range_header: str = Header(None)):
    if range_header:
        start, end = parse_range_header(range_header)
    else:
        start, end = 0, 0

    media_type = classes.videos_handler.get_video_mime(video_id)

    return StreamingResponse(
        classes.videos_handler.stream_video(video_id=video_id, start=start, end=end),
        media_type=media_type,
    )


# ── Settings routes ───────────────────────────────────────────────────────────

@api.get(f"{ROOT}/settings", response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def get_settings_route():
    config = ConfigManager().load_config()
    return ORJSONResponse({
        "status_code": 200,
        "settings": {
            "watch_delay_minutes": config.WATCH_DELAY_MINUTES,
            "videos_directory":    config.VIDEOS_PREFIX_DIRECTORY,
            "auth_enabled":        bool(config.ADMIN_USERNAME),
            "admin_username":      config.ADMIN_USERNAME,
        },
    })


class GeneralSettingsBody(BaseModel):
    watch_delay_minutes: int
    videos_directory: str


@api.put(f"{ROOT}/settings/general", response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def update_general_settings_route(body: GeneralSettingsBody):
    if body.watch_delay_minutes < 1:
        return ORJSONResponse({"ok": False, "message": "Interval must be at least 1 minute"}, status_code=422)
    ConfigManager().save_settings(
        watch_delay_minutes=body.watch_delay_minutes,
        videos_directory=body.videos_directory.strip() or None,
    )
    return ORJSONResponse({"ok": True})


class AuthSettingsBody(BaseModel):
    username: str
    current_password: str = ""
    new_password: str


@api.put(f"{ROOT}/settings/auth", response_class=ORJSONResponse,
         dependencies=[Depends(require_auth)])
async def update_auth_settings_route(body: AuthSettingsBody):
    config = ConfigManager().load_config()
    if config.ADMIN_USERNAME:
        pw_hash = hashlib.pbkdf2_hmac(
            "sha256", body.current_password.encode(), config.ADMIN_SALT.encode(), 200_000
        ).hex()
        if pw_hash != config.ADMIN_PASSWORD_HASH:
            return ORJSONResponse({"ok": False, "message": "Current password is incorrect"}, status_code=401)
    if not body.username.strip():
        return ORJSONResponse({"ok": False, "message": "Username cannot be empty"}, status_code=422)
    if not body.new_password:
        return ORJSONResponse({"ok": False, "message": "Password cannot be empty"}, status_code=422)
    salt    = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", body.new_password.encode(), salt.encode(), 200_000).hex()
    ConfigManager().save_auth(body.username.strip(), pw_hash, salt)
    return ORJSONResponse({"ok": True})


class DisableAuthBody(BaseModel):
    current_password: str


@api.post(f"{ROOT}/settings/auth/disable", response_class=ORJSONResponse,
          dependencies=[Depends(require_auth)])
async def disable_auth_route(body: DisableAuthBody):
    config = ConfigManager().load_config()
    if not config.ADMIN_USERNAME:
        return ORJSONResponse({"ok": True})
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", body.current_password.encode(), config.ADMIN_SALT.encode(), 200_000
    ).hex()
    if pw_hash != config.ADMIN_PASSWORD_HASH:
        return ORJSONResponse({"ok": False, "message": "Password is incorrect"}, status_code=401)
    ConfigManager().save_auth("", "", "")
    return ORJSONResponse({"ok": True})
