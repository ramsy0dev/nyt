import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Request, HTTPException

from nyt.src.config import ConfigManager

_JWT_LIFETIME = 30 * 86400  # 30 days


def _b64url_enc(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64url_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + '==')


_HEADER = _b64url_enc(b'{"alg":"HS256","typ":"JWT"}')


class AuthManager:
    def __init__(self) -> None:
        self._denied_jtis: set[str] = set()

    def _secret(self) -> bytes:
        cfg = ConfigManager().load_config()
        raw = (cfg.ADMIN_SALT + cfg.ADMIN_PASSWORD_HASH) or "nyt-no-auth-placeholder"
        return raw.encode()

    def is_auth_enabled(self) -> bool:
        return bool(ConfigManager().load_config().ADMIN_USERNAME)

    def create_session(self) -> str:
        now = int(time.time())
        payload = {
            "jti": secrets.token_hex(16),
            "sub": ConfigManager().load_config().ADMIN_USERNAME,
            "iat": now,
            "exp": now + _JWT_LIFETIME,
        }
        pl  = _b64url_enc(json.dumps(payload, separators=(',', ':')).encode())
        msg = f"{_HEADER}.{pl}"
        sig = hmac.new(self._secret(), msg.encode(), hashlib.sha256).digest()
        return f"{msg}.{_b64url_enc(sig)}"

    def _decode_token(self, token: str) -> dict | None:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            header, pl, sig = parts
            msg      = f"{header}.{pl}"
            expected = _b64url_enc(hmac.new(self._secret(), msg.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(sig, expected):
                return None
            payload = json.loads(_b64url_dec(pl))
            if payload.get('exp', 0) < int(time.time()):
                return None
            return payload
        except Exception:
            return None

    def validate_session(self, token: str) -> bool:
        payload = self._decode_token(token)
        if payload is None:
            return False
        return payload.get('jti') not in self._denied_jtis

    def revoke_session(self, token: str) -> None:
        payload = self._decode_token(token)
        if payload and payload.get('jti'):
            self._denied_jtis.add(payload['jti'])


auth_manager = AuthManager()


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get("nyt_session")
    if token:
        return token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def require_auth(request: Request) -> None:
    if not auth_manager.is_auth_enabled():
        return
    token = _extract_token(request)
    if not token or not auth_manager.validate_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
