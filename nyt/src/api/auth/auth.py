import secrets

from fastapi import Request, HTTPException

from nyt.src.config import ConfigManager


class AuthManager:
    def __init__(self) -> None:
        self._tokens: set[str] = set()

    def is_auth_enabled(self) -> bool:
        return bool(ConfigManager().load_config().ADMIN_USERNAME)

    def create_session(self) -> str:
        token = secrets.token_hex(32)
        self._tokens.add(token)
        return token

    def validate_session(self, token: str) -> bool:
        return token in self._tokens

    def revoke_session(self, token: str) -> None:
        self._tokens.discard(token)


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
